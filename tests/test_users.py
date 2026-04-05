import pytest
from httpx import AsyncClient

API_PREFIX = "/api/v1"


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test.user@example.com"


@pytest.mark.asyncio
async def test_create_user_minimal_fields(client: AsyncClient):
    """Test creating user with required fields only."""
    response = await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "Minimal",
            "last_name": "User",
            "email": "minimal.user@example.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Minimal"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_user_empty_first_name(client: AsyncClient):
    response = await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": " ",
            "last_name": "User",
            "email": "invalid.user@example.com",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_missing_email(client: AsyncClient):
    response = await client.post(
        f"{API_PREFIX}/users/",
        json={"first_name": "No", "last_name": "Email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient):
    response = await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "Bad",
            "last_name": "Email",
            "email": "invalid-email",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient):
    await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "List",
            "last_name": "User",
            "email": "list.user@example.com",
        },
    )
    response = await client.get(f"{API_PREFIX}/users/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data and "total" in data and "limit" in data and "offset" in data
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2
    assert data["total"] >= len(data["items"])


@pytest.mark.asyncio
async def test_list_users_empty(client: AsyncClient):
    """Test listing users when none exist."""
    response = await client.get(f"{API_PREFIX}/users/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient):
    for i in range(5):
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": f"Page{i}",
                "last_name": "User",
                "email": f"page{i}.user@example.com",
            },
        )

    response1 = await client.get(f"{API_PREFIX}/users/?limit=2&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["items"]) == 2

    response2 = await client.get(f"{API_PREFIX}/users/?limit=2&offset=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2

    ids1 = {item["id"] for item in data1["items"]}
    ids2 = {item["id"] for item in data2["items"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_list_users_invalid_limit(client: AsyncClient):
    """Test listing with invalid limit parameter."""
    response = await client.get(f"{API_PREFIX}/users/?limit=-1&offset=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_users_by_partial_first_name(client: AsyncClient):
    await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "Mariana",
            "last_name": "Stone",
            "email": "mariana.stone@example.com",
        },
    )

    response = await client.get(f"{API_PREFIX}/users/search?q=rian")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["first_name"] == "Mariana" for item in data["items"])


@pytest.mark.asyncio
async def test_search_users_by_partial_last_name(client: AsyncClient):
    await client.post(
        f"{API_PREFIX}/users/",
        json={
            "first_name": "Ava",
            "last_name": "Johnson",
            "email": "ava.johnson@example.com",
        },
    )

    response = await client.get(f"{API_PREFIX}/users/search?q=ohn")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["last_name"] == "Johnson" for item in data["items"])


@pytest.mark.asyncio
async def test_search_users_requires_query(client: AsyncClient):
    response = await client.get(f"{API_PREFIX}/users/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient):
    created = (
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": "Original",
                "last_name": "User",
                "email": "original.user@example.com",
            },
        )
    ).json()
    user_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/users/{user_id}",
        json={"first_name": "Updated", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient):
    response = await client.put(
        f"{API_PREFIX}/users/99999",
        json={"first_name": "Missing"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_partial(client: AsyncClient):
    created = (
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": "Partial",
                "last_name": "User",
                "email": "partial.user@example.com",
            },
        )
    ).json()
    user_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/users/{user_id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Partial"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_invalid_email(client: AsyncClient):
    created = (
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": "Invalid",
                "last_name": "Email",
                "email": "invalid.email@example.com",
            },
        )
    ).json()
    user_id = created["id"]

    response = await client.put(
        f"{API_PREFIX}/users/{user_id}",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient):
    created = (
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": "Delete",
                "last_name": "Me",
                "email": "delete.me@example.com",
            },
        )
    ).json()
    user_id = created["id"]

    response = await client.delete(f"{API_PREFIX}/users/{user_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"{API_PREFIX}/users/search?q=Delete")
    assert follow_up.status_code == 200
    assert all(item["id"] != user_id for item in follow_up.json()["items"])


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient):
    response = await client.delete(f"{API_PREFIX}/users/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_twice(client: AsyncClient):
    created = (
        await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": "Delete",
                "last_name": "Twice",
                "email": "delete.twice@example.com",
            },
        )
    ).json()
    user_id = created["id"]
    response1 = await client.delete(f"{API_PREFIX}/users/{user_id}")
    assert response1.status_code == 204
    response2 = await client.delete(f"{API_PREFIX}/users/{user_id}")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_concurrent_creates(client: AsyncClient):
    import asyncio

    async def create_user(index: int):
        return await client.post(
            f"{API_PREFIX}/users/",
            json={
                "first_name": f"Concurrent{index}",
                "last_name": "User",
                "email": f"concurrent{index}.user@example.com",
            },
        )

    tasks = [create_user(i) for i in range(5)]
    responses = await asyncio.gather(*tasks)
    assert all(r.status_code == 201 for r in responses)
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 5
