
import pytest
from typing import Dict
from unittest.mock import AsyncMock

@pytest.fixture
def mock_openstack_driver():
    """Мок для OpenStack драйвера"""
    mock = AsyncMock()
    
    # Настраиваем возвращаемые значения для разных методов
    mock.create_server.return_value = {
        "id": "test-vm-id-123",
        "name": "test-vm",
        "status": "ACTIVE",
        "ip_addresses": ["192.168.1.100"]
    }
    
    mock.get_server.return_value = {
        "id": "test-vm-id-123",
        "name": "test-vm",
        "status": "ACTIVE",
        "ip_addresses": ["192.168.1.100"]
    }
    
    mock.delete_server.return_value = True
    
    return mock

@pytest.fixture
def sample_vm_request() -> Dict:
    """Пример запроса на создание ВМ"""
    return {
        "name": "test-vm",
        "image": "ubuntu-22.04",
        "flavor": "m1.small",
        "network": "private-network",
        "user_data": None
    }

@pytest.fixture
def sample_host() -> Dict:
    """Пример данных о физическом хосте"""
    return {
        "name": "compute-01",
        "status": "active",
        "total_ram": 65536,  # 64GB
        "free_ram": 32768,    # 32GB
        "total_cpu": 32,
        "free_cpu": 16,
        "ip_address": "192.168.1.10"
    }
