import json
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from ddgs import DDGS

@tool
def math_tool(operation: str, a: float, b: float) -> str:
    """
    Performs basic math operations. 
    'operation' must be one of: 'add', 'subtract', 'multiply', 'divide'.
    """
    if operation == "add":
        return str(a + b)
    elif operation == "subtract":
        return str(a - b)
    elif operation == "multiply":
        return str(a * b)
    elif operation == "divide":
        if b == 0:
            return "Error: Cannot divide by zero."
        return str(a / b)
    else:
        return "Error: Invalid operation. Must be add, subtract, multiply, or divide."

@tool
def web_search(query: str) -> str:
    """
    Performs a web search using DuckDuckGo.
    Use this to find current information, news, or general knowledge on the internet.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No results found."
            
            formatted_results = []
            for res in results:
                formatted_results.append(f"Title: {res['title']}\nSnippet: {res['body']}\nLink: {res['href']}")
            
            return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing web search: {e}"

@tool
def web_scraper(url: str) -> str:
    """
    Scrapes a web page and returns the text content.
    Use this to read the contents of a webpage provided by a URL.
    """
    try:
        # Using 'with' ensures the SSL socket is properly closed to prevent ResourceWarnings
        with requests.get(url, timeout=10) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements as they are not useful text
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        
        # Limit length to avoid blowing up the LLM's context window
        return text[:5000] 
    except Exception as e:
        return f"Error scraping URL: {e}"

@tool
def fetch_recent_executions() -> str:
    """
    Fetches the recent agent execution logs from the local database.
    Use this to see what previous questions the support system has answered.
    """
    try:
        with open("db.json", "r", encoding="utf-8") as f:
            db = json.load(f)
            
        executions = db.get("executions", {})
        if not executions:
            return "No executions found."
            
        # Format the last 3 executions
        result = "Recent Executions:\n"
        # Get the last 3 keys (assuming they are chronological)
        latest_keys = list(executions.keys())[-3:]
        
        for key in latest_keys:
            data = executions[key]
            result += f"- ID: {key} | Route: {data.get('route')} | Question: {data.get('question')}\n"
            
        return result
    except Exception as e:
        return f"Error accessing database: {e}"

@tool
def create_support_ticket(user_email: str, issue_description: str, category: str) -> str:
    """
    Creates a support ticket for a user if they have an issue that cannot be resolved automatically.
    Categories should be 'billing', 'technical', or 'general'.
    """
    # In a real app, this would make an API call to a ticketing system like Jira or Zendesk
    ticket_id = f"TICKET-{category[:3].upper()}-8923"
    return f"Successfully created {category} ticket '{ticket_id}' for {user_email}."

@tool
def check_refund_status(transaction_id: str) -> str:
    """
    Checks the status of a requested refund using a transaction ID.
    Use this when a user asks about their refund.
    """
    # Simulated API call to a payment provider like Stripe
    if len(transaction_id) < 5:
        return "Error: Invalid transaction ID format."
    return f"Transaction {transaction_id} refund is currently 'Processing' and will take 2-3 business days to appear in the user's account."
