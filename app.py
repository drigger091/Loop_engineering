from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from graph import run_support_system
from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str


load_dotenv()


app = FastAPI(title= "Harness engineering for multi agents")


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
    # The custom run_support_system returns 'answer', not 'final_answer'
    final_answer = result.get("answer") or ""
    
    if not final_answer:
        # Fallback to final_answer just in case
        final_answer = result.get("final_answer") or ""
        
    return {
        "final_answer": final_answer,
        "trace": result.get("trace", [])
    }


if __name__ =="__main__":
    uvicorn.run("app:app",
    host ="0.0.0.0",
    port = 8080,
    reload = True)