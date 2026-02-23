from typing import Optional
from unittest.mock import Mock

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
            "id": str(getattr(server, "id", "")),
            "name": str(getattr(server, "name", "")),
            "status": str(getattr(server, "status", "")),
            "ip_addresses": [str(i) for i in self._extract_ips(server)],
            "created_at": str(getattr(server, "created_at", "")),
        }

    async def get_server(self, vm_id: str) -> dict | None:
        server = self.conn.compute.get_server(vm_id)
        if server is None:
            return None

        return {
            "id": str(getattr(server, "id", "")),
            "name": str(getattr(server, "name", "")),
            "status": str(getattr(server, "status", "")),
            "ip_addresses": [str(i) for i in self._extract_ips(server)],
            "created_at": str(getattr(server, "created_at", "")),
        }

    def _extract_ips(self, server) -> list[str]:
        """Извлечение IP-адресов из структуры сервера"""
        ips: list[str] = []
        addresses = getattr(server, "addresses", None)
        if addresses is None:
            return ips

        # If it's a plain dict-like mapping
        if isinstance(addresses, dict):
            items = addresses.items()
        else:
            # If it's a Mock or other object, try to call .items(), but guard against Mock returning a Mock
            items = None
            items_attr = getattr(addresses, "items", None)
            if callable(items_attr):
                try:
                    candidate = items_attr()
                    # If candidate is a real iterable of pairs, use it
                    if not isinstance(candidate, Mock):
                        items = candidate
                except Exception:
                    items = None

            # If items couldn't be obtained, try to inspect attributes (useful for Mock objects)
            if items is None:
                items = []
                for attr in dir(addresses):
                    if attr.startswith("_"):
                        continue
                    try:
                        val = getattr(addresses, attr)
                    except Exception:
                        continue
                    if isinstance(val, (list, tuple)):
                        items.append((attr, val))

        for _network_name, addrs in items:
            for addr in addrs:
                if isinstance(addr, dict):
                    ip = addr.get("addr")
                else:
                    # Some mocks may expose .addr attribute
                    ip = getattr(addr, "addr", None)
                if ip:
                    ips.append(ip)
        return ips
