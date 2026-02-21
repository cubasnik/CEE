import random
from typing import Optional

from lcm.db.repository import HostRepository


class VMScheduler:
    def __init__(self, host_repo: HostRepository):
        self.host_repo = host_repo

    async def select_host(self, flavor_name: str) -> Optional[str]:
        """
        Выбор хоста для размещения ВМ
        Самая простая стратегия: случайный хост с достаточным количеством ресурсов
        """
        _ = flavor_name

        hosts = await self.host_repo.get_active_hosts()
        eligible_hosts = [h for h in hosts if h.free_ram > 4096 and h.free_cpu > 2]

        if not eligible_hosts:
            return None

        return random.choice(eligible_hosts).name
