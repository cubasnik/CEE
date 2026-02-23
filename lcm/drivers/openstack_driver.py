from typing import Optional

import openstack


class OpenStackDriver:
    def __init__(self):
        self.conn = openstack.connect()

    async def create_server(
        self,
        name: str,
        image_name: str,
        flavor_name: str,
        network_name: str,
        availability_zone: Optional[str] = None,
    ) -> dict:
        """Создание сервера в OpenStack"""

        image = self.conn.compute.find_image(image_name)
        if image is None:
            raise ValueError(f"Image '{image_name}' not found")

        flavor = self.conn.compute.find_flavor(flavor_name)
        if flavor is None:
            raise ValueError(f"Flavor '{flavor_name}' not found")

        network = self.conn.network.find_network(network_name)
        if network is None:
            raise ValueError(f"Network '{network_name}' not found")

        server = self.conn.compute.create_server(
            name=name,
            image_id=image.id,
            flavor_id=flavor.id,
            networks=[{"uuid": network.id}],
            availability_zone=availability_zone,
        )

        server = self.conn.compute.wait_for_server(server)

        return {
            "id": server.id,
            "name": server.name,
            "status": server.status,
            "ip_addresses": self._extract_ips(server),
            "created_at": getattr(server, "created_at", ""),
        }

    async def get_server(self, vm_id: str) -> dict | None:
        server = self.conn.compute.get_server(vm_id)
        if server is None:
            return None

        return {
            "id": server.id,
            "name": server.name,
            "status": server.status,
            "ip_addresses": self._extract_ips(server),
            "created_at": getattr(server, "created_at", ""),
        }

    def _extract_ips(self, server) -> list[str]:
        """Извлечение IP-адресов из структуры сервера"""
        ips: list[str] = []
        for _network_name, addresses in server.addresses.items():
            for addr in addresses:
                ip = addr.get("addr")
                if ip:
                    ips.append(ip)
        return ips
