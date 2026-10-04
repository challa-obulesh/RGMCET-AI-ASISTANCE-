import pytest
from fastapi.testclient import TestClient
from app.web_mvp.main import app
from app.web_mvp.auth import create_access_token

@pytest.fixture
def student_token():
    return create_access_token({"sub": "USER-1", "email": "student@test.com", "role": "student", "name": "Test Student"})

@pytest.fixture
def professor_token():
    return create_access_token({"sub": "USER-2", "email": "prof@test.com", "role": "professor", "name": "Test Prof"})

@pytest.fixture
def admin_token():
    return create_access_token({"sub": "USER-3", "email": "admin@test.com", "role": "admin", "name": "Admin"})

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_admin_isolation(client, student_token, professor_token):
    res = client.get("/api/admin/overview")
    assert res.status_code == 401
    
    res = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {student_token}"})
    assert res.status_code == 403
    
    res = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {professor_token}"})
    assert res.status_code == 403

def test_admin_access(client, admin_token):
    res = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "knowledge" in data
