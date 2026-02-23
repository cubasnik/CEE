from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from lcm.orchestrator.vm_lifecycle_kvm import VMLifecycleKVM

class VMResponse(BaseModel):
    id: str
    name: str
    status: str
    ip_addresses: list[str]
    created_at: str

class VMCreateRequest(BaseModel):
    name: str
    vcpus: int
    memory_mb: int
    image_path: str

router = APIRouter(prefix="/vms-kvm", tags=["vms-kvm"])

# --- ROUTES ---

@router.get("/", response_model=list[VMResponse])
async def list_vms():
    vms = await VMLifecycleKVM().list()
    return vms

@router.post("/", response_model=VMResponse)
async def create_vm(request: VMCreateRequest):
    try:
        vm_data = await VMLifecycleKVM().create(
            name=request.name,
            vcpus=request.vcpus,
            memory_mb=request.memory_mb,
            image_path=request.image_path,
        )
        return vm_data
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/{vm_id}", response_model=VMResponse)
async def get_vm(vm_id: str):
    vm: Any = await VMLifecycleKVM().get(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm

@router.delete("/{vm_id}")
async def delete_vm(vm_id: str):
    result = await VMLifecycleKVM().delete(vm_id)
    if not result:
        raise HTTPException(status_code=404, detail="VM not found")
    return {"result": True}
