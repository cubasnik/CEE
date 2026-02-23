from typing import Any, Protocol
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from lcm.drivers.openstack_driver import OpenStackDriver
from lcm.orchestrator.vm_lifecycle import VMLifecycle


class VMResponse(BaseModel):
    id: str
    name: str
    status: str
    ip_addresses: list[str]
    created_at: str


class VMCreateRequest(BaseModel):
    name: str
    image: str  # Имя образа (ubuntu-22.04, windows-2019)
    flavor: str  # Тип ВМ (cpu, ram, disk) — m1.small, m1.medium
    network: str  # ID или имя сети
    user_data: str | None = None  # Cloud-init скрипт


class HostScheduler(Protocol):
    async def select_host(self, flavor: str) -> str | None:
        ...


def get_vm_lifecycle(request: Request) -> VMLifecycle:
    # Если в тестах задан override в app.dependency_overrides, используй его
    override = getattr(request.app, "dependency_overrides", {}).get(get_vm_lifecycle)
    if override:
        return override()
    # По умолчанию создаём реальный lifecycle
    driver = OpenStackDriver()
    return VMLifecycle(driver)


def get_scheduler(request: Request) -> HostScheduler:
    # Respect app.dependency_overrides when tests set an override
    override = getattr(request.app, "dependency_overrides", {}).get(get_scheduler)
    if override:
        return override()

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler is not configured")
    return scheduler


router = APIRouter(prefix="/vms", tags=["vms"])


@router.get("/", response_model=list[VMResponse])
async def list_vms(vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle)):
    """Получение списка всех ВМ"""
    vms = await vm_lifecycle.list()
    return vms


@router.post("/", response_model=VMResponse)
async def create_vm(
    request: VMCreateRequest,
    vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle),
    scheduler: HostScheduler = Depends(get_scheduler),
):
    """Создание новой виртуальной машины"""
    try:
        host = await scheduler.select_host(request.flavor)
        if host is None:
            raise HTTPException(status_code=503, detail="No eligible host available")
        vm_data = await vm_lifecycle.create(
            name=request.name,
            image=request.image,
            flavor=request.flavor,
            network=request.network,
            host=host,
            user_data=request.user_data,
        )
        return vm_data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{vm_id}", response_model=VMResponse)
async def get_vm(
    vm_id: str,
    vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle),
):
    """Получение информации о ВМ"""
    vm: Any = await vm_lifecycle.get(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm


@router.delete("/{vm_id}")
async def delete_vm(vm_id: str, vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle)):
    """Удаление ВМ по ID"""
    result = await vm_lifecycle.delete(vm_id)
    if not result:
        raise HTTPException(status_code=404, detail="VM not found")
    return {"result": True}

@router.delete("/{vm_id}")
async def delete_vm(vm_id: str, vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle)):
    """Удаление ВМ по ID"""
    result = await vm_lifecycle.delete(vm_id)
    if not result:
        raise HTTPException(status_code=404, detail="VM not found")
    return {"result": True}



class VMResponse(BaseModel):
    id: str
    name: str
    status: str
    ip_addresses: list[str]
    created_at: str

class VMCreateRequest(BaseModel):
    name: str
    image: str  # Имя образа (ubuntu-22.04, windows-2019)
    flavor: str  # Тип ВМ (cpu, ram, disk) — m1.small, m1.medium
    network: str  # ID или имя сети
    user_data: str | None = None  # Cloud-init скрипт



class HostScheduler(Protocol):
    async def select_host(self, flavor: str) -> str | None:
        ...

def get_vm_lifecycle() -> VMLifecycle:
    # По умолчанию создаём реальный lifecycle, но в тестах функция полностью подменяется
    driver = OpenStackDriver()
    return VMLifecycle(driver)

def get_scheduler(request: Request) -> HostScheduler:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler is not configured")
    return scheduler


@router.post("/", response_model=VMResponse)
async def create_vm(
    request: VMCreateRequest,
    vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle),
    scheduler: HostScheduler = Depends(get_scheduler),
):
    """Создание новой виртуальной машины"""
    try:
        host = await scheduler.select_host(request.flavor)
        if host is None:
            raise HTTPException(status_code=503, detail="No eligible host available")
        vm_data = await vm_lifecycle.create(
            name=request.name,
            image=request.image,
            flavor=request.flavor,
            network=request.network,
            host=host,
            user_data=request.user_data,
        )
        return vm_data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{vm_id}", response_model=VMResponse)
async def get_vm(
    vm_id: str,
    vm_lifecycle: VMLifecycle = Depends(get_vm_lifecycle),
):
    """Получение информации о ВМ"""
    vm: Any = await vm_lifecycle.get(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm
