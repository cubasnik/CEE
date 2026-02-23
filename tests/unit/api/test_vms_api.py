
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lcm.api.endpoints import vms

class FakeLifecycle:
    async def create(self, **kwargs):
        return {
            "id": "vm-123",
            "name": kwargs["name"],
            "status": "BUILDING",
            "ip_addresses": [],
            "created_at": "2024-01-01T10:00:00"
        }
    async def get(self, vm_id):
        if vm_id == "non-existent-vm":
            return None
        return {
            "id": vm_id,
            "name": "test-vm",
            "status": "ACTIVE",
            "ip_addresses": ["192.168.1.100"],
            "created_at": "2024-01-01T10:00:00"
        }
    async def delete(self, vm_id):
        return True
    async def list(self):
        return [
            {
                "id": "vm-1",
                "name": "test-vm-1",
                "status": "ACTIVE",
                "ip_addresses": ["192.168.1.100"],
                "created_at": "2024-01-01T10:00:00"
            },
            {
                "id": "vm-2",
                "name": "test-vm-2",
                "status": "ACTIVE",
                "ip_addresses": ["192.168.1.101"],
                "created_at": "2024-01-01T10:00:00"
            }
        ]

class FakeScheduler:
    async def select_host(self, flavor: str):
        if flavor == "m1.small":
            return "host1"
        return None

def build_test_client():
    app = FastAPI()
    app.include_router(vms.router, prefix="/api/v1")
    app.dependency_overrides[vms.get_vm_lifecycle] = lambda: FakeLifecycle()
    app.dependency_overrides[vms.get_scheduler] = lambda: FakeScheduler()
    return TestClient(app)

class TestVMsAPI:
    def test_create_vm_success(self, sample_vm_request):
        client = build_test_client()
        response = client.post("/api/v1/vms/", json=sample_vm_request)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_vm_request["name"]
        assert data["status"] == "BUILDING"
        assert "id" in data

    def test_create_vm_invalid_request(self):
        client = build_test_client()
        invalid_request = {"name": "test-vm"}
        response = client.post("/api/v1/vms/", json=invalid_request)
        assert response.status_code == 422

    def test_get_vm_success(self):
        client = build_test_client()
        vm_id = "vm-123"
        response = client.get(f"/api/v1/vms/{vm_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == vm_id
        assert data["status"] == "ACTIVE"

    def test_get_vm_not_found(self):
        client = build_test_client()
        vm_id = "non-existent-vm"
        response = client.get(f"/api/v1/vms/{vm_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_vms(self):
        client = build_test_client()
        response = client.get("/api/v1/vms/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_delete_vm_success(self):
        client = build_test_client()
        vm_id = "vm-123"
        response = client.delete(f"/api/v1/vms/{vm_id}")
        assert response.status_code == 200
