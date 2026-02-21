# CEE LCM

Проект поддерживает Python 3.13 (рекомендуется использовать именно эту версию для корректной работы виртуального окружения и зависимостей).

Основная документация проекта:

- [Обзор и возможности](documentations/README.md)
- [Установка и запуск (Python 3.13+)](documentations/SETUP.md)
- [Архитектура и структура кода](documentations/ARCHITECTURE.md)
- [API и эндпоинты](documentations/API.md)
- [Roadmap](documentations/ROADMAP.md)

## Current Status
CEE is a Cloud Execution Environment - a lightweight hypervisor for virtual machine management.

### Main Components:
- LCM (Lifecycle Management) - core orchestrator
- REST API for VM management
- Drivers for virtualization backends (OpenStack, etc.)
