import os
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq

MODEL_NAME = "openai/gpt-oss-20b"
load_dotenv()

def get_llm():

    return ChatGroq(model =MODEL_NAME,temperature = 0.2, api_key=os.getenv("GROQ_API_KEY"))


# llm = get_llm()
# r = llm.invoke("hello")


# print(r.content)    

def technical_agent(question :str)-> str:
    
    llm = get_llm()
    
    prompt = f"""
    You are the technical Support agent .


    Your Job:
    - Help  with login problems , API Errors , installation problems , bugs and technical setup
    - explain the solution in easy steps
    - Never invent account specific information
    - if important information is missing , clearly say what the user should check
    
    -Answer technical question.
    -Explain complex topics in simple words.
    -Debug user problems.

    Rules:
    
    -Be Clear 
    -Be Concise 
    -Be accurate 
    
    
    Customer Question :
    {question}
    Return only the helpful answer
    """
    return llm.invoke(prompt).content
    

def billing_agent(question:str)->str:
    llm =get_llm()
    
    prompt = f"""
    You are the billing Support agent .


   Company Demo policy:

   - Starter plan 100 INR a month
   - Pro plan 1000 INR a month
   - Refund request must be reviwed by the billing team
   - Never claim a refund that has been already been approved
   - Never ask for full card numbers and  sensitive information


   Customer Question:
   {question}

    Rules:
    - Answer clearly  and safely with the reference above
    -Be Clear
    -Be Concise 
    -Be accurate 
    
    """
    return llm.invoke(prompt).content



def general_agent(question:str)->str:
    llm =get_llm()
    
    prompt = f"""
    You are the general Support agent .
    - Answer Questions politely and simply
    - If the question requires technical support and billing support say it should be handled by the appropiate specialist
    

   Customer Question:
   {question}

    Rules:
    - Answer clearly ,politely and safely 
    -Be Clear
    -Be Concise 
    -Be accurate 
    
    """
    return llm.invoke(prompt).content    





def review_agent(question:str,draft :str)->str:
    llm =get_llm()
    prompt = f"""

    You are the quality reviwer agent in a production customer-support system

    Your Job
    - check the draft answer for 1) clarity 2) relevance 3) unsafe requets for passwords /card numbers, 4) unsupported gurrantes 5) uncessary complexity

    rewrite the answers if needed 
    keep the final answer concise and beginner friendly

    orignal customer question:
    {question}
    
    agents draft:
    {draft}

    Return only the revised answer , nothing else
    """
    return llm.invoke(prompt).content  