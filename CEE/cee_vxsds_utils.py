#!/usr/bin/env python3
"""
CEE VxSDS Storage Management Utilities
Утилиты для управления VxSDS (Dell ScaleIO) в CEE

Включает функции для:
- Управления VxSDS томами
- Мониторинга производительности хранилища  
- Настройки Cinder интеграции
- Анализа метрик хранилища
"""

import json
import logging
import time
import requests
import base64
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from urllib3.exceptions import InsecureRequestWarning

# Отключаем предупреждения о SSL для VxSDS
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@dataclass
class VxSDSVolumeInfo:
    """Информация о VxSDS томе"""
    id: str
    name: str
    size_gb: int
    storage_pool: str
    protection_domain: str
    volume_type: str = "thin"
    creation_time: Optional[str] = None
    mapped_sdcs: List[str] = None
    

@dataclass
class VxSDSStoragePoolInfo:
    """Информация о пуле хранения VxSDS"""
    id: str
    name: str
    protection_domain: str
    media_type: str
    capacity_gb: int
    free_capacity_gb: int
    num_volumes: int
    spare_percentage: int


@dataclass
class VxSDSNodeInfo:
    """Информация об узле VxSDS"""
    id: str
    name: str
    ip_addresses: List[str]
    role: str  # MDM, SDS, SDC
    state: str
    version: str


