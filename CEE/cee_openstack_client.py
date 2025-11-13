#!/usr/bin/env python3
"""
CEE OpenStack Client for Ericsson Cloud Execution Environment
Специализированный клиент для работы с OpenStack CEE с VxSDS и OVS

Поддерживает:
- VxSDS (Dell ScaleIO) storage backend
- Open vSwitch (OVS) networking без DPDK
- Ericsson LCM Infrastructure
"""

import os
import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# OpenStack SDK
from openstack import connect, enable_logging
from openstack.connection import Connection
from openstack.compute import Compute
from openstack.network import Network
from openstack.volume import Volume
from openstack.image import Image

# ScaleIO/VxSDS SDK
try:
    from pyscaleio import ScaleIO
    SCALEIO_AVAILABLE = True
except ImportError:
    SCALEIO_AVAILABLE = False
    print("Warning: pyscaleio module not found. VxSDS management features will be limited.")


@dataclass
class CEENetworkConfig:
    """Конфигурация сетей CEE"""
    lcm_ctrl_sp: str = "192.168.0.11/24"
    cee_ctrl_sp: str = "192.168.2.11/24" 
    glance_san_sp: str = "192.168.19.0/24"
    migration_san_sp: str = "192.168.14.0/24"
    swift_san_sp: str = "192.168.13.0/24"
    gluster_san_sp: str = "192.168.120.0/24"
    cee_om_sp: str = "10.16.33.144/28"
    lcm_om_sp: str = "10.16.33.192/28"
    
    # VxSDS networks
    vxsds_fe_san_pda: str = "192.168.17.0/24"
    vxsds_fe_san_pdb: str = "192.168.18.0/24"
    vxsds_be_san_pda: str = "192.168.15.0/24"
    vxsds_be_san_pdb: str = "192.168.16.0/24"
    
    # SDN networks
    sdnc_internal_sp: str = "192.168.70.0/24"
    sdnc_sbi_sp: str = "192.168.40.0/24"
    sdn_ul: str = "auto"  # VLAN 4086


@dataclass
class VxSDSConfig:
    """Конфигурация VxSDS"""
    cluster_name: str = "vxsds_full_openstack"
    password: str = "Ericsson123@"
    gateway_user: str = "admin"
    gateway_admin_password: str = "Ericsson123@"
    gateway_port: int = 4443
    gateway_be_ssl_port: int = 4445
    gateway_be_http_port: int = 81
    protection_domain: str = "protection_domain1"
    storage_pool: str = "pool1"


