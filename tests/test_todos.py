from fastapi.testclient import TestClient

API_PREFIX = "/api/v1"


def test_create_todo(client: TestClient):
    response = client.post(
        f"{API_PREFIX}/todos/",
        json={
            "title": "Test todo",
            "description": "Testing todo",
            "is_completed": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test todo"


def test_list_todos(client: TestClient):
    client.post(f"{API_PREFIX}/todos/", json={"title": "List todo"})
    response = client.get(f"{API_PREFIX}/todos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_update_todo(client: TestClient):
    created = client.post(f"{API_PREFIX}/todos/", json={"title": "Original"}).json()
    todo_id = created["id"]

    response = client.put(
        f"{API_PREFIX}/todos/{todo_id}",
        json={"title": "Updated", "is_completed": True},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


def test_delete_todo(client: TestClient):
    created = client.post(f"{API_PREFIX}/todos/", json={"title": "Delete me"}).json()
    todo_id = created["id"]

    response = client.delete(f"{API_PREFIX}/todos/{todo_id}")
    assert response.status_code == 204

    follow_up = client.get(f"{API_PREFIX}/todos/{todo_id}")
    assert follow_up.status_code == 404
