"""FastAPI application for the Cloud Execution Environment."""

import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException

from .executor import execute
from .models import ExecutionRequest, ExecutionResult, JobStatus

app = FastAPI(
    title="Cloud Execution Environment",
    description="Submit code for remote sandboxed execution and retrieve results.",
    version="1.0.0",
)

# In-memory job store (keyed by job_id)
_jobs: Dict[str, ExecutionResult] = {}


@app.post("/execute", response_model=ExecutionResult, status_code=201)
def submit_job(request: ExecutionRequest) -> ExecutionResult:
    """Submit code for execution.

    The job runs synchronously and the completed result is returned immediately.
    """
    job_id = str(uuid.uuid4())

    stdout, stderr, exit_code, timed_out = execute(
        language=request.language,
        code=request.code,
        timeout=request.timeout,
        stdin=request.stdin,
    )

    if timed_out:
        status = JobStatus.timeout
    elif exit_code == 0:
        status = JobStatus.completed
    else:
        status = JobStatus.failed

    result = ExecutionResult(
        job_id=job_id,
        status=status,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        language=request.language,
        timeout=request.timeout,
    )
    _jobs[job_id] = result
    return result


@app.get("/jobs/{job_id}", response_model=ExecutionResult)
def get_job(job_id: str) -> ExecutionResult:
    """Retrieve the result of a previously submitted job."""
    result = _jobs.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return result
