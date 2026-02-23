from lcm.drivers.kvm.kvm_driver import KVMDriver
from typing import Optional

class VMLifecycleKVM:
    def __init__(self, driver: Optional[KVMDriver] = None):
        self.driver = driver or KVMDriver()

    async def create(self, *, name: str, vcpus: int, memory_mb: int, image_path: str) -> dict:
        vm_id = self.driver.create_vm(name=name, vcpus=vcpus, memory_mb=memory_mb, image_path=image_path)
        if not vm_id:
            raise RuntimeError("Failed to create VM")
        return {"id": vm_id, "name": name, "status": "running", "ip_addresses": [], "created_at": ""}

    async def get(self, vm_id: str) -> dict | None:
        vms = self.driver.list_vms()
        for vm in vms:
            if vm["id"] == vm_id:
                return vm
        return None

    async def list(self) -> list:
        return self.driver.list_vms()

    async def delete(self, vm_id: str) -> bool:
        return self.driver.delete_vm(vm_id)
