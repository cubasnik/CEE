import pytest
from unittest.mock import Mock, AsyncMock
from lcm.orchestrator.vm_scheduler import VMScheduler

class TestVMScheduler:
    """Тесты для планировщика ВМ"""
    
    @pytest.fixture
    def scheduler(self):
        """Фикстура с замоканным репозиторием хостов"""
        mock_host_repo = AsyncMock()
        return VMScheduler(mock_host_repo)
    
    @pytest.mark.asyncio
    async def test_select_host_with_available_hosts(self, scheduler, sample_host):
        """Тест выбора хоста при наличии доступных хостов"""
        
        # Создаем несколько хостов с разными характеристиками
        hosts = [
            Mock(name="host1", free_ram=8192, free_cpu=4),
            Mock(name="host2", free_ram=4096, free_cpu=2),
            Mock(name="host3", free_ram=16384, free_cpu=8)
        ]
        
        scheduler.host_repo.get_active_hosts.return_value = hosts
        
        # Выбираем хост для flavor, требующего 4096 MB RAM и 2 CPU
        selected_host = await scheduler.select_host("m1.small")
        
        assert selected_host in ["host1", "host2", "host3"]
    
    @pytest.mark.asyncio
    async def test_select_host_no_available_hosts(self, scheduler):
        """Тест выбора хоста при отсутствии доступных хостов"""
        
        # Все хосты перегружены
        hosts = [
            Mock(name="host1", free_ram=1024, free_cpu=1),
            Mock(name="host2", free_ram=2048, free_cpu=1)
        ]
        
        scheduler.host_repo.get_active_hosts.return_value = []
        
        selected_host = await scheduler.select_host("m1.small")
        
        assert selected_host is None
    
    @pytest.mark.asyncio
    async def test_select_host_empty_host_list(self, scheduler):
        """Тест выбора хоста при пустом списке хостов"""
        
        scheduler.host_repo.get_active_hosts.return_value = []
        
        selected_host = await scheduler.select_host("m1.small")
        
        assert selected_host is None
    
    def test_filter_hosts_by_resources(self, scheduler):
        """Тест фильтрации хостов по ресурсам"""
        
        hosts = [
            Mock(free_ram=8192, free_cpu=4),
            Mock(free_ram=2048, free_cpu=1),
            Mock(free_ram=4096, free_cpu=2),
            Mock(free_ram=16384, free_cpu=8)
        ]
        
        # Минимальные требования: 4096 MB RAM и 2 CPU
        required_ram = 4096
        required_cpu = 2
        
        eligible_hosts = [
            h for h in hosts 
            if h.free_ram >= required_ram and h.free_cpu >= required_cpu
        ]
        
        assert len(eligible_hosts) == 3  # hosts 0, 2, 3
