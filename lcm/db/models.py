from dataclasses import dataclass


class _Metadata:
    def create_all(self, bind=None) -> None:
        return None


class Base:
    metadata = _Metadata()


@dataclass
class Host:
    name: str
    free_ram: int
    free_cpu: int
    active: bool = True
