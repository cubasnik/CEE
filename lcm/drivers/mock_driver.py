"""Mock driver for development without libvirt"""

import time

class MockDriver:
    """Mock driver для тестирования API с полной поддержкой операций"""
    
    def __init__(self):
        self.vms = {}
        self.vm_states = {}  # отслеживаем состояние ВМ
        print("🔧 Using MockDriver for development")
    
    def list_vms(self):
        """Возвращает список всех ВМ"""
        return list(self.vms.values())
    
    def get_server(self, vm_id):
        """Получить информацию о конкретной ВМ"""
        return self.vms.get(vm_id)
    
    def create_server(self, name, image_name, flavor_name, network_name, **kwargs):
        """Создать новую ВМ (в остановленном состоянии)"""
        vm_id = f"vm-{len(self.vms) + 1}"
        
        # Определяем начальное состояние на основе параметра autostart
        autostart = kwargs.get('autostart', False)
        
        if autostart:
            state = "running"
            status = "ACTIVE"
        else:
            state = "stopped"
            status = "SHUTOFF"
        
        vm = {
            "id": vm_id,
            "name": name,
            "status": status,
            "state": state,
            "image": image_name,
            "flavor": flavor_name,
            "network": network_name,
            "ip_addresses": ["192.168.1.100"] if state == "running" else [],
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vcpus": kwargs.get('vcpus', 2),
            "memory": kwargs.get('memory', 2048),
            "autostart": autostart
        }
        self.vms[vm_id] = vm
        self.vm_states[vm_id] = state
        return vm
    
    # Алиас для create_vm (для совместимости с API)
    def create_vm(self, name, image, vcpus=1, memory=1024, **kwargs):
        """Создание ВМ через альтернативный метод"""
        return self.create_server(
            name=name,
            image_name=image,
            flavor_name=f"custom-{vcpus}vcpu-{memory}mb",
            network_name="default",
            vcpus=vcpus,
            memory=memory,
            **kwargs
        )
    
    def delete_server(self, vm_id):
        """Удалить ВМ"""
        if vm_id in self.vms:
            del self.vms[vm_id]
            if vm_id in self.vm_states:
                del self.vm_states[vm_id]
            return True
        return False
    
    # Методы для управления ВМ
    
    def start_vm(self, vm_id):
        """Запустить ВМ"""
        if vm_id in self.vms:
            self.vm_states[vm_id] = "running"
            self.vms[vm_id]["status"] = "ACTIVE"
            self.vms[vm_id]["state"] = "running"
            # При запуске ВМ получает IP
            self.vms[vm_id]["ip_addresses"] = ["192.168.1.100"]
            return True
        return False
    
    def stop_vm(self, vm_id):
        """Остановить ВМ"""
        if vm_id in self.vms:
            self.vm_states[vm_id] = "stopped"
            self.vms[vm_id]["status"] = "SHUTOFF"
            self.vms[vm_id]["state"] = "stopped"
            # При остановке IP исчезает
            self.vms[vm_id]["ip_addresses"] = []
            return True
        return False
    
    def reboot_vm(self, vm_id):
        """Перезагрузить ВМ"""
        if vm_id in self.vms and self.vm_states.get(vm_id) == "running":
            # Имитация перезагрузки
            old_ip = self.vms[vm_id].get("ip_addresses", [])
            self.vm_states[vm_id] = "rebooting"
            self.vms[vm_id]["status"] = "REBOOT"
            self.vms[vm_id]["state"] = "rebooting"
            self.vms[vm_id]["ip_addresses"] = []  # IP временно пропадает
            
            # В реальности здесь была бы задержка, но для мока сразу возвращаем
            self.vm_states[vm_id] = "running"
            self.vms[vm_id]["status"] = "ACTIVE"
            self.vms[vm_id]["state"] = "running"
            self.vms[vm_id]["ip_addresses"] = old_ip or ["192.168.1.100"]
            return True
        return False
    
    def pause_vm(self, vm_id):
        """Приостановить ВМ"""
        if vm_id in self.vms and self.vm_states.get(vm_id) == "running":
            self.vm_states[vm_id] = "paused"
            self.vms[vm_id]["status"] = "PAUSED"
            self.vms[vm_id]["state"] = "paused"
            return True
        return False
    
    def resume_vm(self, vm_id):
        """Возобновить ВМ"""
        if vm_id in self.vms and self.vm_states.get(vm_id) == "paused":
            self.vm_states[vm_id] = "running"
            self.vms[vm_id]["status"] = "ACTIVE"
            self.vms[vm_id]["state"] = "running"
            return True
        return False
    
    def get_vm_status(self, vm_id):
        """Получить статус ВМ"""
        if vm_id in self.vms:
            return {
                "id": vm_id,
                "status": self.vms[vm_id]["status"],
                "state": self.vm_states.get(vm_id, "unknown"),
                "ip_addresses": self.vms[vm_id].get("ip_addresses", [])
            }
        return None
    
    def _extract_ips(self, server):
        """Извлечение IP-адресов (для совместимости)"""
        if isinstance(server, dict):
            return server.get("ip_addresses", [])
        return ["192.168.1.100"]
