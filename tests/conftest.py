import pytest
from unittest.mock import Mock, patch

@pytest.fixture(autouse=True)
def mock_openstack_connection():
    """Мокируем OpenStack connection для всех тестов"""
    with patch('lcm.drivers.openstack_driver.openstack.connect') as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        yield mock_conn

@pytest.fixture
def sample_vm_request():
    """Фикстура с валидным запросом на создание ВМ"""
    return {
        "name": "test-vm",
        "image": "ubuntu-22.04",
        "flavor": "m1.small",
        "network": "private-network"
    }

@pytest.fixture
def sample_host():
    """Фикстура с примером хоста"""
    return {
        "name": "compute-01",
        "ip_address": "192.168.1.10",
        "free_cpu": 16,
        "free_ram": 32768
    }
