from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lcm.api.endpoints import hosts, images, networks, vms
from lcm.config import settings
from lcm.db import engine
from lcm.db.models import Base
from lcm.db.repository import HostRepository
from lcm.orchestrator.vm_scheduler import VMScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.scheduler = VMScheduler(host_repo=HostRepository())
    yield


app = FastAPI(
    title="CEE-LCM",
    description="Cloud Environment Orchestrator - Lifecycle Management",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vms.router, prefix="/api/v1", tags=["VMs"])
app.include_router(networks.router, prefix="/api/v1", tags=["Networks"])
app.include_router(images.router, prefix="/api/v1", tags=["Images"])
app.include_router(hosts.router, prefix="/api/v1", tags=["Hosts"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
