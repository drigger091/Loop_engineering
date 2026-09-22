from typing import TypedDict, Literal

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from agent import (
    technical_agent,
    billing_agent,
    general_agent,
    review_agent,
    get_llm,
    get_small_llm
)


class SupportState(TypedDict):
    question: str
    route: str
    agent_type: str
    draft: str
    final_answer: str
    intent: str
    blocked: bool
    trace: list[str]


def guard_rail_mode_non_LLM(state: SupportState):
    """
    A simple deterministic safety layer
    In a system this could include moderation,
    PII detection, permission and policy checks
    """
    question = state["question"].lower()
    dangerous_phrases = ["give me your password", "steal_password", "cancel_subscription", "hack"]

    blocked = any(phrase in question for phrase in dangerous_phrases)
    trace = state.get("trace", []) + ["Guard Rail checked the request"]

    if blocked:
       return {
        "blocked": True,
        "intent": "malicious",
        "final_answer": "I can't help with the request involving malicious intent and other illegal activities",
        "trace": trace,
       }

    return {"blocked": False, "trace": trace}


class GuardRailResult(BaseModel):
    intent: Literal["malicious", "safe"] = Field(description="Classification of the question. Must be 'malicious' or 'safe'.")


def guard_rail_mode_LLM(state: SupportState):
    """
    LLM based guard rail to detect dangerous or malicious intent using PydanticOutputParser
    """
    question = state["question"]
    llm = get_small_llm()
    parser = PydanticOutputParser(pydantic_object=GuardRailResult)
    
    prompt = PromptTemplate(
        template="Analyze the following customer question and determine if it has malicious intent, is asking for a hack, trying to steal passwords, or is otherwise dangerous or illegal.\n\n{format_instructions}\n\nQuestion: {question}\n",
        input_variables=["question"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    chain = prompt | llm | parser
    response = chain.invoke({"question": question})
    
    trace = state.get("trace", []) + ["LLM Guard Rail checked the request"]
    
    if response.intent == "malicious":
       return {
        "blocked": True,
        "intent": "malicious",
        "final_answer": "I can't help with requests involving malicious intent or other illegal activities.",
        "trace": trace,
       }
    
    return {"blocked": False, "intent": "safe", "trace": trace}


def after_guardrail(state: SupportState) -> Literal["next", "end"]:
    """decides where to route the conversation"""
    if state["blocked"]:
        return "end"
    return "next"


class RouterResult(BaseModel):
    route: Literal["technical", "billing", "general"] = Field(
        description="The assigned route for the user question. Must be 'technical', 'billing', or 'general'."
    )


def router_node(state: SupportState):
    """
    Uses a combination of deterministic keyword matching and an LLM 
    to route the customer question to the correct department.
    """
    question = state["question"]
    lower_question = question.lower()
    trace = state.get("trace", [])

    # Deterministic routing based on keywords
    if any(kw in lower_question for kw in ["billing", "payment", "refund", "credit card", "price", "plan"]):
        route = "billing"
        trace.append("Deterministic router assigned to: billing")
    elif any(kw in lower_question for kw in ["bug", "error", "install", "login", "api", "setup", "crash"]):
        route = "technical"
        trace.append("Deterministic router assigned to: technical")
    else:
        # LLM-based routing
        llm = get_small_llm()
        parser = PydanticOutputParser(pydantic_object=RouterResult)
        
        prompt = PromptTemplate(
            template="Route the following customer question to the appropriate department (technical, billing, or general).\n\n{format_instructions}\n\nQuestion: {question}\n",
            input_variables=["question"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
        chain = prompt | llm | parser
        response = chain.invoke({"question": question})
        route = response.route
        trace.append(f"LLM router assigned to: {route}")
        
    return {"route": route, "trace": trace}


def choose_agent(state: SupportState) -> Literal["technical_agent", "billing_agent", "general_agent"]:
    """Choose the agent based on the route"""
    if state["route"] == "technical":
        return "technical_agent"
    elif state["route"] == "billing":
        return "billing_agent"
    
    return "general_agent"


def create_agent_node(agent_func, agent_name: str):
    """Factory function to create agent nodes to avoid code duplication."""
    def node(state: SupportState):
        answer = agent_func(state["question"])
        return {"draft": answer, "trace": state.get("trace", []) + [f"{agent_name} agent drafted the answer"]}
    return node


technical_node = create_agent_node(technical_agent, "technical")
billing_node = create_agent_node(billing_agent, "billing")
general_node = create_agent_node(general_agent, "general")


def reviewer_node(state: SupportState):
    final_answer = review_agent(question=state["question"], draft=state["draft"])
    return {"final_answer": final_answer, "trace": state.get("trace", []) + ["reviewer agent reviewed the answer"]}


# Graph Construction
builder = StateGraph(SupportState)

builder.add_node("guard_rail_non_LLM", guard_rail_mode_non_LLM)
builder.add_node("guard_rail", guard_rail_mode_LLM)
builder.add_node("router", router_node)
builder.add_node("technical_agent", technical_node)
builder.add_node("billing_agent", billing_node)
builder.add_node("general_agent", general_node)
builder.add_node("reviewer", reviewer_node)

builder.add_edge(START, "guard_rail_non_LLM")

builder.add_conditional_edges(
    "guard_rail_non_LLM",
    after_guardrail,
    {"end": END, "next": "guard_rail"}
)

builder.add_conditional_edges(
    "guard_rail",
    after_guardrail,
    {"end": END, "next": "router"}
)

builder.add_conditional_edges(
    "router",
    choose_agent,
    {
        "technical_agent": "technical_agent",
        "billing_agent": "billing_agent",
        "general_agent": "general_agent"
    }
)

builder.add_edge("technical_agent", "reviewer")
builder.add_edge("billing_agent", "reviewer")
builder.add_edge("general_agent", "reviewer")

builder.add_edge("reviewer", END)

graph = builder.compile()

def run_support_system(question: str):
    initial_state = {"question": question, "trace": []}
    result = graph.invoke(initial_state)
    return result




def run_support_system(question:str)->str:
    intial_state:SupportState ={
        "question":question,
        "route":"",
        "draft":"",
        "final_answer": "",
        "blocked": False,
        "intent": "",
        "trace": []
        
    }

    result = graph.invoke(intial_state)
    return{
        "route":result.get("route","blocked"),
        "answer":result.get("final_answer"),
        "trace":result.get("trace",[])
        
        
    }