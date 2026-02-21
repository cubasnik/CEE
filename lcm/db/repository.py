from lcm.db.models import Host


class HostRepository:
    def __init__(self) -> None:
        self._hosts: list[Host] = [
            Host(name="compute-01", free_ram=16384, free_cpu=8, active=True),
            Host(name="compute-02", free_ram=8192, free_cpu=4, active=True),
            Host(name="compute-03", free_ram=2048, free_cpu=1, active=True),
            Host(name="compute-04", free_ram=32768, free_cpu=16, active=False),
        ]

    async def get_active_hosts(self) -> list[Host]:
        return [host for host in self._hosts if host.active]
