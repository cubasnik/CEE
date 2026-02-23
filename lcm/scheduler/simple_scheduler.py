class SimpleScheduler:
    async def select_host(self, flavor: str) -> str:
        return f"auto-host-for-{flavor}"
