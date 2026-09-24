import operator
from typing import TypedDict, Literal, Annotated, Sequence

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from tools import math_tool, web_search, web_scraper, fetch_recent_executions, create_support_ticket, check_refund_status

from agent import (
    technical_agent,
    billing_agent,
    general_agent,
    review_agent,
    get_llm,
    get_small_llm
)


class SupportState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    question: str
    route: str
    final_answer: str
    intent: str
    blocked: bool
    trace: Annotated[list[str], operator.add]


def guard_rail_mode_non_LLM(state: SupportState):
    """
    A simple deterministic safety layer
    In a system this could include moderation,
    PII detection, permission and policy checks
    """
    question = state["question"].lower()
    dangerous_phrases = ["give me your password", "steal_password", "cancel_subscription", "hack"]

    blocked = any(phrase in question for phrase in dangerous_phrases)

    if blocked:
       return {
        "blocked": True,
        "intent": "malicious",
        "final_answer": "I can't help with the request involving malicious intent and other illegal activities",
        "trace": ["Guard Rail checked the request"],
       }

    return {"blocked": False, "trace": ["Guard Rail checked the request"]}


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
    
    if response.intent == "malicious":
       return {
        "blocked": True,
        "intent": "malicious",
        "final_answer": "I can't help with requests involving malicious intent or other illegal activities.",
        "trace": ["LLM Guard Rail checked the request"],
       }
    
    return {"blocked": False, "intent": "safe", "trace": ["LLM Guard Rail checked the request"]}


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

    # Deterministic routing based on strict keywords
    if any(kw in lower_question for kw in ["payment", "refund", "credit card", "cancel subscription"]):
        route = "billing"
        trace_msg = "Deterministic router assigned to: billing"
    elif any(kw in lower_question for kw in ["install", "login", "crash"]):
        route = "technical"
        trace_msg = "Deterministic router assigned to: technical"
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
        trace_msg = f"LLM router assigned to: {route}"
        
    return {"route": route, "trace": [trace_msg]}


def choose_agent(state: SupportState) -> Literal["technical_agent", "billing_agent", "general_agent"]:
    """Choose the agent based on the route"""
    if state["route"] == "technical":
        return "technical_agent"
    elif state["route"] == "billing":
        return "billing_agent"
    
    return "general_agent"

def should_continue(state: SupportState) -> Literal["tools", "reviewer"]:
    """Determines whether to execute a tool or go to the reviewer."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM returned tool calls, route to the tools node
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return "reviewer"


# Set up tools for LangGraph prebuilt ToolNode
all_tools = [math_tool, web_search, web_scraper, fetch_recent_executions, create_support_ticket, check_refund_status]
tool_node = ToolNode(all_tools)


# Graph Construction
builder = StateGraph(SupportState)

builder.add_node("guard_rail_non_LLM", guard_rail_mode_non_LLM)
builder.add_node("guard_rail", guard_rail_mode_LLM)
builder.add_node("router", router_node)
builder.add_node("technical_agent", technical_agent)
builder.add_node("billing_agent", billing_agent)
builder.add_node("general_agent", general_agent)
builder.add_node("tools", tool_node)
builder.add_node("reviewer", review_agent)

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

# Agents route to either tools (if they requested a tool call) or reviewer
builder.add_conditional_edges("technical_agent", should_continue, {"tools": "tools", "reviewer": "reviewer"})
builder.add_conditional_edges("billing_agent", should_continue, {"tools": "tools", "reviewer": "reviewer"})
builder.add_conditional_edges("general_agent", should_continue, {"tools": "tools", "reviewer": "reviewer"})

# Tool node routes back to the active agent to interpret the tool result
def route_tool_back(state: SupportState) -> str:
    return state["route"] + "_agent"

builder.add_conditional_edges("tools", route_tool_back, {
    "technical_agent": "technical_agent",
    "billing_agent": "billing_agent",
    "general_agent": "general_agent"
})

builder.add_edge("reviewer", END)

graph = builder.compile()


def run_support_system(question: str) -> dict:
    initial_state: SupportState = {
        "question": question,
        "messages": [HumanMessage(content=question)],
        "route": "",
        "final_answer": "",
        "blocked": False,
        "intent": "",
        "trace": []
    }

    result = graph.invoke(initial_state)
    
    # Extract used tools from the message history
    used_tools = []
    if "messages" in result:
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    agent_name = result.get("route", "unknown") + "_agent"
                    used_tools.append(f"{agent_name} used '{tc['name']}'")

    return {
        "route": result.get("route", "blocked"),
        "answer": result.get("final_answer"),
        "trace": result.get("trace", []),
        "used_tools": used_tools
    }