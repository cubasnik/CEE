# CEE OpenStack Management Tools

Набор Python инструментов для управления Ericsson Cloud Execution Environment (CEE) на базе OpenStack с интеграцией VxSDS (Dell ScaleIO) и Open vSwitch без DPDK.

## Возможности

### 🚀 Основные компоненты

- **CEE OpenStack Client** - Клиент для работы с OpenStack API с учетом CEE специфики
- **VxSDS Management** - Утилиты для управления VxSDS хранилищем
- **OVS Network Utils** - Инструменты для управления Open vSwitch без DPDK
- **Integration Orchestrator** - Комплексный оркестратор для интеграции всех компонентов

### 🛠 Функциональность

#### OpenStack Integration
- Создание ВМ с VxSDS хранилищем
- Управление сетями OVS (VLAN, VXLAN)
- Настройка QoS для сетевых портов
- Автоматизация создания тенантов
- Мониторинг кластера OpenStack

#### VxSDS Storage Management
- Управление томами VxSDS
- Мониторинг производительности хранилища
- Создание Protection Domains и Storage Pools
- Подключение/отключение томов к compute узлам
- Анализ метрик хранилища

#### Network Management
- Настройка OVS мостов без DPDK
- Создание VXLAN туннелей
- Мониторинг сетевой топологии
- QoS конфигурация
- Анализ производительности сети

## 📋 Требования

### Системные требования
- Python 3.7+
- Доступ к CEE OpenStack API
- Доступ к VxSDS Gateway API
- Права администратора для OVS команд

### Python зависимости
```bash
pip install -r requirements.txt
```

Основные зависимости:
- `openstacksdk` - для работы с OpenStack API
- `requests` - для HTTP запросов к VxSDS
- `PyYAML` - для работы с конфигурационными файлами
- `psutil` - для мониторинга системы

## 🚀 Быстрый старт

### 1. Настройка конфигурации

Убедитесь, что ваши CEE конфигурационные файлы доступны:
```
config/
├── config.yaml
├── hosts.yaml  
├── networks.yaml
└── services/
    └── vxsds/
        └── config/
            └── vxsds/
                └── vxsds.yml
```

### 2. Базовое использование

```python
from cee_openstack_client import create_cee_client_from_config

# Создание клиента на основе конфигурации
client = create_cee_client_from_config("path/to/config")

# Проверка статуса кластера
status = client.get_cee_cluster_status()
print(f"Статус кластера: {status}")

# Создание ВМ с VxSDS хранилищем
vm_result = client.create_vm_with_vxsds_storage(
    name="test-vm",
    image="ubuntu-20.04",
    flavor="m1.medium",
    volume_size=20,
    volume_type="vxsds_thin_SSD"
)
```

### 3. Управление VxSDS

```python
from cee_vxsds_utils import VxSDSClient, CEEVxSDSManager

# Создание VxSDS клиента
vxsds_client = VxSDSClient(
    gateway_host="192.168.2.13",
    username="admin",
    password="your_password"
)

# Создание менеджера
vxsds_manager = CEEVxSDSManager(vxsds_client)

# Получение статистики хранилища
summary = vxsds_manager.get_cee_storage_summary()
print(f"Общая емкость: {summary['capacity']['total_gb']} ГБ")

# Создание тома
volume = vxsds_manager.create_cee_volume(
    name="test-volume",
    size_gb=10,
    volume_type="thin"
)
```

### 4. Управление сетями OVS

```python
from cee_network_utils import CEEOVSManager

# Создание OVS менеджера
ovs_manager = CEEOVSManager()

# Мониторинг производительности
performance = ovs_manager.monitor_ovs_performance()
print(f"OVS статистика: {performance}")

# Создание provider network моста
success = ovs_manager.setup_cee_provider_network(
    bridge_name="br-provider",
    physical_interface="eno1",
    vlan_range="100:200"
)
```

### 5. Комплексная интеграция

```python
from cee_integration_example import CEEOrchestrator

# Создание оркестратора
orchestrator = CEEOrchestrator("path/to/config")

# Создание полной среды тенанта
tenant_result = orchestrator.create_complete_tenant_environment(
    tenant_name="my-tenant",
    tenant_description="Production tenant",
    user_name="tenant-admin", 
    user_password="secure-password",
    network_cidr="192.168.100.0/24",
    storage_quota_gb=100
)

# Проверка здоровья системы
health_check = orchestrator.perform_health_check()
print(f"Проверок пройдено: {health_check['passed']}/{health_check['passed'] + health_check['failed']}")
```

## 📚 Подробная документация

### CEE OpenStack Client (`cee_openstack_client.py`)

Основной клиент для работы с OpenStack в CEE.

**Основные методы:**
- `create_vm_with_vxsds_storage()` - Создание ВМ с VxSDS диском
- `create_ovs_network()` - Создание OVS сети  
- `configure_ovs_qos()` - Настройка QoS
- `create_cee_tenant_setup()` - Автоматизация создания тенанта
- `get_cee_cluster_status()` - Мониторинг кластера

**Конфигурация сетей CEE:**
```python
# Автоматически загружается из networks.yaml
cee_ctrl_sp: "192.168.2.11/24"     # Управляющая сеть CEE
vxsds_fe_san_pda: "192.168.17.0/24" # VxSDS Frontend A
vxsds_be_san_pda: "192.168.15.0/24" # VxSDS Backend A
# ... другие сети из конфигурации
```

