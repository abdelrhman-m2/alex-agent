"""
Alex Agent FastAPI Backend — Phase 5

REST API with:
- Async request handling
- HITL approval system
- Task queue management
- Monitoring & logging
- Status tracking
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from enum import Enum
import uuid

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DATA MODELS ====================

class TaskStatus(str, Enum):
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExecutionRequest(BaseModel):
    """Request to execute a goal"""
    goal: str
    priority: str = "normal"  # low, normal, high
    require_approval: bool = True
    metadata: Dict[str, Any] = {}


class ApprovalRequest(BaseModel):
    """Request for approval"""
    task_id: str
    decision: ApprovalDecision
    feedback: Optional[str] = None
    reviewer_id: str


class ExecutionResponse(BaseModel):
    """Response from task execution"""
    task_id: str
    status: TaskStatus
    goal: str
    result: Optional[str] = None
    confidence: float = 0.0
    timestamp: str


# ==================== TASK MANAGER ====================

class Task:
    """Represents an execution task"""
    
    def __init__(self, goal: str, priority: str = "normal", require_approval: bool = True):
        self.task_id = str(uuid.uuid4())[:8]
        self.goal = goal
        self.priority = priority
        self.require_approval = require_approval
        
        self.status = TaskStatus.PENDING
        self.result = None
        self.confidence = 0.0
        
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        
        self.approval_status = None
        self.approval_feedback = None
        self.approved_by = None
        self.approved_at = None
        
        self.attempts = 0
        self.max_attempts = 3
        self.error_message = None
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "priority": self.priority,
            "status": self.status.value,
            "result": self.result,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "attempts": self.attempts,
            "error_message": self.error_message
        }


class TaskQueue:
    """Manages task queue"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.pending_approvals: List[str] = []
    
    def create_task(self, goal: str, priority: str = "normal", require_approval: bool = True) -> Task:
        """Create and queue a task"""
        task = Task(goal, priority, require_approval)
        self.tasks[task.task_id] = task
        
        if require_approval:
            self.pending_approvals.append(task.task_id)
            task.status = TaskStatus.WAITING_APPROVAL
            logger.info(f"Task {task.task_id} created, awaiting approval")
        else:
            task.status = TaskStatus.PENDING
            logger.info(f"Task {task.task_id} created, ready for execution")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def approve_task(self, task_id: str, reviewer_id: str, feedback: Optional[str] = None) -> bool:
        """Approve a task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.approval_status = ApprovalDecision.APPROVED.value
        task.approved_by = reviewer_id
        task.approved_at = datetime.now().isoformat()
        task.approval_feedback = feedback
        
        task.status = TaskStatus.APPROVED
        
        if task_id in self.pending_approvals:
            self.pending_approvals.remove(task_id)
        
        logger.info(f"Task {task_id} approved by {reviewer_id}")
        return True
    
    def reject_task(self, task_id: str, reviewer_id: str, feedback: str) -> bool:
        """Reject a task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.approval_status = ApprovalDecision.REJECTED.value
        task.approved_by = reviewer_id
        task.approved_at = datetime.now().isoformat()
        task.approval_feedback = feedback
        
        task.status = TaskStatus.REJECTED
        
        if task_id in self.pending_approvals:
            self.pending_approvals.remove(task_id)
        
        logger.info(f"Task {task_id} rejected by {reviewer_id}")
        return True
    
    def start_execution(self, task_id: str) -> bool:
        """Start executing a task"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.EXECUTING
        task.started_at = datetime.now().isoformat()
        task.attempts += 1
        
        logger.info(f"Task {task_id} execution started (attempt {task.attempts})")
        return True
    
    def complete_task(self, task_id: str, result: str, confidence: float = 0.0) -> bool:
        """Mark task as completed"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.confidence = confidence
        task.completed_at = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} completed with confidence {confidence}")
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.FAILED
        task.error_message = error
        task.completed_at = datetime.now().isoformat()
        
        logger.error(f"Task {task_id} failed: {error}")
        return True
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get all tasks waiting for approval"""
        return [
            self.tasks[tid].to_dict()
            for tid in self.pending_approvals
        ]
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """Get all tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        return [t.to_dict() for t in tasks]


# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Alex Agent API",
    description="Autonomous Research & Analysis Agent",
    version="1.0.0"
)

# Initialize task queue
task_queue = TaskQueue()

# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "Alex Agent API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/execute")
async def execute_goal(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """
    Execute a goal
    
    If require_approval=True, returns task ID with WAITING_APPROVAL status.
    Otherwise, starts execution immediately.
    """
    logger.info(f"Execute request: {request.goal}")
    
    # Create task
    task = task_queue.create_task(
        goal=request.goal,
        priority=request.priority,
        require_approval=request.require_approval
    )
    
    if not request.require_approval:
        # Start execution immediately
        background_tasks.add_task(execute_task_background, task.task_id)
    
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "goal": task.goal,
        "requires_approval": request.require_approval,
        "message": "Task queued" if request.require_approval else "Task executing"
    }


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@app.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """List all tasks"""
    return {
        "tasks": task_queue.get_all_tasks(status),
        "count": len(task_queue.tasks),
        "pending_approvals": len(task_queue.pending_approvals)
    }


@app.get("/approvals/pending")
async def get_pending_approvals():
    """Get tasks waiting for approval"""
    return {
        "pending_count": len(task_queue.pending_approvals),
        "tasks": task_queue.get_pending_approvals()
    }


@app.post("/approvals/{task_id}")
async def approve_task(task_id: str, request: ApprovalRequest, background_tasks: BackgroundTasks):
    """
    Approve or reject a task
    """
    logger.info(f"Approval request for {task_id}: {request.decision}")
    
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if request.decision == ApprovalDecision.APPROVED:
        task_queue.approve_task(task_id, request.reviewer_id, request.feedback)
        # Start execution
        background_tasks.add_task(execute_task_background, task_id)
        
        return {
            "task_id": task_id,
            "decision": "approved",
            "message": "Task approved and executing",
            "status": task.status.value
        }
    
    elif request.decision == ApprovalDecision.REJECTED:
        task_queue.reject_task(task_id, request.reviewer_id, request.feedback or "No reason provided")
        
        return {
            "task_id": task_id,
            "decision": "rejected",
            "message": "Task rejected",
            "feedback": request.feedback
        }
    
    else:  # NEEDS_REVISION
        return {
            "task_id": task_id,
            "decision": "needs_revision",
            "message": "Task needs revision",
            "feedback": request.feedback
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tasks_total": len(task_queue.tasks),
        "tasks_pending": len([t for t in task_queue.tasks.values() if t.status == TaskStatus.PENDING]),
        "tasks_executing": len([t for t in task_queue.tasks.values() if t.status == TaskStatus.EXECUTING]),
        "tasks_completed": len([t for t in task_queue.tasks.values() if t.status == TaskStatus.COMPLETED]),
        "approvals_pending": len(task_queue.pending_approvals)
    }


@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    all_tasks = list(task_queue.tasks.values())
    
    completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
    failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]
    
    avg_confidence = sum(t.confidence for t in completed) / len(completed) if completed else 0
    
    return {
        "total_tasks": len(all_tasks),
        "completed_tasks": len(completed),
        "failed_tasks": len(failed),
        "success_rate": len(completed) / len(all_tasks) if all_tasks else 0,
        "avg_confidence": avg_confidence,
        "pending_approvals": len(task_queue.pending_approvals),
        "timestamp": datetime.now().isoformat()
    }


# ==================== BACKGROUND TASKS ====================

async def execute_task_background(task_id: str):
    """Background task execution"""
    logger.info(f"Starting background execution for task {task_id}")
    
    task = task_queue.get_task(task_id)
    if not task:
        return
    
    try:
        task_queue.start_execution(task_id)
        
        # Simulate execution
        import asyncio
        await asyncio.sleep(2)  # Simulate processing
        
        # Mock result
        result = f"Analysis complete for: {task.goal}\n\nKey findings:\n- Finding 1\n- Finding 2\n- Finding 3"
        
        task_queue.complete_task(task_id, result, confidence=0.87)
        logger.info(f"Task {task_id} execution completed")
        
    except Exception as e:
        task_queue.fail_task(task_id, str(e))
        logger.error(f"Task {task_id} execution failed: {e}")


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.now().isoformat()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.now().isoformat()}
    )


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    logger.info("Alex Agent API starting up...")
    logger.info("HITL approval system ready")
    logger.info("Task queue initialized")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Alex Agent API shutting down...")
    logger.info(f"Final stats: {len(task_queue.tasks)} tasks processed")


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Alex Agent API")
    print("📋 HITL Approval System: ENABLED")
    print("📊 Task Queue: INITIALIZED")
    print("\n🔗 API running at http://localhost:8000")
    print("📖 Docs at http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
