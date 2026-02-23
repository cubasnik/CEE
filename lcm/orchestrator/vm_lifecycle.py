from lcm.drivers.openstack_driver import OpenStackDriver


class VMLifecycle:
    def __init__(self, driver: OpenStackDriver):
        self.driver = driver

    async def create(
        self,
        *,
        name: str,
        image: str,
        flavor: str,
        network: str,
        host: str,
        user_data: str | None = None,
    ) -> dict:
        _ = (host, user_data)
        vm = await self.driver.create_server(
            name=name,
            image_name=image,
            flavor_name=flavor,
            network_name=network,
        )
        return vm

    async def get(self, vm_id: str) -> dict | None:
        return await self.driver.get_server(vm_id)

    async def list(self) -> list[dict]:
        """Список ВМ"""
        # Delegate to driver if available
        if hasattr(self.driver, "list_servers"):
            result = self.driver.list_servers()
            return result or []
        return []

    async def delete(self, vm_id: str) -> bool:
        """Удаление ВМ по ID"""
        if hasattr(self.driver, "delete_server"):
            return self.driver.delete_server(vm_id)
        return False
