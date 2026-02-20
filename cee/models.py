"""Data models for the Cloud Execution Environment."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Language(str, Enum):
    python = "python"
    bash = "bash"


class ExecutionRequest(BaseModel):
    language: Language = Field(
        ..., description="Programming language to execute the code in"
    )
    code: str = Field(..., description="Source code to execute")
    timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Maximum execution time in seconds (1–60)",
    )
    stdin: Optional[str] = Field(
        default=None, description="Optional standard input to pass to the program"
    )


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"


class ExecutionResult(BaseModel):
    job_id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(..., description="Current status of the job")
    stdout: Optional[str] = Field(default=None, description="Standard output")
    stderr: Optional[str] = Field(default=None, description="Standard error")
    exit_code: Optional[int] = Field(default=None, description="Process exit code")
    language: Language = Field(..., description="Language used")
    timeout: int = Field(..., description="Configured timeout in seconds")
