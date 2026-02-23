# Setup

## Требования
- Python 3.10+
- Доступ к OpenStack API (keystone)
- PostgreSQL (опционально)

## Переменные окружения OpenStack (обязательные)
LCM использует стандартные переменные окружения OpenStack:

- `OS_AUTH_URL`
- `OS_USERNAME`
- `OS_PASSWORD`
- `OS_PROJECT_NAME`
- `OS_USER_DOMAIN_NAME`

Дополнительно в большинстве инсталляций также задают:
- `OS_PROJECT_DOMAIN_NAME`

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/cee-lcm.git
cd cee-lcm

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env под свою среду

# Запуск
uvicorn lcm.main:app --reload
```

## Linux-нюанс: ошибка `ensurepip is not available`

Если при создании виртуального окружения появляется ошибка про `ensurepip`,
установите пакет `python3.13-venv` и повторите шаги:

```bash
sudo apt-get update
sudo apt-get install -y python3.13-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Проверка
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## Команды через Makefile

```bash
make venv         # создать .venv
make install      # установить runtime зависимости
make install-dev  # установить dev зависимости
make test         # запустить тесты
make run          # запустить API
```
