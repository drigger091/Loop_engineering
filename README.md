# Agent Harness

Agent Harness is a multi-agent customer support system built with LangGraph and FastAPI, featuring a modern, interactive frontend dashboard. The system intelligently routes user queries to specialized AI agents, executes tasks with safety guardrails, and rigorously reviews outputs before presenting the final response to the user.

## System Workflow

Here is a step-by-step breakdown of how the LangGraph multi-agent system processes a user's request:

1. **User Query**: The user asks a question via the web chat interface.
2. **Deterministic Guardrails**: The input is first scanned for obvious malicious intents (e.g., asking for passwords or hacking attempts) using keyword matching.
3. **LLM Guardrails**: A secondary, lightweight LLM analyzes the query to detect more complex, nuanced malicious requests.
4. **Router**: The request is intelligently routed to the appropriate specialized agent using keyword heuristics or an LLM decision node:
   - **Technical Agent**: Handles bugs, login issues, and API errors.
   - **Billing Agent**: Handles refunds, pricing, and plan upgrades based on company policy.
   - **General Agent**: Handles general inquiries.
5. **Draft Generation**: The selected specialized agent processes the query and generates a draft response.
6. **Reviewer Agent**: The draft is evaluated by a Quality Reviewer Agent for clarity, safety, relevance, and unnecessary complexity. The draft is rewritten if necessary.
7. **Final Output**: The UI displays the polished response along with a live execution trace and updates the session logs.

## Setup Instructions

### 1. Set up the Python Environment
It is highly recommended to use a virtual environment to manage dependencies:
```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (macOS/Linux)
# source venv/bin/activate
```

### 2. Install Dependencies
Install all required Python packages (FastAPI, LangGraph, LangChain, etc.):
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
You need to provide your API keys for the LLM to function. 
Create a new file named `.env` in the root folder of the project and add your API key. Make sure to **never** commit this file to version control.

```env
# .env
GROQ_API_KEY="your_secret_api_key_here"
```
*(Replace `your_secret_api_key_here` with your actual Groq API key)*

### 4. Run the Application
Start the FastAPI server. The app is configured to automatically run on port `8080`:
```bash
python app.py
```

### 5. Access the Dashboard
Open your web browser and navigate to:
[http://localhost:8080](http://localhost:8080)
