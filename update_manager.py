"""
Update management endpoints for Local Agent
Handles backend and frontend updates via API
"""
import os
import subprocess
import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Track update status
update_status = {
    "backend": {"running": False, "status": "idle", "message": ""},
    "frontend": {"running": False, "status": "idle", "message": ""}
}

class UpdateResponse(BaseModel):
    success: bool
    message: str
    status: str

def run_update_script(script_name: str, update_type: str):
    """Run update script in background"""
    global update_status
    
    try:
        # Get the project root directory (where the script should be)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(project_root, script_name)
        
        if not os.path.exists(script_path):
            update_status[update_type]["status"] = "error"
            update_status[update_type]["message"] = f"Script not found: {script_path}"
            update_status[update_type]["running"] = False
            return
        
        update_status[update_type]["status"] = "running"
        update_status[update_type]["message"] = f"Updating {update_type}..."
        
        # Run the batch script
        logger.info(f"Running update script: {script_path}")
        
        # For backend updates, run in a way that allows server restart
        if update_type == "backend":
            # Start the script and detach (it will handle stopping/restarting the server)
            subprocess.Popen(
                [script_path],
                cwd=project_root,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            update_status[update_type]["status"] = "initiated"
            update_status[update_type]["message"] = "Backend update initiated. Server will restart automatically."
        else:
            # For frontend, run in background
            process = subprocess.Popen(
                [script_path],
                cwd=project_root,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            update_status[update_type]["status"] = "success"
            update_status[update_type]["message"] = f"{update_type.capitalize()} update started successfully"
        
        update_status[update_type]["running"] = False
        
    except Exception as e:
        logger.error(f"Error running {update_type} update: {e}")
        update_status[update_type]["status"] = "error"
        update_status[update_type]["message"] = str(e)
        update_status[update_type]["running"] = False

@router.post("/update/app", response_model=UpdateResponse)
async def update_app():
    """Update entire application from GitHub - preserves indexed documents"""
    
    if update_status["backend"]["running"] or update_status["frontend"]["running"]:
        raise HTTPException(status_code=409, detail="Update already in progress")
    
    # Start backend update first
    update_status["backend"]["running"] = True
    thread_backend = threading.Thread(target=run_update_script, args=("update_backend.bat", "backend"))
    thread_backend.daemon = True
    thread_backend.start()
    
    # Start frontend update
    update_status["frontend"]["running"] = True
    thread_frontend = threading.Thread(target=run_update_script, args=("update_frontend.bat", "frontend"))
    thread_frontend.daemon = True
    thread_frontend.start()
    
    return UpdateResponse(
        success=True,
        message="Application update started. Your indexed documents are safe. Console windows will show progress.",
        status="initiated"
    )

@router.get("/update/status")
async def get_update_status():
    """Get current update status"""
    return update_status
