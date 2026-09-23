from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from graph import run_support_system
from pydantic import BaseModel
import logging
from tinydb import TinyDB
from datetime import datetime

class ChatRequest(BaseModel):
    question: str


load_dotenv()


app = FastAPI(title= "Harness engineering for multi agents")

# Setup Logging
logging.basicConfig(
    filename='agent_executions.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
agent_logger = logging.getLogger("AgentLogger")

# Setup TinyDB
db = TinyDB('db.json')
logs_table = db.table('executions')

BASE_DIR = Path(__file__).resolve().parent
static_dir =BASE_DIR /"static"
temp_dir= BASE_DIR /"templates"


app.mount("/static",StaticFiles(directory="static"),name="static")
template = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return template.TemplateResponse(request=request, name="index.html")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    result = run_support_system(req.question)
    
    # Calculate iterations (number of traces)
    trace_array = result.get("trace", [])
    iterations = len(trace_array)
    
    # The custom run_support_system returns 'answer', not 'final_answer'
    final_answer = result.get("answer") or ""
    
    if not final_answer:
        # Fallback to final_answer just in case
        final_answer = result.get("final_answer") or ""
        
    # Log the execution
    agent_logger.info(f"Question: {req.question} | Iterations: {iterations} | Route: {result.get('route', 'unknown')}")
    
    # Save to NoSQL Database
    logs_table.insert({
        "timestamp": datetime.now().isoformat(),
        "question": req.question,
        "final_answer": final_answer,
        "route": result.get("route", ""),
        "iterations": iterations,
        "trace": trace_array
    })
        
    return {
        "final_answer": final_answer,
        "trace": trace_array,
        "iterations": iterations
    }

from collections import defaultdict

@app.get("/api/metrics")
async def get_metrics():
    records = logs_table.all()
    total = len(records)
    
    if total == 0:
        return {"total_queries": 0, "workload": {}, "traffic": {}, "success_rate": 0}
        
    successful = 0
    workload = defaultdict(int)
    traffic = defaultdict(int)
    
    for r in records:
        if r.get("final_answer"):
            successful += 1
            
        route = r.get("route", "unknown")
        if route:
            workload[route] += 1
            
        ts = r.get("timestamp")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                hour_label = dt.strftime("%I %p").lstrip('0')
                traffic[hour_label] += 1
            except:
                pass
                
    success_rate = round((successful / total) * 100, 1)
    
    # Fill in default routes if missing so frontend doesn't break
    for r in ["technical", "billing", "general"]:
        if r not in workload:
            workload[r] = 0
            
    return {
        "total_queries": total,
        "success_rate": success_rate,
        "workload": dict(workload),
        "traffic": dict(traffic)
    }


if __name__ =="__main__":
    uvicorn.run("app:app",
    host ="0.0.0.0",
    port = 8080,
    reload = True,
    reload_includes=["*.html", "*.css", "*.js"])