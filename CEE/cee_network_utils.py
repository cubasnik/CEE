#!/usr/bin/env python3
"""
CEE Network Management Utilities
Утилиты для управления сетями OVS в CEE

Включает специфические функции для:
- Управления OVS без DPDK
- Настройки VLAN и VXLAN
- Мониторинга сетевой производительности
"""

import subprocess
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class OVSBridgeInfo:
    """Информация о OVS мосте"""
    name: str
    datapath_type: str
    ports: List[str]
    controller: Optional[str] = None
    fail_mode: Optional[str] = None


@dataclass
class OVSPortInfo:
    """Информация о OVS порте"""
    name: str
    interface_type: str
    vlan_tag: Optional[int] = None
    trunk_vlans: List[int] = None
    mac: Optional[str] = None
    mtu: Optional[int] = None


class CEEOVSManager:
    """
    Менеджер для управления Open vSwitch в CEE
    Специально адаптирован для CEE без DPDK
    """
    
    def __init__(self):
        self.logger = logging.getLogger('CEEOVSManager')
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _run_ovs_command(self, command: List[str]) -> Tuple[bool, str]:
        """
        Выполнение OVS команды
        
        Args:
            command: Список команды и аргументов
            
        Returns:
            Tuple[success, output]
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка выполнения команды {' '.join(command)}: {e.stderr}")
            return False, e.stderr
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {e}")
            return False, str(e)
    
    def get_bridge_info(self, bridge_name: str) -> Optional[OVSBridgeInfo]:
        """
        Получение информации о OVS мосте
        """
        success, output = self._run_ovs_command(['ovs-vsctl', 'show'])
        if not success:
            return None
        
        # Парсим вывод ovs-vsctl show
        bridges = self._parse_ovs_show_output(output)
        return bridges.get(bridge_name)
    
    def _parse_ovs_show_output(self, output: str) -> Dict[str, OVSBridgeInfo]:
        """Парсинг вывода ovs-vsctl show"""
        bridges = {}
        current_bridge = None
        current_ports = []
        
        for line in output.split('\n'):
            line = line.strip()
            
            if line.startswith('Bridge'):
                if current_bridge:
                    bridges[current_bridge] = OVSBridgeInfo(
                        name=current_bridge,
                        datapath_type="system",  # По умолчанию для CEE без DPDK
                        ports=current_ports.copy()
                    )
                current_bridge = line.split()[1].strip('"')
                current_ports = []
            elif line.startswith('Port'):
                port_name = line.split()[1].strip('"')
                current_ports.append(port_name)
        
        # Добавляем последний мост
        if current_bridge:
            bridges[current_bridge] = OVSBridgeInfo(
                name=current_bridge,
                datapath_type="system",
                ports=current_ports
            )
        
        return bridges
    
    def create_cee_bridge(
        self,
        bridge_name: str,
        vlan_id: Optional[int] = None,
        physical_interface: Optional[str] = None
    ) -> bool:
        """
        Создание OVS моста для CEE
        
        Args:
            bridge_name: Имя моста
            vlan_id: VLAN ID для настройки
            physical_interface: Физический интерфейс для подключения
        """
        try:
            # Создаем мост
            success, _ = self._run_ovs_command(['ovs-vsctl', 'add-br', bridge_name])
            if not success:
                return False
            
            # Устанавливаем datapath_type = system (не netdev, так как нет DPDK)
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'set', 'bridge', bridge_name, 'datapath_type=system'
            ])
            if not success:
                return False
            
            # Подключаем физический интерфейс если указан
            if physical_interface:
                success, _ = self._run_ovs_command([
                    'ovs-vsctl', 'add-port', bridge_name, physical_interface
                ])
                if not success:
                    return False
                
                # Настраиваем VLAN тег если указан
                if vlan_id:
                    success, _ = self._run_ovs_command([
                        'ovs-vsctl', 'set', 'port', physical_interface, f'tag={vlan_id}'
                    ])
                    if not success:
                        return False
            
            self.logger.info(f"Создан OVS мост: {bridge_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка создания моста: {e}")
            return False
    
    def setup_cee_provider_network(
        self,
        bridge_name: str,
        physical_interface: str,
        vlan_range: str = "100:200"
    ) -> bool:
        """
        Настройка provider network моста для CEE
        
        Args:
            bridge_name: Имя моста (например br-provider)
            physical_interface: Физический интерфейс
            vlan_range: Диапазон VLAN (например "100:200")
        """
        try:
            # Создаем мост
            if not self.create_cee_bridge(bridge_name, physical_interface=physical_interface):
                return False
            
            # Настраиваем trunk порт для VLAN range
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'set', 'port', physical_interface, 'trunk=' + vlan_range
            ])
            if not success:
                return False
            
            # Отключаем STP для производительности
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'set', 'bridge', bridge_name, 'stp_enable=false'
            ])
            
            self.logger.info(f"Настроен provider network мост: {bridge_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки provider network: {e}")
            return False
    
    def setup_cee_tenant_network(
        self,
        tunnel_interface: str,
        tunnel_ip: str,
        vni_range: str = "1:1000"
    ) -> bool:
        """
        Настройка tenant network с VXLAN для CEE
        
        Args:
            tunnel_interface: Интерфейс для туннелей
            tunnel_ip: IP адрес туннельного интерфейса
            vni_range: Диапазон VNI для VXLAN
        """
        try:
            bridge_name = "br-tun"
            
            # Создаем tunnel мост
            success, _ = self._run_ovs_command(['ovs-vsctl', 'add-br', bridge_name])
            if not success:
                return False
            
            # Настраиваем туннельный интерфейс
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'set', 'bridge', bridge_name, f'other-config:local_ip={tunnel_ip}'
            ])
            if not success:
                return False
            
            self.logger.info(f"Настроен tenant network мост: {bridge_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки tenant network: {e}")
            return False
    
    def create_vxlan_tunnel(
        self,
        bridge_name: str,
        tunnel_name: str,
        remote_ip: str,
        vni: int
    ) -> bool:
        """
        Создание VXLAN туннеля между узлами
        """
        try:
            # Добавляем VXLAN порт
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'add-port', bridge_name, tunnel_name,
                '--', 'set', 'interface', tunnel_name, 'type=vxlan',
                f'options:remote_ip={remote_ip}',
                f'options:key={vni}'
            ])
            
            if success:
                self.logger.info(f"Создан VXLAN туннель: {tunnel_name} -> {remote_ip}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка создания VXLAN туннеля: {e}")
            return False
    
    def get_port_statistics(self, bridge_name: str, port_name: str) -> Dict:
        """
        Получение статистики порта
        """
        success, output = self._run_ovs_command([
            'ovs-vsctl', 'get', 'interface', port_name, 'statistics'
        ])
        
        if not success:
            return {}
        
        try:
            # Парсим статистику (формат: {key1=value1, key2=value2, ...})
            stats_str = output.strip()
            if stats_str.startswith('{') and stats_str.endswith('}'):
                stats_str = stats_str[1:-1]  # Убираем фигурные скобки
                
                stats = {}
                for pair in stats_str.split(', '):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        try:
                            stats[key] = int(value)
                        except ValueError:
                            stats[key] = value
                
                return stats
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга статистики: {e}")
        
        return {}
    
    def monitor_ovs_performance(self) -> Dict:
        """
        Мониторинг производительности OVS
        """
        performance_data = {
            "timestamp": time.time(),
            "bridges": {},
            "cpu_usage": {},
            "memory_usage": {}
        }
        
        try:
            # Получаем список мостов
            success, output = self._run_ovs_command(['ovs-vsctl', 'list-br'])
            if success:
                bridges = output.strip().split('\n')
                
                for bridge in bridges:
                    if bridge:
                        bridge_info = self.get_bridge_info(bridge)
                        if bridge_info:
                            performance_data["bridges"][bridge] = {
                                "ports_count": len(bridge_info.ports),
                                "datapath_type": bridge_info.datapath_type
                            }
                            
                            # Получаем статистику портов
                            for port in bridge_info.ports:
                                port_stats = self.get_port_statistics(bridge, port)
                                if port_stats:
                                    performance_data["bridges"][bridge][f"port_{port}_stats"] = port_stats
            
            # Получаем статистику ovs-vswitchd процесса
            try:
                success, output = self._run_ovs_command(['ps', 'aux'])
                if success:
                    for line in output.split('\n'):
                        if 'ovs-vswitchd' in line:
                            parts = line.split()
                            if len(parts) >= 11:
                                performance_data["cpu_usage"]["ovs_vswitchd"] = float(parts[2])
                                performance_data["memory_usage"]["ovs_vswitchd"] = float(parts[3])
            except:
                pass  # Статистика процессов не критична
            
        except Exception as e:
            self.logger.error(f"Ошибка мониторинга производительности: {e}")
        
        return performance_data
    
    def setup_cee_qos_rules(
        self,
        port_name: str,
        max_rate_mbps: int,
        burst_mbps: int = None
    ) -> bool:
        """
        Настройка QoS правил для CEE портов
        """
        try:
            if burst_mbps is None:
                burst_mbps = max_rate_mbps
            
            # Настраиваем ingress policing
            success, _ = self._run_ovs_command([
                'ovs-vsctl', 'set', 'interface', port_name,
                f'ingress_policing_rate={max_rate_mbps * 1000}',  # в kbps
                f'ingress_policing_burst={burst_mbps * 1000}'     # в kbps
            ])
            
            if success:
                self.logger.info(f"QoS настроен для порта {port_name}: {max_rate_mbps} Mbps")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки QoS: {e}")
            return False


class CEENetworkTopology:
    """
    Анализатор сетевой топологии CEE
    """
    
    def __init__(self, ovs_manager: CEEOVSManager):
        self.ovs_manager = ovs_manager
        self.logger = logging.getLogger('CEENetworkTopology')
    
    def discover_cee_topology(self) -> Dict:
        """
        Обнаружение сетевой топологии CEE
        """
        topology = {
            "compute_nodes": {},
            "controller_nodes": {},
            "network_nodes": {},
            "bridges": {},
            "tunnels": {}
        }
        
        try:
            # Получаем информацию о мостах
            success, output = self.ovs_manager._run_ovs_command(['ovs-vsctl', 'list-br'])
            if success:
                bridges = output.strip().split('\n')
                
                for bridge in bridges:
                    if bridge:
                        bridge_info = self.ovs_manager.get_bridge_info(bridge)
                        if bridge_info:
                            topology["bridges"][bridge] = {
                                "datapath_type": bridge_info.datapath_type,
                                "ports": bridge_info.ports,
                                "role": self._identify_bridge_role(bridge)
                            }
            
            # Анализируем VXLAN туннели
            self._analyze_vxlan_tunnels(topology)
            
            # Определяем роли узлов
            self._identify_node_roles(topology)
            
        except Exception as e:
            self.logger.error(f"Ошибка обнаружения топологии: {e}")
        
        return topology
    
    def _identify_bridge_role(self, bridge_name: str) -> str:
        """Определение роли моста"""
        if bridge_name == "br-int":
            return "integration"
        elif bridge_name.startswith("br-provider") or bridge_name.startswith("br-ex"):
            return "provider"
        elif bridge_name == "br-tun":
            return "tunnel"
        else:
            return "unknown"
    
    def _analyze_vxlan_tunnels(self, topology: Dict):
        """Анализ VXLAN туннелей"""
        try:
            success, output = self.ovs_manager._run_ovs_command([
                'ovs-vsctl', '--format=json', 'list', 'interface'
            ])
            
            if success:
                interfaces = json.loads(output)
                
                for interface in interfaces.get('data', []):
                    if len(interface) > 2 and interface[2] == 'vxlan':
                        # Это VXLAN интерфейс
                        name = interface[1]  # Предполагаем что имя во втором элементе
                        # Дополнительная логика анализа VXLAN туннелей
                        topology["tunnels"][name] = {
                            "type": "vxlan",
                            "status": "active"  # Упрощенно
                        }
        except:
            pass  # JSON парсинг может не работать на всех версиях
    
    def _identify_node_roles(self, topology: Dict):
        """Определение ролей узлов"""
        # Упрощенная логика определения ролей на основе наличия мостов
        has_integration = "br-int" in topology["bridges"]
        has_tunnel = "br-tun" in topology["bridges"]
        has_provider = any(name.startswith("br-provider") or name.startswith("br-ex") 
                          for name in topology["bridges"])
        
        node_type = "unknown"
        if has_integration and has_tunnel:
            if has_provider:
                node_type = "network_node"
            else:
                node_type = "compute_node"
        elif has_integration:
            node_type = "controller_node"
        
        topology["node_type"] = node_type


# === Утилитарные функции ===

def setup_cee_standard_bridges(config_path: str = None) -> bool:
    """
    Настройка стандартных мостов для CEE
    """
    ovs_manager = CEEOVSManager()
    
    # Загружаем конфигурацию CEE
    from cee_openstack_client import load_cee_config_from_yaml
    config = load_cee_config_from_yaml(config_path)
    
    success = True
    
    try:
        # Интеграционный мост (всегда нужен)
        if not ovs_manager.create_cee_bridge("br-int"):
            success = False
        
        # Provider мосты (для внешних сетей)
        # Настраиваем на основе физических сетей из конфигурации
        physical_networks = ["physnet1", "physnet2"]  # Из конфигурации CEE
        
        for i, physnet in enumerate(physical_networks):
            bridge_name = f"br-{physnet}"
            physical_interface = f"eno{i+1}"  # Предполагаемые интерфейсы
            
            if not ovs_manager.setup_cee_provider_network(
                bridge_name, 
                physical_interface,
                "100:4000"  # VLAN range для CEE
            ):
                success = False
        
        # Tunnel мост (для VXLAN)
        tunnel_ip = "192.168.40.20"  # Из sdn_ul сети
        if not ovs_manager.setup_cee_tenant_network(
            "eno3",  # Tunnel interface
            tunnel_ip
        ):
            success = False
        
    except Exception as e:
        logging.error(f"Ошибка настройки мостов: {e}")
        success = False
    
    return success


def monitor_cee_network_health() -> Dict:
    """
    Мониторинг здоровья сети CEE
    """
    ovs_manager = CEEOVSManager()
    topology = CEENetworkTopology(ovs_manager)
    
    health_report = {
        "timestamp": time.time(),
        "overall_status": "healthy",
        "issues": [],
        "performance": {},
        "topology": {}
    }
    
    try:
        # Получаем топологию
        topo_data = topology.discover_cee_topology()
        health_report["topology"] = topo_data
        
        # Проверяем производительность
        perf_data = ovs_manager.monitor_ovs_performance()
        health_report["performance"] = perf_data
        
        # Анализируем проблемы
        issues = []
        
        # Проверяем наличие обязательных мостов
        required_bridges = ["br-int"]
        for bridge in required_bridges:
            if bridge not in topo_data["bridges"]:
                issues.append(f"Отсутствует обязательный мост: {bridge}")
        
        # Проверяем производительность CPU
        if "cpu_usage" in perf_data and "ovs_vswitchd" in perf_data["cpu_usage"]:
            cpu_usage = perf_data["cpu_usage"]["ovs_vswitchd"]
            if cpu_usage > 80:
                issues.append(f"Высокая загрузка CPU ovs-vswitchd: {cpu_usage}%")
        
        health_report["issues"] = issues
        if issues:
            health_report["overall_status"] = "warning" if len(issues) <= 2 else "critical"
        
    except Exception as e:
        health_report["overall_status"] = "error"
        health_report["issues"].append(f"Ошибка мониторинга: {e}")
    
    return health_report


# === Пример использования ===

if __name__ == "__main__":
    import time
    
    # Создание менеджера OVS
    ovs_manager = CEEOVSManager()
    
    # Мониторинг производительности
    print("=== Мониторинг OVS ===")
    performance = ovs_manager.monitor_ovs_performance()
    print(f"Данные производительности: {performance}")
    
    # Анализ топологии
    print("\n=== Анализ топологии ===")
    topology_analyzer = CEENetworkTopology(ovs_manager)
    topology = topology_analyzer.discover_cee_topology()
    print(f"Топология сети: {topology}")
    
    # Общий отчет о здоровье сети
    print("\n=== Отчет о здоровье сети ===")
    health = monitor_cee_network_health()
    print(f"Статус: {health['overall_status']}")
    if health['issues']:
        print(f"Проблемы: {health['issues']}")