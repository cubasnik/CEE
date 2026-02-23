import pytest
from fastapi.testclient import TestClient
import sys
import os
cee_lcm_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cee-lcm'))
sys.path.insert(0, cee_lcm_path)
from main import app
import json
import time

client = TestClient(app)

@pytest.fixture(scope="module")
def sample_data():
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/sample_data.json'))) as f:
        return json.load(f)

@pytest.mark.parametrize("vm_data", [
    {"name": "test-vm1", "image": "img1", "flavor": "flavor1", "network": "net1"},
    {"name": "test-vm2", "image": "img2", "flavor": "flavor2", "network": "net2"}
])
def test_create_vm_full_flow(vm_data):
    response = client.post("/vms", json=vm_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert "id" in data

    # Проверка появления VM
    response2 = client.get("/vms")
    vms = response2.json()
    assert any(vm["name"] == vm_data["name"] for vm in vms)


def test_create_vm_error():
    # Ошибка: отсутствует обязательное поле
    payload = {"name": "bad-vm"}
    response = client.post("/vms", json=payload)
    assert response.status_code == 422


def test_create_vm_performance():
    payload = {"name": "perf-vm", "image": "img1", "flavor": "flavor1", "network": "net1"}
    start = time.time()
    response = client.post("/vms", json=payload)
    duration = time.time() - start
    assert response.status_code == 200
    assert duration < 2  # Проверка, что создание VM занимает менее 2 секунд
