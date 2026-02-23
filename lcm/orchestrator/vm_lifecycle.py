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
