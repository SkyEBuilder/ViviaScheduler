import datetime as DT
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from vivia_v4.templates import ALLTASKTEMPLATES, ScheduleInterval
from vivia_v4.scheduler import ViviaScheduler
from vivia_v4.api.auth import router as auth_router, get_current_user
from vivia_v4.api.manager import PoolManager

app = FastAPI(
    title="ViviaScheduler API",
    description="API for ViviaScheduler task management and solving",
    version="0.1.0"
)

app.include_router(auth_router)

# --- Dependencies ---

def get_current_user_pool(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    return PoolManager.load_pool(user_id)

# --- Models ---

class SolveRequest(BaseModel):
    start: DT.datetime
    end: DT.datetime

class SolveResponse(BaseModel):
    status: str
    intervals: dict[str, list[ScheduleInterval]]  # task_id -> intervals

# --- Endpoints ---

@app.post("/tasks/create", tags=["Tasks"])
async def create_task(
    task: ALLTASKTEMPLATES,
    user: dict = Depends(get_current_user)
):
    """
    Add a single task to the user's pool.
    """
    user_id = user["user_id"]
    pool = PoolManager.load_pool(user_id)
    
    # We add to 'default' group for now, or could expose group_name in query param
    pool.add_task(task)
    
    PoolManager.save_pool(user_id, pool)
    return {"message": "Task added successfully", "task_id": task.id}

@app.post("/tasks/batch", tags=["Tasks"])
async def create_tasks_batch(
    tasks: list[ALLTASKTEMPLATES],
    user: dict = Depends(get_current_user)
):
    """
    Add multiple tasks to the user's pool.
    """
    user_id = user["user_id"]
    pool = PoolManager.load_pool(user_id)
    
    for t in tasks:
        pool.add_task(t)
        
    PoolManager.save_pool(user_id, pool)
    return {"message": f"{len(tasks)} tasks added successfully"}

@app.post("/scheduler/solve", tags=["Scheduler"], response_model=SolveResponse)
async def solve_schedule(
    request: SolveRequest,
    user: dict = Depends(get_current_user)
):
    """
    Build and solve the schedule for the user's task pool within the specified range.
    """
    user_id = user["user_id"]
    pool = PoolManager.load_pool(user_id)
    
    if not pool.tasks:
        raise HTTPException(status_code=400, detail="Task pool is empty")

    scheduler = ViviaScheduler(
        task_pool=pool,
        schedule_range=(request.start, request.end)
    )
    
    try:
        scheduler.build_model()
        # Capture output or check status (scheduler.solve prints to stdout currently)
        # We need to adapt scheduler.solve to return status or inspect context after solve
        # Since scheduler.solve() prints, we trust it modifies the intervals in-place
        
        # We can modify scheduler.py later to return status, but for now we run it
        # and check context
        scheduler.solve()
        
        # Check if we have results (mapped to actual intervals)
        # We will group by task ID for the response
        result = {}
        for task_id, intervals in scheduler._ctx._interval_map.items():
            # Only include intervals that are assigned (presence=1) or meaningful
            # For now, we return all, as interprete_cp_model_vars handles setting them
            result[str(task_id)] = intervals
            
        return SolveResponse(status="Solved", intervals=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount Gradio app to /admin
import gradio as gr

from vivia_v4.admin_ui import demo as gradio_admin_app
app = gr.mount_gradio_app(app, gradio_admin_app, path="/admin")

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", ssl_keyfile="skinkebravia.top_private.key", ssl_certfile="skinkebravia.top_full.crt")
