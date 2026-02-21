# API

## Base URL
- `http://localhost:8000`

## Документация
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Эндпоинты

### Health
- `GET /health`

### VMs
- `POST /api/v1/vms/` — создание виртуальной машины
- `GET /api/v1/vms/{vm_id}` — получение информации о ВМ

### Networks
- `GET /api/v1/networks/` — список сетей

### Images
- `GET /api/v1/images/` — список образов

### Hosts
- `GET /api/v1/hosts/` — список хостов
