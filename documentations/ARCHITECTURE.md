# Architecture

![Architecture Diagram](../docs/images/architecture.png)

Система состоит из:
- **LCM API** (этот проект) - управляющий слой
- **OpenStack** - гипервизор и сеть
- **KVM** - аппаратная виртуализация

## Структура кода
- `main.py` — корневая точка запуска
- `lcm/main.py` — FastAPI-приложение и подключение роутеров
- `lcm/api/endpoints/` — REST API endpoints
- `lcm/orchestrator/` — логика жизненного цикла и планировщик ВМ
- `lcm/drivers/` — интеграция с OpenStack
- `lcm/db/` — модели и репозитории

## Изображения архитектуры
Изображения хранятся в `docs/images/`.

Рекомендации для `architecture.png`:
- Формат: PNG
- Ширина: от 1600 px для читаемости в GitHub
- Содержимое: LCM API, OpenStack, KVM, ключевые связи между компонентами
