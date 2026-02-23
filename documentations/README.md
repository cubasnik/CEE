# CEE LCM - Cloud Execution Environment Lifecycle Manager

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

**LCM** - это оркестратор для облачной среды на базе OpenStack и KVM.
Он предоставляет единый API для управления виртуальными машинами,
автоматизирует выбор хостов и собирает метрики.

## ✨ Возможности

- ✅ Создание, удаление, остановка виртуальных машин
- ✅ Планирование размещения ВМ на физических хостах
- ✅ Интеграция с OpenStack через официальный SDK
- ✅ Мониторинг состояния хостов и ВМ
- ✅ REST API с документацией Swagger

## 🔐 OpenStack Env

LCM использует стандартные переменные окружения OpenStack:

- `OS_AUTH_URL`
- `OS_USERNAME`
- `OS_PASSWORD`
- `OS_PROJECT_NAME`
- `OS_USER_DOMAIN_NAME`

## 📚 Документация

- Быстрый запуск и окружение: `documentations/SETUP.md`
- Архитектура и структура кода: `documentations/ARCHITECTURE.md`
- API и эндпоинты: `documentations/API.md`

## 🗺️ Roadmap

- План развития: `documentations/ROADMAP.md`
