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
async def test_create_todo_minimal_fields(client: AsyncClient):
    """Test creating todo with only required title field."""
    response = await client.post(
        f"{API_PREFIX}/todos/",
        json={"title": "Minimal todo"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal todo"
    assert data["description"] is None
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_create_todo_empty_title(client: AsyncClient):
    """Test creating todo with empty title fails validation."""
    response = await client.post(
        f"{API_PREFIX}/todos/",
        json={"title": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_missing_title(client: AsyncClient):
    """Test creating todo without title fails validation."""
    response = await client.post(
        f"{API_PREFIX}/todos/",
        json={"description": "No title"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_long_title(client: AsyncClient):
    """Test creating todo with very long title."""
    long_title = "x" * 500
    response = await client.post(
        f"{API_PREFIX}/todos/",
        json={"title": long_title},
    )
    # API enforces title length; expect validation failure
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_todos(client: AsyncClient):
    await client.post(f"{API_PREFIX}/todos/", json={"title": "List todo"})
    response = await client.get(f"{API_PREFIX}/todos/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data and "total" in data and "limit" in data and "offset" in data
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2
    assert data["total"] >= len(data["items"])


@pytest.mark.asyncio
async def test_list_todos_empty(client: AsyncClient):
    """Test listing todos when none exist."""
    response = await client.get(f"{API_PREFIX}/todos/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_todos_pagination(client: AsyncClient):
    """Test pagination with offset."""
    # Create 5 todos
    for i in range(5):
        await client.post(f"{API_PREFIX}/todos/", json={"title": f"Todo {i}"})

    # Get first page
    response1 = await client.get(f"{API_PREFIX}/todos/?limit=2&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["items"]) == 2

    # Get second page
    response2 = await client.get(f"{API_PREFIX}/todos/?limit=2&offset=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2

    # Ensure different items
    ids1 = {item["id"] for item in data1["items"]}
    ids2 = {item["id"] for item in data2["items"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_list_todos_invalid_limit(client: AsyncClient):
    """Test listing with invalid limit parameter."""
    response = await client.get(f"{API_PREFIX}/todos/?limit=-1&offset=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_todo_by_id(client: AsyncClient):
    """Test retrieving a specific todo by ID."""
    created = (
        await client.post(f"{API_PREFIX}/todos/", json={"title": "Get by ID"})
    ).json()
    todo_id = created["id"]

    response = await client.get(f"{API_PREFIX}/todos/{todo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == todo_id
    assert data["title"] == "Get by ID"


@pytest.mark.asyncio
async def test_get_todo_not_found(client: AsyncClient):
    """Test retrieving non-existent todo returns 404."""
    response = await client.get(f"{API_PREFIX}/todos/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_todo_invalid_id(client: AsyncClient):
    """Test retrieving todo with invalid ID format."""
    response = await client.get(f"{API_PREFIX}/todos/invalid")
    assert response.status_code == 422


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
async def test_update_todo_not_found(client: AsyncClient):
    """Test updating non-existent todo returns 404."""
    response = await client.put(
        f"{API_PREFIX}/todos/99999",
        json={"title": "Does not exist"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_todo_partial(client: AsyncClient):
    """Test partial update - only updating completion status."""
    created = (
        await client.post(
            f"{API_PREFIX}/todos/",
            json={"title": "Original", "description": "Original desc"},
        )
    ).json()
    todo_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/todos/{todo_id}",
        json={"title": "Original", "is_completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Original"
    assert data["is_completed"] is True


@pytest.mark.asyncio
async def test_update_todo_empty_title(client: AsyncClient):
    """Test updating todo with empty title fails validation."""
    created = (
        await client.post(f"{API_PREFIX}/todos/", json={"title": "Original"})
    ).json()
    todo_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/todos/{todo_id}",
        json={"title": ""},
    )
    assert response.status_code == 422


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


@pytest.mark.asyncio
async def test_delete_todo_not_found(client: AsyncClient):
    """Test deleting non-existent todo returns 404."""
    response = await client.delete(f"{API_PREFIX}/todos/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_todo_twice(client: AsyncClient):
    """Test deleting the same todo twice returns 404 on second attempt."""
    created = (
        await client.post(f"{API_PREFIX}/todos/", json={"title": "Delete twice"})
    ).json()
    todo_id = created["id"]

    # First delete
    response1 = await client.delete(f"{API_PREFIX}/todos/{todo_id}")
    assert response1.status_code == 204

    # Second delete should fail
    response2 = await client.delete(f"{API_PREFIX}/todos/{todo_id}")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_concurrent_creates(client: AsyncClient):
    """Test creating multiple todos concurrently."""
    import asyncio

    async def create_todo(title: str):
        return await client.post(
            f"{API_PREFIX}/todos/",
            json={"title": title},
        )

    # Create 5 todos concurrently
    tasks = [create_todo(f"Concurrent {i}") for i in range(5)]
    responses = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r.status_code == 201 for r in responses)

    # All should have unique IDs
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 5
