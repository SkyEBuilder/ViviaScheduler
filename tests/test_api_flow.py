import pytest
from fastapi.testclient import TestClient
import datetime as DT
import uuid
import os

from vivia_v4.api.main import app
from vivia_v4.api.config import settings
from vivia_v4.templates import ExactDateTask

client = TestClient(app)

# Clean up test files
@pytest.fixture(scope="module", autouse=True)
def cleanup():
    # Setup: Ensure clean state if needed (or just let files persist for debug)
    # We will use a unique email to avoid collision
    yield
    # Teardown: Remove test user files if strictly needed, 
    # but since we use random emails/IDs, collisions are rare.

def test_public_registration_stub():
    response = client.post("/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert "unavailable" in response.json()["message"]

def test_admin_registration_flow():
    # 1. Register via Admin
    email = f"admin_user_{uuid.uuid4()}@example.com"
    response = client.post("/auth/admin/register", json={
        "email": email,
        "admin_secret": settings.admin_secret
    })
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == email
    assert user_data["is_active"] is True
    api_key = user_data["api_key"]
    
    # 2. Add Task (ExactDateTask)
    headers = {"X-API-Key": api_key}
    
    anchor = DT.datetime(2024, 1, 1, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(hours=2)
    task = ExactDateTask(
        name="api_test_task",
        mandatory=True,
        priority=1,
        repeatition=1,
        start_interval=(anchor, anchor),
        end_interval=(end, end),
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1)),
    )
    
    # Pydantic model_dump_json serializes datetimes to strings, which requests/TestClient needs
    # But TestClient json= param expects a dict.
    # We use task.model_dump(mode='json') to get JSON-compatible dict (isoformat strings)
    task_payload = task.model_dump(mode='json')
    
    resp_add = client.post("/tasks/create", headers=headers, json=task_payload)
    assert resp_add.status_code == 200
    assert resp_add.json()["message"] == "Task added successfully"
    
    # 3. Solve Schedule
    solve_payload = {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z"
    }
    resp_solve = client.post("/scheduler/solve", headers=headers, json=solve_payload)
    assert resp_solve.status_code == 200
    result = resp_solve.json()
    assert result["status"] == "Solved"
    
    # Check if we got intervals back
    intervals = result["intervals"]
    assert str(task.id) in intervals
    assert len(intervals[str(task.id)]) == 1
    
    # Verify persistence: check if {user_id}.json exists in data dir
    user_id = user_data["user_id"]
    expected_path = os.path.join(settings.data_dir, f"{user_id}.json")
    assert os.path.exists(expected_path)

def test_auth_failure():
    resp = client.post("/tasks/create", headers={"X-API-Key": "INVALID"}, json={})
    assert resp.status_code == 401