### VxSDS Management (`cee_vxsds_utils.py`)

Инструменты для управления VxSDS хранилищем.

**Основные классы:**
- `VxSDSClient` - Низкоуровневый API клиент
- `CEEVxSDSManager` - Высокоуровневый менеджер
- `VxSDSVolumeInfo`, `VxSDSStoragePoolInfo` - Структуры данных

**Пример создания и подключения тома:**
```python
# Создание тома
volume = vxsds_manager.create_cee_volume("app-data", 50, "thin")

# Подключение к compute узлу
success = vxsds_manager.attach_volume_to_compute_node(
    volume.id, 
    "mokc1ltecom16"
)
```

### Network Management (`cee_network_utils.py`)

Утилиты для управления OVS без DPDK.

**Основные возможности:**
- Создание и настройка OVS мостов
- Мониторинг сетевой топологии
- VXLAN туннели между узлами
- QoS конфигурация портов

**Пример настройки стандартных мостов:**
```python
from cee_network_utils import setup_cee_standard_bridges

# Автоматическая настройка всех мостов CEE
success = setup_cee_standard_bridges("path/to/config")
```

### Integration Orchestrator (`cee_integration_example.py`)

Комплексный оркестратор для управления всей инфраструктурой.

**Возможности:**
- Создание полных сред тенантов
- Развертывание стеков приложений
- Комплексный мониторинг
- Проверки здоровья системы

## 🔧 Конфигурация

### OpenStack подключение

Клиент автоматически извлекает параметры подключения из CEE конфигурации:

```python
# Автоматически из config.yaml:
cee_name = config['name']  # "mokc01ltecee01"
domain = config['dnsConfig']['internalDomain']  # "plte.evergy.com"
auth_url = f"https://{cee_name}-openstack.{domain}:5000/v3"
```

### VxSDS подключение

```python
# Параметры из vxsds.yml:
gateway_host = "192.168.2.13"  # openstack_int_vip
gateway_port = 4443            # gatewayPort
username = "admin"             # gatewayUser
password = "Ericsson123@"      # gatewayAdminPassword
```

### OVS конфигурация

```bash
# Мосты создаются с типом datapath = system (без DPDK)
# Интеграционный мост
br-int

# Provider мосты
br-physnet1, br-physnet2

# Tunnel мост для VXLAN
br-tun
```

## 🔍 Мониторинг и диагностика

### Проверка здоровья системы

```python
orchestrator = CEEOrchestrator()

# Комплексная проверка
health = orchestrator.perform_health_check()

# Индивидуальные проверки
openstack_ok = orchestrator._check_openstack_api()
vxsds_ok = orchestrator._check_vxsds_connectivity()  
ovs_ok = orchestrator._check_ovs_bridges()
```

### Мониторинг производительности

```python
# OpenStack метрики
cluster_status = client.get_cee_cluster_status()

# VxSDS метрики
storage_summary = vxsds_manager.get_cee_storage_summary()
vxsds_health = vxsds_manager.monitor_vxsds_health()

# OVS метрики
network_perf = ovs_manager.monitor_ovs_performance()
topology = network_topology.discover_cee_topology()
```

## ⚠ Важные замечания

### Безопасность
- Используйте переменные окружения для паролей в продакшене
- VxSDS Gateway использует self-signed сертификаты (verify=False)
- Ограничьте сетевой доступ к management интерфейсам

### Производительность  
- OVS без DPDK: datapath_type=system
- VxSDS: рекомендуется минимум 3 SDS узла
- Мониторинг: кэширование данных на 5 минут

### Ограничения
- Поддержка только IPv4 сетей
- Один Protection Domain (protection_domain1)
- Фиксированные VLAN диапазоны из конфигурации

## 🐛 Устранение неполадок

### Частые проблемы

1. **Ошибка подключения к OpenStack API**
```bash
# Проверка доступности
curl -k https://mokc01ltecee01-openstack.plte.evergy.com:5000/v3

# Проверка сертификатов  
openssl s_client -connect mokc01ltecee01-openstack.plte.evergy.com:5000
```

2. **VxSDS Gateway недоступен**
```bash
# Проверка доступности Gateway
curl -k https://192.168.2.13:4443/api/version

# Проверка сетевой связанности
ping 192.168.2.13
```

3. **OVS команды не работают**
```bash
# Проверка статуса OVS
systemctl status openvswitch-switch

# Проверка мостов
ovs-vsctl show

# Права доступа
sudo usermod -a -G openvswitch $USER
```

### Логирование

Все компоненты используют стандартное Python логирование:

```python
import logging

# Включение подробного логирования
logging.basicConfig(level=logging.DEBUG)

# Логирование только ошибок
logging.basicConfig(level=logging.ERROR)
```

## 📄 Лицензия

Инструменты предназначены для использования с Ericsson Cloud Execution Environment.

## 👥 Поддержка

При возникновении проблем:

1. Проверьте логи компонентов
2. Убедитесь в корректности сетевой конфигурации
3. Проверьте доступность всех API endpoint'ов  
4. Консультируйтесь с документацией Ericsson CEE

---

**Примечание:** Данные инструменты созданы специально для конфигурации CEE с VxSDS и OVS без DPDK. Адаптация для других конфигураций может потребовать модификации кода.