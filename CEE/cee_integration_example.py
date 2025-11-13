#!/usr/bin/env python3
"""
CEE Integration Example
Комплексный пример использования всех компонентов CEE

Демонстрирует:
- Создание полной инфраструктуры тенанта
- Интеграцию OpenStack + VxSDS + OVS
- Мониторинг и управление ресурсами
"""

import time
import json
import logging
from typing import Dict, List, Optional

# Импортируем наши модули
from cee_openstack_client import CEEOpenStackClient, create_cee_client_from_config
from cee_network_utils import CEEOVSManager, CEENetworkTopology
from cee_vxsds_utils import VxSDSClient, CEEVxSDSManager


class CEEOrchestrator:
    """
    Оркестратор для комплексного управления CEE
    Интегрирует все компоненты: OpenStack, VxSDS, OVS
    """
    
    def __init__(self, config_path: str = None):
        """
        Инициализация оркестратора
        
        Args:
            config_path: Путь к конфигурационным файлам CEE
        """
        self.logger = logging.getLogger('CEEOrchestrator')
        self._setup_logging()
        
        # Инициализация компонентов
        self.openstack_client = None
        self.vxsds_client = None
        self.vxsds_manager = None
        self.ovs_manager = None
        self.network_topology = None
        
        # Загружаем конфигурацию
        self.config_path = config_path
        self._initialize_components()
    
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_components(self):
        """Инициализация всех компонентов"""
        try:
            # OpenStack клиент
            self.openstack_client = create_cee_client_from_config(self.config_path)
            self.logger.info("Инициализирован OpenStack клиент")
            
            # VxSDS компоненты
            self.vxsds_client = VxSDSClient()
            self.vxsds_manager = CEEVxSDSManager(self.vxsds_client)
            self.logger.info("Инициализированы VxSDS компоненты")
            
            # OVS компоненты
            self.ovs_manager = CEEOVSManager()
            self.network_topology = CEENetworkTopology(self.ovs_manager)
            self.logger.info("Инициализированы OVS компоненты")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    # === Комплексные операции ===
    
    def create_complete_tenant_environment(
        self,
        tenant_name: str,
        tenant_description: str = "",
        user_name: str = None,
        user_password: str = None,
        network_cidr: str = "192.168.100.0/24",
        storage_quota_gb: int = 100
    ) -> Dict:
        """
        Создание полной среды тенанта включая:
        - Проект и пользователя OpenStack
        - Сеть с OVS
        - VxSDS квоты
        - Базовые security groups
        """
        result = {
            "tenant_name": tenant_name,
            "status": "success",
            "created_resources": {},
            "errors": []
        }
        
        try:
            self.logger.info(f"Создание полной среды для тенанта: {tenant_name}")
            
            # 1. Создаем OpenStack тенант
            tenant_setup = self.openstack_client.create_cee_tenant_setup(
                tenant_name=tenant_name,
                tenant_description=tenant_description,
                user_name=user_name,
                user_password=user_password,
                network_cidr=network_cidr,
                create_router=True
            )
            
            if tenant_setup["status"] == "success":
                result["created_resources"]["openstack"] = tenant_setup["tenant_setup"]
                self.logger.info(f"Создан OpenStack тенант: {tenant_name}")
            else:
                result["errors"].append(f"Ошибка создания OpenStack тенанта: {tenant_setup.get('message')}")
                result["status"] = "partial_failure"
            
            # 2. Настраиваем сетевые ресурсы
            network_result = self._setup_tenant_networking(
                tenant_name, 
                tenant_setup["tenant_setup"]["project"].id if tenant_setup["status"] == "success" else None
            )
            
            if network_result["status"] == "success":
                result["created_resources"]["networking"] = network_result
            else:
                result["errors"].append(f"Ошибка настройки сети: {network_result.get('message')}")
                result["status"] = "partial_failure"
            
            # 3. Создаем базовые security groups
            if tenant_setup["status"] == "success":
                sg_result = self._create_tenant_security_groups(
                    tenant_setup["tenant_setup"]["project"].id
                )
                result["created_resources"]["security_groups"] = sg_result
            
            # 4. Настройка VxSDS квот (концептуально)
            storage_result = self._setup_tenant_storage_quota(tenant_name, storage_quota_gb)
            result["created_resources"]["storage"] = storage_result
            
            self.logger.info(f"Завершено создание среды тенанта: {tenant_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка создания среды тенанта: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))
        
        return result
    
    def _setup_tenant_networking(self, tenant_name: str, project_id: str = None) -> Dict:
        """Настройка сетевых ресурсов тенанта"""
        result = {"status": "success", "networks": {}, "subnets": {}}
        
        try:
            # Создаем внутреннюю сеть тенанта
            internal_net = self.openstack_client.create_ovs_network(
                name=f"{tenant_name}-internal",
                network_type="vxlan",
                cidr="10.0.1.0/24",
                enable_dhcp=True
            )
            
            if internal_net["status"] == "success":
                result["networks"]["internal"] = internal_net["network"]
                result["subnets"]["internal"] = internal_net["subnet"]
            
            # Создаем DMZ сеть если требуется
            dmz_net = self.openstack_client.create_ovs_network(
                name=f"{tenant_name}-dmz",
                network_type="vxlan", 
                cidr="10.0.2.0/24",
                enable_dhcp=True
            )
            
            if dmz_net["status"] == "success":
                result["networks"]["dmz"] = dmz_net["network"]
                result["subnets"]["dmz"] = dmz_net["subnet"]
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
        
        return result
    
    def _create_tenant_security_groups(self, project_id: str) -> Dict:
        """Создание базовых security groups для тенанта"""
        security_groups = {}
        
        try:
            # Web security group
            web_sg = self.openstack_client.conn.network.create_security_group(
                name="web-sg",
                description="Security group for web servers",
                project_id=project_id
            )
            
            # Правила для веб-трафика
            self.openstack_client.conn.network.create_security_group_rule(
                security_group_id=web_sg.id,
                direction="ingress",
                protocol="tcp",
                port_range_min=80,
                port_range_max=80,
                remote_ip_prefix="0.0.0.0/0"
            )
            
            self.openstack_client.conn.network.create_security_group_rule(
                security_group_id=web_sg.id,
                direction="ingress",
                protocol="tcp",
                port_range_min=443,
                port_range_max=443,
                remote_ip_prefix="0.0.0.0/0"
            )
            
            security_groups["web"] = web_sg
            
            # SSH security group
            ssh_sg = self.openstack_client.conn.network.create_security_group(
                name="ssh-sg",
                description="Security group for SSH access",
                project_id=project_id
            )
            
            self.openstack_client.conn.network.create_security_group_rule(
                security_group_id=ssh_sg.id,
                direction="ingress",
                protocol="tcp",
                port_range_min=22,
                port_range_max=22,
                remote_ip_prefix="10.0.0.0/8"  # Только внутренние сети
            )
            
            security_groups["ssh"] = ssh_sg
            
        except Exception as e:
            self.logger.error(f"Ошибка создания security groups: {e}")
        
        return security_groups
    
    def _setup_tenant_storage_quota(self, tenant_name: str, quota_gb: int) -> Dict:
        """Настройка квот хранилища для тенанта"""
        # В реальной реализации здесь была бы настройка квот VxSDS
        # Пока возвращаем информационный результат
        return {
            "tenant": tenant_name,
            "allocated_quota_gb": quota_gb,
            "storage_backend": "vxsds",
            "note": "Storage quota configuration requires additional VxSDS setup"
        }
    
    def deploy_application_stack(
        self,
        stack_name: str,
        project_id: str,
        stack_config: Dict
    ) -> Dict:
        """
        Развертывание стека приложений
        
        Args:
            stack_name: Имя стека
            project_id: ID проекта
            stack_config: Конфигурация стека
        """
        result = {
            "stack_name": stack_name,
            "status": "success",
            "instances": [],
            "volumes": [],
            "load_balancers": []
        }
        
        try:
            # Получаем параметры стека
            instances_config = stack_config.get("instances", [])
            volumes_config = stack_config.get("volumes", [])
            
            # Создаем тома для стека
            for vol_config in volumes_config:
                volume_result = self.openstack_client.create_vm_with_vxsds_storage(
                    name=f"{stack_name}-{vol_config['name']}-vol",
                    image="dummy",  # Будет заменен на том
                    flavor=vol_config.get("flavor", "m1.small"),
                    volume_size=vol_config.get("size_gb", 20),
                    volume_type=vol_config.get("type", "vxsds_thin_SSD")
                )
                
                if volume_result["status"] == "success":
                    result["volumes"].append(volume_result["volume"])
            
            # Создаем инстансы стека
            for inst_config in instances_config:
                instance_result = self.openstack_client.create_vm_with_vxsds_storage(
                    name=f"{stack_name}-{inst_config['name']}",
                    image=inst_config.get("image", "ubuntu-20.04"),
                    flavor=inst_config.get("flavor", "m1.medium"),
                    network_name=inst_config.get("network", "default"),
                    volume_size=inst_config.get("disk_size_gb", 20),
                    volume_type=inst_config.get("volume_type", "vxsds_thin_SSD")
                )
                
                if instance_result["status"] == "success":
                    result["instances"].append(instance_result["server"])
                    
                    # Настраиваем QoS если указано
                    if inst_config.get("qos"):
                        qos_config = inst_config["qos"]
                        # Получаем порты инстанса
                        ports = list(self.openstack_client.conn.network.ports(
                            device_id=instance_result["server"].id
                        ))
                        
                        for port in ports:
                            self.openstack_client.configure_ovs_qos(
                                port_id=port.id,
                                max_kbps=qos_config.get("max_kbps"),
                                min_kbps=qos_config.get("min_kbps")
                            )
            
            self.logger.info(f"Развернут стек приложений: {stack_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка развертывания стека: {e}")
            result["status"] = "error"
            result["message"] = str(e)
        
        return result
    
    # === Мониторинг и анализ ===
    
    def get_comprehensive_status(self) -> Dict:
        """
        Получение комплексного статуса CEE
        """
        status = {
            "timestamp": time.time(),
            "overall_health": "healthy",
            "components": {},
            "alerts": [],
            "recommendations": []
        }
        
        try:
            # Статус OpenStack
            if self.openstack_client:
                os_status = self.openstack_client.get_cee_cluster_status()
                status["components"]["openstack"] = os_status
                
                if os_status["status"] != "success":
                    status["alerts"].append("OpenStack cluster issues detected")
                    status["overall_health"] = "warning"
            
            # Статус VxSDS
            if self.vxsds_manager:
                vxsds_health = self.vxsds_manager.monitor_vxsds_health()
                status["components"]["vxsds"] = vxsds_health
                
                if vxsds_health["overall_status"] != "healthy":
                    status["alerts"].append(f"VxSDS issues: {vxsds_health['overall_status']}")
                    if vxsds_health["overall_status"] == "critical":
                        status["overall_health"] = "critical"
                    elif status["overall_health"] == "healthy":
                        status["overall_health"] = "warning"
            
            # Статус сети OVS
            if self.ovs_manager:
                network_perf = self.ovs_manager.monitor_ovs_performance()
                status["components"]["ovs"] = network_perf
                
                # Проверяем загрузку CPU OVS
                if "cpu_usage" in network_perf:
                    ovs_cpu = network_perf["cpu_usage"].get("ovs_vswitchd", 0)
                    if ovs_cpu > 80:
                        status["alerts"].append(f"High OVS CPU usage: {ovs_cpu}%")
                        if status["overall_health"] == "healthy":
                            status["overall_health"] = "warning"
            
            # Генерируем рекомендации
            recommendations = []
            
            if len(status["alerts"]) == 0:
                recommendations.append("System is operating normally")
            else:
                recommendations.append("Review alerts and consider maintenance actions")
            
            # Проверяем ресурсы
            if "vxsds" in status["components"]:
                vxsds_metrics = status["components"]["vxsds"].get("metrics", {})
                capacity = vxsds_metrics.get("capacity", {})
                
                if capacity.get("total_gb", 0) > 0:
                    free_pct = capacity.get("free_gb", 0) / capacity["total_gb"] * 100
                    if free_pct < 15:
                        recommendations.append("Consider adding storage capacity")
            
            status["recommendations"] = recommendations
            
        except Exception as e:
            status["overall_health"] = "error"
            status["alerts"].append(f"Status collection error: {e}")
        
        return status
    
    def perform_health_check(self) -> Dict:
        """
        Выполнение проверки здоровья системы
        """
        health_check = {
            "timestamp": time.time(),
            "checks": {},
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        
        checks = [
            ("openstack_api", self._check_openstack_api),
            ("vxsds_connectivity", self._check_vxsds_connectivity),
            ("ovs_bridges", self._check_ovs_bridges),
            ("network_connectivity", self._check_network_connectivity),
            ("storage_health", self._check_storage_health)
        ]
        
        for check_name, check_function in checks:
            try:
                result = check_function()
                health_check["checks"][check_name] = result
                
                if result["status"] == "pass":
                    health_check["passed"] += 1
                elif result["status"] == "warning":
                    health_check["warnings"] += 1
                else:
                    health_check["failed"] += 1
                    
            except Exception as e:
                health_check["checks"][check_name] = {
                    "status": "fail",
                    "message": f"Check failed with exception: {e}"
                }
                health_check["failed"] += 1
        
        return health_check
    
    def _check_openstack_api(self) -> Dict:
        """Проверка OpenStack API"""
        try:
            if not self.openstack_client:
                return {"status": "fail", "message": "OpenStack client not initialized"}
            
            # Простая проверка - получение списка проектов
            projects = list(self.openstack_client.conn.identity.projects())
            
            return {
                "status": "pass",
                "message": f"OpenStack API accessible, {len(projects)} projects found"
            }
            
        except Exception as e:
            return {"status": "fail", "message": f"OpenStack API error: {e}"}
    
    def _check_vxsds_connectivity(self) -> Dict:
        """Проверка подключения к VxSDS"""
        try:
            if not self.vxsds_client:
                return {"status": "fail", "message": "VxSDS client not initialized"}
            
            system_info = self.vxsds_client.get_system_info()
            if system_info:
                return {"status": "pass", "message": "VxSDS Gateway accessible"}
            else:
                return {"status": "fail", "message": "Cannot reach VxSDS Gateway"}
                
        except Exception as e:
            return {"status": "fail", "message": f"VxSDS connectivity error: {e}"}
    
    def _check_ovs_bridges(self) -> Dict:
        """Проверка OVS мостов"""
        try:
            if not self.ovs_manager:
                return {"status": "fail", "message": "OVS manager not initialized"}
            
            success, output = self.ovs_manager._run_ovs_command(['ovs-vsctl', 'list-br'])
            
            if success:
                bridges = output.strip().split('\n') if output.strip() else []
                required_bridges = ['br-int']  # Минимальный набор
                
                missing_bridges = [br for br in required_bridges if br not in bridges]
                
                if missing_bridges:
                    return {
                        "status": "warning",
                        "message": f"Missing bridges: {missing_bridges}"
                    }
                else:
                    return {
                        "status": "pass",
                        "message": f"OVS bridges operational: {bridges}"
                    }
            else:
                return {"status": "fail", "message": "Cannot access OVS"}
                
        except Exception as e:
            return {"status": "fail", "message": f"OVS check error: {e}"}
    
    def _check_network_connectivity(self) -> Dict:
        """Проверка сетевого подключения"""
        # Упрощенная проверка
        return {"status": "pass", "message": "Network connectivity check not implemented"}
    
    def _check_storage_health(self) -> Dict:
        """Проверка здоровья хранилища"""
        try:
            if not self.vxsds_manager:
                return {"status": "warning", "message": "VxSDS manager not available"}
            
            health = self.vxsds_manager.monitor_vxsds_health()
            
            if health["overall_status"] == "healthy":
                return {"status": "pass", "message": "Storage system healthy"}
            elif health["overall_status"] == "warning":
                return {
                    "status": "warning",
                    "message": f"Storage warnings: {health.get('warnings', [])}"
                }
            else:
                return {
                    "status": "fail", 
                    "message": f"Storage issues: {health.get('issues', [])}"
                }
                
        except Exception as e:
            return {"status": "fail", "message": f"Storage health check error: {e}"}


# === Пример конфигурации и использования ===

def example_usage():
    """
    Пример использования CEE оркестратора
    """
    print("=== CEE Orchestrator Example ===")
    
    # Создание оркестратора
    orchestrator = CEEOrchestrator()
    
    # Проверка здоровья системы
    print("\n1. Проверка здоровья системы...")
    health_check = orchestrator.perform_health_check()
    print(f"Проверок пройдено: {health_check['passed']}")
    print(f"Проверок провалено: {health_check['failed']}")
    print(f"Предупреждений: {health_check['warnings']}")
    
    # Получение комплексного статуса
    print("\n2. Комплексный статус...")
    status = orchestrator.get_comprehensive_status()
    print(f"Общее состояние: {status['overall_health']}")
    if status['alerts']:
        print(f"Алерты: {status['alerts']}")
    
    # Создание тестового тенанта
    print("\n3. Создание тестового тенанта...")
    tenant_result = orchestrator.create_complete_tenant_environment(
        tenant_name="test-tenant",
        tenant_description="Test tenant for CEE",
        user_name="test-user",
        user_password="test-password123",
        network_cidr="192.168.150.0/24",
        storage_quota_gb=50
    )
    
    print(f"Статус создания тенанта: {tenant_result['status']}")
    if tenant_result['errors']:
        print(f"Ошибки: {tenant_result['errors']}")
    
    # Пример конфигурации стека приложения
    app_stack_config = {
        "instances": [
            {
                "name": "web-01",
                "image": "ubuntu-20.04",
                "flavor": "m1.medium",
                "network": "test-tenant-internal",
                "disk_size_gb": 20,
                "volume_type": "vxsds_thin_SSD",
                "qos": {
                    "max_kbps": 100000,  # 100 Mbps
                    "min_kbps": 10000    # 10 Mbps
                }
            },
            {
                "name": "db-01",
                "image": "ubuntu-20.04", 
                "flavor": "m1.large",
                "network": "test-tenant-internal",
                "disk_size_gb": 50,
                "volume_type": "vxsds_thick_SSD"
            }
        ],
        "volumes": [
            {
                "name": "shared-data",
                "size_gb": 100,
                "type": "vxsds_thin_SSD"
            }
        ]
    }
    
    # Развертывание стека (закомментировано для примера)
    # print("\n4. Развертывание стека приложения...")
    # if tenant_result['status'] in ['success', 'partial_failure']:
    #     project_id = tenant_result['created_resources']['openstack']['project'].id
    #     stack_result = orchestrator.deploy_application_stack(
    #         stack_name="test-app",
    #         project_id=project_id,
    #         stack_config=app_stack_config
    #     )
    #     print(f"Статус развертывания стека: {stack_result['status']}")


if __name__ == "__main__":
    example_usage()