class VxSDSClient:
    """
    Клиент для управления VxSDS через REST API
    Специально адаптирован для CEE конфигурации
    """
    
    def __init__(
        self,
        gateway_host: str = "192.168.2.13",  # openstack_int_vip
        gateway_port: int = 4443,
        username: str = "admin", 
        password: str = "Ericsson123@",
        verify_ssl: bool = False
    ):
        """
        Инициализация VxSDS клиента
        
        Args:
            gateway_host: IP адрес VxSDS Gateway
            gateway_port: Порт VxSDS Gateway
            username: Имя пользователя
            password: Пароль
            verify_ssl: Проверка SSL сертификатов
        """
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        
        self.base_url = f"https://{gateway_host}:{gateway_port}/api"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        self.logger = logging.getLogger('VxSDSClient')
        self._setup_logging()
        
        # Аутентификация
        self.token = None
        self._authenticate()
    
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _authenticate(self) -> bool:
        """
        Аутентификация в VxSDS Gateway
        """
        try:
            auth_url = f"{self.base_url}/login"
            auth_string = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            }
            
            response = self.session.get(auth_url, headers=headers)
            
            if response.status_code == 200:
                self.token = response.text.strip('"')
                self.session.headers.update({
                    "Authorization": f"Basic {auth_string}"
                })
                self.logger.info("Успешная аутентификация в VxSDS")
                return True
            else:
                self.logger.error(f"Ошибка аутентификации: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка подключения к VxSDS: {e}")
            return False
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict = None
    ) -> Optional[Dict]:
        """
        Выполнение запроса к VxSDS API
        
        Args:
            method: HTTP метод (GET, POST, DELETE, etc.)
            endpoint: Конечная точка API
            data: Данные для отправки
            
        Returns:
            Ответ API или None в случае ошибки
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            headers = {"Content-Type": "application/json"}
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"status": "success", "data": response.text}
            else:
                self.logger.error(
                    f"API ошибка {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка запроса: {e}")
            return None
    
    # === Управление системой ===
    
    def get_system_info(self) -> Optional[Dict]:
        """
        Получение информации о системе VxSDS
        """
        return self._make_request("GET", "/instances/System")
    
    def get_system_statistics(self) -> Optional[Dict]:
        """
        Получение статистики системы
        """
        system_info = self.get_system_info()
        if not system_info:
            return None
        
        try:
            systems = system_info.get("data", [])
            if systems:
                system_id = systems[0]["id"]
                return self._make_request("GET", f"/instances/System::{system_id}/relationships/Statistics")
        except (KeyError, IndexError):
            return None
    
    # === Управление Protection Domains ===
    
    def get_protection_domains(self) -> List[Dict]:
        """
        Получение списка Protection Domains
        """
        response = self._make_request("GET", "/instances/ProtectionDomain")
        if response:
            return response.get("data", [])
        return []
    
    def create_protection_domain(self, name: str) -> Optional[Dict]:
        """
        Создание Protection Domain
        """
        data = {"name": name}
        return self._make_request("POST", "/instances/ProtectionDomain", data)
    
    # === Управление Storage Pools ===
    
    def get_storage_pools(self, protection_domain_id: str = None) -> List[VxSDSStoragePoolInfo]:
        """
        Получение списка пулов хранения
        """
        pools = []
        
        if protection_domain_id:
            endpoint = f"/instances/ProtectionDomain::{protection_domain_id}/relationships/StoragePool"
        else:
            endpoint = "/instances/StoragePool"
        
        response = self._make_request("GET", endpoint)
        
        if response:
            raw_pools = response.get("data", [])
            
            for pool_data in raw_pools:
                try:
                    # Получаем детальную информацию о пуле
                    pool_stats = self._make_request(
                        "GET", 
                        f"/instances/StoragePool::{pool_data['id']}/relationships/Statistics"
                    )
                    
                    capacity_gb = 0
                    free_capacity_gb = 0
                    
                    if pool_stats and pool_stats.get("data"):
                        stats = pool_stats["data"][0]
                        capacity_gb = stats.get("capacityInUseInKb", 0) // 1024 // 1024
                        free_capacity_gb = stats.get("capacityAvailableForVolumeAllocationInKb", 0) // 1024 // 1024
                    
                    pool_info = VxSDSStoragePoolInfo(
                        id=pool_data["id"],
                        name=pool_data["name"],
                        protection_domain=pool_data.get("protectionDomainId", ""),
                        media_type=pool_data.get("mediaType", "SSD"),
                        capacity_gb=capacity_gb,
                        free_capacity_gb=free_capacity_gb,
                        num_volumes=pool_data.get("numOfVolumes", 0),
                        spare_percentage=pool_data.get("sparePercentage", 10)
                    )
                    
                    pools.append(pool_info)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки пула {pool_data.get('id', 'unknown')}: {e}")
        
        return pools
    
    def create_storage_pool(
        self,
        name: str,
        protection_domain_id: str,
        media_type: str = "SSD",
        spare_percentage: int = 10
    ) -> Optional[Dict]:
        """
        Создание пула хранения
        """
        data = {
            "name": name,
            "protectionDomainId": protection_domain_id,
            "mediaType": media_type,
            "sparePercentage": spare_percentage
        }
        return self._make_request("POST", "/instances/StoragePool", data)
    
    # === Управление томами ===
    
    def get_volumes(self, storage_pool_id: str = None) -> List[VxSDSVolumeInfo]:
        """
        Получение списка томов
        """
        volumes = []
        
        if storage_pool_id:
            endpoint = f"/instances/StoragePool::{storage_pool_id}/relationships/Volume"
        else:
            endpoint = "/instances/Volume"
        
        response = self._make_request("GET", endpoint)
        
        if response:
            raw_volumes = response.get("data", [])
            
            for volume_data in raw_volumes:
                try:
                    mapped_sdcs = []
                    
                    # Получаем информацию о маппинге
                    mapping_response = self._make_request(
                        "GET",
                        f"/instances/Volume::{volume_data['id']}/relationships/SdcMappedToVolume"
                    )
                    
                    if mapping_response:
                        for mapping in mapping_response.get("data", []):
                            mapped_sdcs.append(mapping.get("sdcId", ""))
                    
                    volume_info = VxSDSVolumeInfo(
                        id=volume_data["id"],
                        name=volume_data.get("name", ""),
                        size_gb=volume_data.get("sizeInKb", 0) // 1024 // 1024,
                        storage_pool=volume_data.get("storagePoolId", ""),
                        protection_domain="",  # Заполним позже
                        volume_type=volume_data.get("volumeType", "ThinProvisioned"),
                        creation_time=volume_data.get("creationTime"),
                        mapped_sdcs=mapped_sdcs
                    )
                    
                    volumes.append(volume_info)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки тома {volume_data.get('id', 'unknown')}: {e}")
        
        return volumes
    
    def create_volume(
        self,
        name: str,
        size_gb: int,
        storage_pool_id: str,
        volume_type: str = "ThinProvisioned"
    ) -> Optional[Dict]:
        """
        Создание тома
        """
        data = {
            "name": name,
            "sizeInGb": size_gb,
            "storagePoolId": storage_pool_id,
            "volumeType": volume_type
        }
        
        result = self._make_request("POST", "/instances/Volume", data)
        
        if result:
            self.logger.info(f"Создан том: {name} ({size_gb} GB)")
        
        return result
    
    def delete_volume(self, volume_id: str, remove_mode: str = "ONLY_ME") -> bool:
        """
        Удаление тома
        
        Args:
            volume_id: ID тома
            remove_mode: Режим удаления (ONLY_ME, INCLUDING_DESCENDANTS)
        """
        data = {"removeMode": remove_mode}
        
        result = self._make_request(
            "POST", 
            f"/instances/Volume::{volume_id}/action/removeVolume",
            data
        )
        
        return result is not None
    
    def map_volume_to_sdc(self, volume_id: str, sdc_id: str, allow_multi_map: bool = False) -> bool:
        """
        Подключение тома к SDC (Storage Data Client)
        """
        data = {
            "sdcId": sdc_id,
            "allowMultipleMapping": "true" if allow_multi_map else "false"
        }
        
        result = self._make_request(
            "POST",
            f"/instances/Volume::{volume_id}/action/addMappedSdc",
            data
        )
        
        return result is not None
    
    def unmap_volume_from_sdc(self, volume_id: str, sdc_id: str) -> bool:
        """
        Отключение тома от SDC
        """
        data = {"sdcId": sdc_id}
        
        result = self._make_request(
            "POST",
            f"/instances/Volume::{volume_id}/action/removeMappedSdc",
            data
        )
        
        return result is not None
    
    # === Управление узлами ===
    
    def get_sdc_nodes(self) -> List[VxSDSNodeInfo]:
        """
        Получение списка SDC узлов
        """
        nodes = []
        
        response = self._make_request("GET", "/instances/Sdc")
        
        if response:
            raw_nodes = response.get("data", [])
            
            for node_data in raw_nodes:
                try:
                    node_info = VxSDSNodeInfo(
                        id=node_data["id"],
                        name=node_data.get("name", ""),
                        ip_addresses=[node_data.get("sdcIp", "")],
                        role="SDC",
                        state=node_data.get("mdmConnectionState", "unknown"),
                        version=node_data.get("versionInfo", "")
                    )
                    nodes.append(node_info)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки SDC узла: {e}")
        
        return nodes
    
    def get_sds_nodes(self) -> List[VxSDSNodeInfo]:
        """
        Получение списка SDS узлов
        """
        nodes = []
        
        response = self._make_request("GET", "/instances/Sds")
        
        if response:
            raw_nodes = response.get("data", [])
            
            for node_data in raw_nodes:
                try:
                    # Собираем IP адреса
                    ip_addresses = []
                    for ip_info in node_data.get("ipList", []):
                        ip_addresses.append(ip_info.get("ip", ""))
                    
                    node_info = VxSDSNodeInfo(
                        id=node_data["id"],
                        name=node_data.get("name", ""),
                        ip_addresses=ip_addresses,
                        role="SDS",
                        state=node_data.get("sdsState", "unknown"),
                        version=""  # SDS версия обычно не доступна напрямую
                    )
                    nodes.append(node_info)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки SDS узла: {e}")
        
        return nodes


class CEEVxSDSManager:
    """
    Высокоуровневый менеджер для VxSDS в CEE
    Предоставляет упрощенный интерфейс для типовых операций
    """
    
    def __init__(self, vxsds_client: VxSDSClient):
        self.vxsds = vxsds_client
        self.logger = logging.getLogger('CEEVxSDSManager')
        
        # Кэш для часто используемых данных
        self._protection_domains_cache = None
        self._storage_pools_cache = None
        self._cache_time = 0
        self._cache_ttl = 300  # 5 минут
    
    def _update_cache(self):
        """Обновление кэша данных"""
        current_time = time.time()
        if current_time - self._cache_time > self._cache_ttl:
            self._protection_domains_cache = self.vxsds.get_protection_domains()
            self._storage_pools_cache = self.vxsds.get_storage_pools()
            self._cache_time = current_time
    
    def get_default_storage_pool(self) -> Optional[VxSDSStoragePoolInfo]:
        """
        Получение пула хранения по умолчанию (pool1 из CEE конфигурации)
        """
        self._update_cache()
        
        for pool in self._storage_pools_cache or []:
            if pool.name == "pool1":  # Из конфигурации vxsds.yml
                return pool
        
        # Если pool1 не найден, возвращаем первый доступный
        if self._storage_pools_cache:
            return self._storage_pools_cache[0]
        
        return None
    
    def create_cee_volume(
        self,
        name: str,
        size_gb: int,
        volume_type: str = "thin",
        multiattach: bool = False
    ) -> Optional[VxSDSVolumeInfo]:
        """
        Создание тома с настройками CEE
        
        Args:
            name: Имя тома
            size_gb: Размер в ГБ
            volume_type: Тип тома (thin/thick)
            multiattach: Разрешить множественное подключение
        """
        default_pool = self.get_default_storage_pool()
        if not default_pool:
            self.logger.error("Не найден пул хранения по умолчанию")
            return None
        
        # Преобразуем тип тома в формат VxSDS
        vxsds_volume_type = "ThinProvisioned" if volume_type == "thin" else "ThickProvisioned"
        
        result = self.vxsds.create_volume(
            name=name,
            size_gb=size_gb,
            storage_pool_id=default_pool.id,
            volume_type=vxsds_volume_type
        )
        
        if result:
            # Возвращаем информацию о созданном томе
            volume_id = result.get("id")
            if volume_id:
                volumes = self.vxsds.get_volumes()
                for volume in volumes:
                    if volume.id == volume_id:
                        return volume
        
        return None
    
    def attach_volume_to_compute_node(
        self,
        volume_id: str,
        compute_node_hostname: str
    ) -> bool:
        """
        Подключение тома к compute узлу
        
        Args:
            volume_id: ID тома
            compute_node_hostname: Hostname compute узла
        """
        # Получаем список SDC узлов
        sdc_nodes = self.vxsds.get_sdc_nodes()
        
        # Ищем узел по hostname
        target_sdc = None
        for sdc in sdc_nodes:
            if compute_node_hostname in sdc.name:
                target_sdc = sdc
                break
        
        if not target_sdc:
            self.logger.error(f"Не найден SDC узел для {compute_node_hostname}")
            return False
        
        # Подключаем том
        return self.vxsds.map_volume_to_sdc(volume_id, target_sdc.id)
    
    def get_cee_storage_summary(self) -> Dict:
        """
        Получение сводки по хранилищу CEE
        """
        self._update_cache()
        
        summary = {
            "timestamp": time.time(),
            "protection_domains": len(self._protection_domains_cache or []),
            "storage_pools": {},
            "volumes": {},
            "nodes": {},
            "capacity": {
                "total_gb": 0,
                "free_gb": 0,
                "used_gb": 0
            }
        }
        
        # Анализируем пулы
        for pool in self._storage_pools_cache or []:
            summary["storage_pools"][pool.name] = {
                "capacity_gb": pool.capacity_gb,
                "free_capacity_gb": pool.free_capacity_gb,
                "num_volumes": pool.num_volumes,
                "media_type": pool.media_type
            }
            
            summary["capacity"]["total_gb"] += pool.capacity_gb
            summary["capacity"]["free_gb"] += pool.free_capacity_gb
        
        summary["capacity"]["used_gb"] = (
            summary["capacity"]["total_gb"] - summary["capacity"]["free_gb"]
        )
        
        # Анализируем тома
        volumes = self.vxsds.get_volumes()
        volume_stats = {
            "total_count": len(volumes),
            "total_size_gb": sum(v.size_gb for v in volumes),
            "by_type": {},
            "mapped_count": 0
        }
        
        for volume in volumes:
            if volume.volume_type not in volume_stats["by_type"]:
                volume_stats["by_type"][volume.volume_type] = {"count": 0, "size_gb": 0}
            
            volume_stats["by_type"][volume.volume_type]["count"] += 1
            volume_stats["by_type"][volume.volume_type]["size_gb"] += volume.size_gb
            
            if volume.mapped_sdcs:
                volume_stats["mapped_count"] += 1
        
        summary["volumes"] = volume_stats
        
        # Анализируем узлы
        sdc_nodes = self.vxsds.get_sdc_nodes()
        sds_nodes = self.vxsds.get_sds_nodes()
        
        summary["nodes"] = {
            "sdc_count": len(sdc_nodes),
            "sds_count": len(sds_nodes),
            "sdc_online": len([n for n in sdc_nodes if n.state == "Connected"]),
            "sds_online": len([n for n in sds_nodes if n.state == "Normal"])
        }
        
        return summary
    
    def monitor_vxsds_health(self) -> Dict:
        """
        Мониторинг здоровья VxSDS
        """
        health_report = {
            "timestamp": time.time(),
            "overall_status": "healthy",
            "issues": [],
            "warnings": [],
            "metrics": {}
        }
        
        try:
            # Получаем сводку
            summary = self.get_cee_storage_summary()
            health_report["metrics"] = summary
            
            issues = []
            warnings = []
            
            # Проверяем состояние узлов
            if summary["nodes"]["sdc_count"] == 0:
                issues.append("Нет доступных SDC узлов")
            elif summary["nodes"]["sdc_online"] < summary["nodes"]["sdc_count"]:
                warnings.append(
                    f"Не все SDC узлы онлайн: {summary['nodes']['sdc_online']}/{summary['nodes']['sdc_count']}"
                )
            
            if summary["nodes"]["sds_count"] == 0:
                issues.append("Нет доступных SDS узлов")
            elif summary["nodes"]["sds_online"] < summary["nodes"]["sds_count"]:
                warnings.append(
                    f"Не все SDS узлы онлайн: {summary['nodes']['sds_online']}/{summary['nodes']['sds_count']}"
                )
            
            # Проверяем свободное место
            if summary["capacity"]["total_gb"] > 0:
                free_percentage = (
                    summary["capacity"]["free_gb"] / summary["capacity"]["total_gb"] * 100
                )
                
                if free_percentage < 10:
                    issues.append(f"Критически мало свободного места: {free_percentage:.1f}%")
                elif free_percentage < 20:
                    warnings.append(f"Мало свободного места: {free_percentage:.1f}%")
            
            health_report["issues"] = issues
            health_report["warnings"] = warnings
            
            # Определяем общий статус
            if issues:
                health_report["overall_status"] = "critical"
            elif warnings:
                health_report["overall_status"] = "warning"
            
        except Exception as e:
            health_report["overall_status"] = "error"
            health_report["issues"] = [f"Ошибка мониторинга: {e}"]
        
        return health_report


# === Утилитарные функции ===

def setup_vxsds_cinder_backend() -> Dict:
    """
    Настройка VxSDS backend для Cinder (информационно)
    Возвращает конфигурацию для cinder.conf
    """
    return {
        "volume_driver": "cinder.volume.drivers.dell_emc.scaleio.ScaleIODriver",
        "volume_backend_name": "vxsds_backend",
        "san_ip": "192.168.2.13",  # VxSDS Gateway IP
        "san_login": "admin",
        "san_password": "Ericsson123@",
        "scaleio_protection_domain_name": "protection_domain1",
        "scaleio_storage_pool_name": "pool1",
        "scaleio_storage_pools": "protection_domain1:pool1",
        "scaleio_rest_server_port": "4443",
        "scaleio_verify_server_certificate": "false",
        "scaleio_server_certificate_path": "/opt/emc/scaleio/openssl/certs"
    }


def create_vxsds_performance_report(vxsds_manager: CEEVxSDSManager) -> Dict:
    """
    Создание отчета о производительности VxSDS
    """
    report = {
        "timestamp": time.time(),
        "summary": {},
        "performance_metrics": {},
        "recommendations": []
    }
    
    try:
        # Получаем базовую статистику
        summary = vxsds_manager.get_cee_storage_summary()
        report["summary"] = summary
        
        # Получаем системную статистику
        system_stats = vxsds_manager.vxsds.get_system_statistics()
        if system_stats and system_stats.get("data"):
            stats = system_stats["data"][0]
            report["performance_metrics"] = {
                "total_read_bw_mbps": stats.get("totalReadBwc", {}).get("totalWeightInKb", 0) // 1024,
                "total_write_bw_mbps": stats.get("totalWriteBwc", {}).get("totalWeightInKb", 0) // 1024,
                "total_iops": stats.get("totalReadBwc", {}).get("numOccured", 0) + 
                             stats.get("totalWriteBwc", {}).get("numOccured", 0),
                "primary_read_bw_mbps": stats.get("primaryReadBwc", {}).get("totalWeightInKb", 0) // 1024,
                "primary_write_bw_mbps": stats.get("primaryWriteBwc", {}).get("totalWeightInKb", 0) // 1024
            }
        
        # Генерируем рекомендации
        recommendations = []
        
        if summary["capacity"]["total_gb"] > 0:
            free_percentage = summary["capacity"]["free_gb"] / summary["capacity"]["total_gb"] * 100
            if free_percentage < 20:
                recommendations.append("Рассмотрите возможность добавления дисков")
        
        if summary["nodes"]["sds_count"] < 3:
            recommendations.append("Рекомендуется минимум 3 SDS узла для отказоустойчивости")
        
        report["recommendations"] = recommendations
        
    except Exception as e:
        report["error"] = str(e)
    
    return report


# === Пример использования ===

if __name__ == "__main__":
    # Создание клиента VxSDS
    vxsds_client = VxSDSClient(
        gateway_host="192.168.2.13",  # Из CEE конфигурации
        username="admin",
        password="Ericsson123@"
    )
    
    # Создание менеджера
    vxsds_manager = CEEVxSDSManager(vxsds_client)
    
    # Получение сводки по хранилищу
    print("=== Сводка по хранилищу VxSDS ===")
    summary = vxsds_manager.get_cee_storage_summary()
    print(f"Всего дисков: {summary['capacity']['total_gb']} ГБ")
    print(f"Свободно: {summary['capacity']['free_gb']} ГБ")
    print(f"Использовано: {summary['capacity']['used_gb']} ГБ")
    print(f"Томов: {summary['volumes']['total_count']}")
    
    # Мониторинг здоровья
    print("\n=== Мониторинг здоровья VxSDS ===")
    health = vxsds_manager.monitor_vxsds_health()
    print(f"Статус: {health['overall_status']}")
    if health['issues']:
        print(f"Проблемы: {health['issues']}")
    if health['warnings']:
        print(f"Предупреждения: {health['warnings']}")
    
    # Создание тестового тома
    print("\n=== Создание тестового тома ===")
    volume = vxsds_manager.create_cee_volume(
        name="test-volume-cee",
        size_gb=10,
        volume_type="thin"
    )
    if volume:
        print(f"Создан том: {volume.name} ({volume.size_gb} ГБ)")
    
    # Отчет о производительности
    print("\n=== Отчет о производительности ===")
    perf_report = create_vxsds_performance_report(vxsds_manager)
    if "performance_metrics" in perf_report:
        metrics = perf_report["performance_metrics"]
        print(f"Общие IOPS: {metrics.get('total_iops', 0)}")
        print(f"Общая пропускная способность чтения: {metrics.get('total_read_bw_mbps', 0)} МБ/с")
        print(f"Общая пропускная способность записи: {metrics.get('total_write_bw_mbps', 0)} МБ/с")