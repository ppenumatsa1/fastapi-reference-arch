import pytest
from httpx import AsyncClient

API_PREFIX = "/api/v1"


@pytest.mark.asyncio
async def test_create_todo(client: AsyncClient):
    response = await client.post(
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


@pytest.mark.asyncio
async def test_list_todos(client: AsyncClient):
    await client.post(f"{API_PREFIX}/todos/", json={"title": "List todo"})
    response = await client.get(f"{API_PREFIX}/todos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_todo(client: AsyncClient):
    created = (
        await client.post(f"{API_PREFIX}/todos/", json={"title": "Original"})
    ).json()
    todo_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/todos/{todo_id}",
        json={"title": "Updated", "is_completed": True},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_delete_todo(client: AsyncClient):
    created = (
        await client.post(f"{API_PREFIX}/todos/", json={"title": "Delete me"})
    ).json()
    todo_id = created["id"]

    response = await client.delete(f"{API_PREFIX}/todos/{todo_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"{API_PREFIX}/todos/{todo_id}")
    assert follow_up.status_code == 404
