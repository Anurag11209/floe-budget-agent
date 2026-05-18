from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.orchestrator import run_task

router = APIRouter()

class TaskRequest(BaseModel):
    description: str

@router.post("/tasks/run")
async def run_agent_task(request: TaskRequest):
    result = await run_task(request.description)
    return result