class CEEOpenStackClient:
    """
    Клиент для работы с Ericsson CEE OpenStack
    """
    
    def __init__(
        self,
        auth_url: str = "https://mokc01ltecee01-openstack.plte.evergy.com:5000/v3",
        username: str = "admin",
        password: str = None,
        project_name: str = "admin",
        user_domain_name: str = "Default",
        project_domain_name: str = "Default",
        region_name: str = "RegionOne",
        verify: bool = False
    ):
        """
        Инициализация CEE OpenStack клиента
        
        Args:
            auth_url: URL для аутентификации OpenStack
            username: Имя пользователя
            password: Пароль
            project_name: Имя проекта
            user_domain_name: Домен пользователя
            project_domain_name: Домен проекта
            region_name: Регион
            verify: Проверка SSL сертификатов
        """
        self.network_config = CEENetworkConfig()
        self.vxsds_config = VxSDSConfig()
        
        # Настройка логирования
        self._setup_logging()
        
        # Подключение к OpenStack
        self.conn = connect(
            auth_url=auth_url,
            username=username,
            password=password,
            project_name=project_name,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name,
            region_name=region_name,
            verify=verify
        )
        
        self.logger.info(f"Подключен к CEE OpenStack: {auth_url}")
        
        # Инициализация VxSDS клиента
        self.scaleio = None
        if SCALEIO_AVAILABLE:
            self._init_vxsds_client()
    
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CEEOpenStack')
    
    def _init_vxsds_client(self):
        """Инициализация клиента VxSDS"""
        try:
            # VxSDS Gateway обычно доступен через внутренний VIP
            gateway_ip = "192.168.2.13"  # openstack_int_vip из конфигурации
            
            self.scaleio = ScaleIO(
                api_url=f"https://{gateway_ip}:{self.vxsds_config.gateway_port}",
                username=self.vxsds_config.gateway_user,
                password=self.vxsds_config.gateway_admin_password,
                verify_ssl=False
            )
            self.logger.info("VxSDS клиент инициализирован")
        except Exception as e:
            self.logger.warning(f"Не удалось инициализировать VxSDS клиент: {e}")
    
    # === Управление виртуальными машинами ===
    
    def create_vm_with_vxsds_storage(
        self,
        name: str,
        image: str,
        flavor: str,
        network_name: str = "cee_ctrl_sp",
        volume_size: int = 20,
        volume_type: str = "vxsds_thin_SSD",
        availability_zone: str = None
    ) -> Dict:
        """
        Создание ВМ с VxSDS хранилищем
        
        Args:
            name: Имя ВМ
            image: Образ для запуска
            flavor: Размер ВМ
            network_name: Имя сети
            volume_size: Размер диска в ГБ
            volume_type: Тип VxSDS тома
            availability_zone: Зона доступности
        """
        try:
            # Получаем образ, flavor и сеть
            image_obj = self.conn.compute.find_image(image)
            flavor_obj = self.conn.compute.find_flavor(flavor)
            network_obj = self.conn.network.find_network(network_name)
            
            if not all([image_obj, flavor_obj, network_obj]):
                raise ValueError("Не найдены необходимые ресурсы")
            
            # Создаем загрузочный том из образа
            volume = self.conn.volume.create_volume(
                name=f"{name}-root-vol",
                size=volume_size,
                imageRef=image_obj.id,
                volume_type=volume_type,
                availability_zone=availability_zone
            )
            
            # Ждем создания тома
            volume = self.conn.volume.wait_for_status(volume, "available")
            self.logger.info(f"Создан VxSDS том: {volume.name}")
            
            # Создаем ВМ с загрузкой с тома
            server = self.conn.compute.create_server(
                name=name,
                image=None,  # Загрузка с тома
                flavor=flavor_obj.id,
                networks=[{"uuid": network_obj.id}],
                block_device_mapping=[{
                    "boot_index": 0,
                    "delete_on_termination": True,
                    "destination_type": "volume",
                    "source_type": "volume",
                    "uuid": volume.id
                }],
                availability_zone=availability_zone
            )
            
            server = self.conn.compute.wait_for_server(server)
            self.logger.info(f"Создана ВМ: {server.name} с VxSDS хранилищем")
            
            return {
                "server": server,
                "volume": volume,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка создания ВМ: {e}")
            return {"status": "error", "message": str(e)}
    
    def attach_vxsds_volume(self, server_id: str, volume_size: int, volume_type: str = "vxsds_thin_SSD") -> Dict:
        """
        Подключение дополнительного VxSDS тома к ВМ
        """
        try:
            # Создаем том
            volume = self.conn.volume.create_volume(
                name=f"additional-vol-{int(time.time())}",
                size=volume_size,
                volume_type=volume_type
            )
            
            volume = self.conn.volume.wait_for_status(volume, "available")
            
            # Подключаем к серверу
            self.conn.compute.create_volume_attachment(
                server=server_id,
                volume_id=volume.id
            )
            
            self.logger.info(f"Том {volume.id} подключен к серверу {server_id}")
            
            return {"volume": volume, "status": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения тома: {e}")
            return {"status": "error", "message": str(e)}
    
    # === Управление сетями OVS ===
    
    def create_ovs_network(
        self,
        name: str,
        network_type: str = "vlan",
        physical_network: str = "physnet1",
        segmentation_id: int = None,
        enable_dhcp: bool = True,
        cidr: str = None,
        gateway_ip: str = None
    ) -> Dict:
        """
        Создание сети с OVS
        
        Args:
            name: Имя сети
            network_type: Тип сети (vlan, vxlan, flat)
            physical_network: Физическая сеть
            segmentation_id: VLAN ID или VNI
            enable_dhcp: Включить DHCP
            cidr: Подсеть в формате CIDR
            gateway_ip: IP шлюза
        """
        try:
            # Создаем сеть
            network_args = {
                "name": name,
                "provider_network_type": network_type,
                "admin_state_up": True
            }
            
            if physical_network:
                network_args["provider_physical_network"] = physical_network
            
            if segmentation_id:
                network_args["provider_segmentation_id"] = segmentation_id
            
            network = self.conn.network.create_network(**network_args)
            
            # Создаем подсеть если указан CIDR
            subnet = None
            if cidr:
                subnet_args = {
                    "network_id": network.id,
                    "name": f"{name}-subnet",
                    "cidr": cidr,
                    "ip_version": 4,
                    "enable_dhcp": enable_dhcp
                }
                
                if gateway_ip:
                    subnet_args["gateway_ip"] = gateway_ip
                
                subnet = self.conn.network.create_subnet(**subnet_args)
                self.logger.info(f"Создана подсеть: {subnet.name}")
            
            self.logger.info(f"Создана OVS сеть: {network.name}")
            
            return {
                "network": network,
                "subnet": subnet,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка создания сети: {e}")
            return {"status": "error", "message": str(e)}
    
    def configure_ovs_qos(
        self,
        port_id: str,
        max_kbps: int = None,
        max_burst_kbps: int = None,
        min_kbps: int = None
    ) -> Dict:
        """
        Настройка QoS для OVS порта
        """
        try:
            # Создаем QoS политику
            qos_policy = self.conn.network.create_qos_policy(
                name=f"qos-policy-{int(time.time())}",
                description="Auto-generated QoS policy for CEE"
            )
            
            # Создаем правило ограничения пропускной способности
            if max_kbps:
                bandwidth_rule = self.conn.network.create_qos_bandwidth_limit_rule(
                    qos_policy=qos_policy.id,
                    max_kbps=max_kbps,
                    max_burst_kbps=max_burst_kbps or max_kbps
                )
            
            # Создаем правило минимальной пропускной способности
            if min_kbps:
                min_bandwidth_rule = self.conn.network.create_qos_minimum_bandwidth_rule(
                    qos_policy=qos_policy.id,
                    min_kbps=min_kbps
                )
            
            # Применяем политику к порту
            port = self.conn.network.update_port(
                port_id,
                qos_policy_id=qos_policy.id
            )
            
            self.logger.info(f"QoS настроен для порта: {port_id}")
            
            return {
                "qos_policy": qos_policy,
                "port": port,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки QoS: {e}")
            return {"status": "error", "message": str(e)}
    
    # === VxSDS управление ===
    
    def get_vxsds_statistics(self) -> Dict:
        """
        Получение статистики VxSDS
        """
        if not self.scaleio:
            return {"status": "error", "message": "VxSDS клиент недоступен"}
        
        try:
            # Получаем информацию о системе
            system_stats = self.scaleio.get_system_statistics()
            
            # Получаем информацию о protection domain
            protection_domains = self.scaleio.get_protection_domains()
            
            # Получаем информацию о пулах
            storage_pools = []
            for pd in protection_domains:
                pools = self.scaleio.get_storage_pools(protection_domain_id=pd['id'])
                storage_pools.extend(pools)
            
            return {
                "system_stats": system_stats,
                "protection_domains": protection_domains,
                "storage_pools": storage_pools,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения VxSDS статистики: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_vxsds_volumes(self) -> Dict:
        """
        Получение списка VxSDS томов
        """
        if not self.scaleio:
            return {"status": "error", "message": "VxSDS клиент недоступен"}
        
        try:
            volumes = self.scaleio.get_volumes()
            
            # Обогащаем информацию о томах
            enriched_volumes = []
            for volume in volumes:
                vol_info = {
                    "id": volume.get("id"),
                    "name": volume.get("name"),
                    "size_gb": volume.get("sizeInKb", 0) // 1024 // 1024,
                    "storage_pool": volume.get("storagePoolId"),
                    "creation_time": volume.get("creationTime"),
                    "mapped_sdcs": volume.get("mappedSdcInfo", [])
                }
                enriched_volumes.append(vol_info)
            
            return {
                "volumes": enriched_volumes,
                "total_count": len(enriched_volumes),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения VxSDS томов: {e}")
            return {"status": "error", "message": str(e)}
    
    # === Мониторинг и утилиты ===
    
    def get_cee_cluster_status(self) -> Dict:
        """
        Получение статуса CEE кластера
        """
        try:
            status = {
                "timestamp": time.time(),
                "openstack": {},
                "vxsds": {},
                "networks": {}
            }
            
            # OpenStack сервисы
            compute_services = list(self.conn.compute.services())
            network_agents = list(self.conn.network.agents())
            volume_services = list(self.conn.volume.services())
            
            status["openstack"] = {
                "compute_services": len([s for s in compute_services if s.status == "enabled"]),
                "network_agents": len([a for a in network_agents if a.admin_state_up]),
                "volume_services": len([s for s in volume_services if s.status == "enabled"]),
                "total_hypervisors": len(list(self.conn.compute.hypervisors())),
                "total_instances": len(list(self.conn.compute.servers()))
            }
            
            # VxSDS статистика
            vxsds_stats = self.get_vxsds_statistics()
            if vxsds_stats["status"] == "success":
                status["vxsds"] = {
                    "protection_domains": len(vxsds_stats["protection_domains"]),
                    "storage_pools": len(vxsds_stats["storage_pools"]),
                    "system_health": "ok"  # Упрощенно
                }
            
            # Сети
            networks = list(self.conn.network.networks())
            subnets = list(self.conn.network.subnets())
            
            status["networks"] = {
                "total_networks": len(networks),
                "total_subnets": len(subnets),
                "ovs_agents": len([a for a in network_agents if a.agent_type == "Open vSwitch agent"])
            }
            
            return {"status": "success", "cluster_status": status}
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса кластера: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_cee_tenant_setup(
        self,
        tenant_name: str,
        tenant_description: str = "",
        user_name: str = None,
        user_password: str = None,
        network_cidr: str = "192.168.100.0/24",
        create_router: bool = True
    ) -> Dict:
        """
        Создание полной настройки для тенанта в CEE
        """
        try:
            results = {}
            
            # Создаем проект
            project = self.conn.identity.create_project(
                name=tenant_name,
                description=tenant_description or f"CEE Tenant: {tenant_name}",
                enabled=True
            )
            results["project"] = project
            
            # Создаем пользователя если указан
            if user_name and user_password:
                user = self.conn.identity.create_user(
                    name=user_name,
                    password=user_password,
                    project_id=project.id,
                    enabled=True
                )
                
                # Добавляем роль member
                member_role = self.conn.identity.find_role("member")
                if member_role:
                    self.conn.identity.assign_project_role_to_user(
                        project.id, user.id, member_role.id
                    )
                
                results["user"] = user
            
            # Создаем сеть для тенанта
            network_result = self.create_ovs_network(
                name=f"{tenant_name}-network",
                network_type="vxlan",  # Используем VXLAN для tenant networks
                cidr=network_cidr
            )
            
            if network_result["status"] == "success":
                results["network"] = network_result["network"]
                results["subnet"] = network_result["subnet"]
                
                # Создаем роутер если требуется
                if create_router:
                    router = self.conn.network.create_router(
                        name=f"{tenant_name}-router",
                        admin_state_up=True,
                        project_id=project.id
                    )
                    
                    # Добавляем интерфейс к подсети
                    self.conn.network.add_interface_to_router(
                        router.id,
                        subnet_id=results["subnet"].id
                    )
                    
                    results["router"] = router
            
            self.logger.info(f"Создана настройка тенанта: {tenant_name}")
            
            return {"status": "success", "tenant_setup": results}
            
        except Exception as e:
            self.logger.error(f"Ошибка создания тенанта: {e}")
            return {"status": "error", "message": str(e)}


# === Вспомогательные функции ===

def load_cee_config_from_yaml(config_path: str = None) -> Dict:
    """
    Загрузка конфигурации CEE из YAML файлов
    """
    import yaml
    
    if not config_path:
        config_path = "C:\\Users\\sasha\\Documents\\Работа\\Конфиги\\CEE\\config"
    
    config = {}
    
    try:
        # Загружаем основной config.yaml
        with open(f"{config_path}\\config.yaml", 'r', encoding='utf-8') as f:
            config['main'] = yaml.safe_load(f)
        
        # Загружаем hosts.yaml
        with open(f"{config_path}\\hosts.yaml", 'r', encoding='utf-8') as f:
            config['hosts'] = yaml.safe_load(f)
        
        # Загружаем networks.yaml
        with open(f"{config_path}\\networks.yaml", 'r', encoding='utf-8') as f:
            config['networks'] = yaml.safe_load(f)
        
        # Загружаем VxSDS конфигурацию
        vxsds_path = f"{config_path}\\services\\vxsds\\config\\vxsds\\vxsds.yml"
        if os.path.exists(vxsds_path):
            with open(vxsds_path, 'r', encoding='utf-8') as f:
                config['vxsds'] = yaml.safe_load(f)
        
        return config
        
    except Exception as e:
        logging.error(f"Ошибка загрузки конфигурации: {e}")
        return {}


def create_cee_client_from_config(config_path: str = None) -> CEEOpenStackClient:
    """
    Создание CEE клиента на основе конфигурационных файлов
    """
    config = load_cee_config_from_yaml(config_path)
    
    # Извлекаем параметры подключения из конфигурации
    cee_name = config.get('main', {}).get('name', 'mokc01ltecee01')
    domain = config.get('main', {}).get('dnsConfig', {}).get('internalDomain', 'plte.evergy.com')
    
    # Формируем URL для подключения
    auth_url = f"https://{cee_name}-openstack.{domain}:5000/v3"
    
    # Создаем клиент
    client = CEEOpenStackClient(
        auth_url=auth_url,
        username="admin",  # Можно сделать параметром
        project_name="admin",
        verify=False  # CEE обычно использует self-signed сертификаты
    )
    
    return client


# === Пример использования ===

if __name__ == "__main__":
    # Создание клиента
    client = create_cee_client_from_config()
    
    # Проверка статуса кластера
    status = client.get_cee_cluster_status()
    print("Статус CEE кластера:", status)
    
    # Создание ВМ с VxSDS хранилищем
    vm_result = client.create_vm_with_vxsds_storage(
        name="test-vm-vxsds",
        image="cirros-0.5.2",  # Замените на доступный образ
        flavor="m1.small",
        volume_size=10,
        volume_type="vxsds_thin_SSD"
    )
    print("Результат создания ВМ:", vm_result)
    
    # Получение VxSDS статистики
    vxsds_stats = client.get_vxsds_statistics()
    print("VxSDS статистика:", vxsds_stats)