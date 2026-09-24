import os
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from tools import math_tool, web_search, web_scraper, fetch_recent_executions, create_support_ticket, check_refund_status

MAIN_MODEL_NAME = "openai/gpt-oss-20b"
OTHER_MODEL_NAME = "openai/gpt-oss-safeguard-20b"
load_dotenv()

def get_llm():
    return ChatGroq(model=MAIN_MODEL_NAME, temperature=0.2, api_key=os.getenv("GROQ_API_KEY"))

def get_small_llm():
    return ChatGroq(model=OTHER_MODEL_NAME, temperature=0.2, api_key=os.getenv("GROQ_API_KEY"))

def technical_agent(state: dict):
    llm = get_llm()
    tools = [web_search, web_scraper, fetch_recent_executions, create_support_ticket]
    llm_with_tools = llm.bind_tools(tools)
    
    sys_msg = SystemMessage(content="""
    You are the technical Support agent.

    Your Job:
    - Help with login problems, API Errors, installation problems, bugs and technical setup
    - explain the solution in easy steps
    - Never invent account specific information
    - if important information is missing, clearly say what the user should check
    - Answer technical question.
    - Explain complex topics in simple words.
    - Debug user problems.

    Rules:
    - Be Clear 
    - Be Concise 
    - Be accurate 
    """)
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    
    trace_msgs = ["technical agent processed request"]
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            trace_msgs.append(f"technical agent requested tool: {tc['name']}")
            
    return {"messages": [response], "trace": trace_msgs}

def billing_agent(state: dict):
    llm = get_llm()
    tools = [math_tool, check_refund_status, create_support_ticket]
    llm_with_tools = llm.bind_tools(tools)
    
    sys_msg = SystemMessage(content="""
    You are the billing Support agent.

    Company Demo policy:
    - Starter plan 100 INR a month
    - Pro plan 1000 INR a month
    - Refund request must be reviewed by the billing team
    - Never claim a refund that has been already been approved
    - Never ask for full card numbers and sensitive information

    Rules:
    - Answer clearly and safely with the reference above
    - Be Clear
    - Be Concise 
    - Be accurate 
    """)
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    
    trace_msgs = ["billing agent processed request"]
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            trace_msgs.append(f"billing agent requested tool: {tc['name']}")
            
    return {"messages": [response], "trace": trace_msgs}

def general_agent(state: dict):
    llm = get_llm()
    tools = [web_search, web_scraper, math_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    sys_msg = SystemMessage(content="""
    You are the general Support agent.
    - Answer Questions politely and simply
    - If the question requires technical support and billing support say it should be handled by the appropriate specialist
    - IMPORTANT: If the user asks general questions about entities, companies, games, products, current events, news, or facts, YOU MUST USE THE `web_search` tool. Do not rely solely on your pre-trained knowledge.
    - IMPORTANT: If the user provides a specific URL/link in their question, YOU MUST USE THE `web_scraper` tool to read its contents. Do not use web_search for URLs.
    - IMPORTANT: You MUST use the `math_tool` for ALL numerical calculations. Do not attempt to calculate numbers yourself, no matter how simple the math is.

    Rules:
    - Answer clearly, politely and safely 
    - Be Clear
    - Be Concise 
    - Be accurate 
    """)
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    
    trace_msgs = ["general agent processed request"]
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            trace_msgs.append(f"general agent requested tool: {tc['name']}")
            
    return {"messages": [response], "trace": trace_msgs}

def review_agent(state: dict):
    llm = get_llm()
    question = state["question"]
    # Get the last AI message as the draft
    draft = state["messages"][-1].content
    
    prompt = f"""
    You are the quality reviewer agent in a production customer-support system

    Your Job
    - check the draft answer for 1) clarity 2) relevance 3) unsafe requests for passwords /card numbers, 4) unsupported guarantees 5) unnecessary complexity
    - Structure and format the final answer nicely (use Markdown, bold text, bullet points, headers) so the context is easy to read and understand.

    rewrite the answers if needed.
    If no changes are needed, return the original draft exactly as is.
    keep the final answer concise and beginner friendly.

    original customer question:
    {question}
    
    agents draft:
    {draft}

    Return the final revised answer. Do not return empty.
    """
    response = llm.invoke(prompt)
    return {"final_answer": response.content, "trace": ["reviewer agent reviewed the answer"]}