"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health check endpoint returns healthy status."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "tmdb_configured" in data
    assert isinstance(data["tmdb_configured"], bool)


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test root endpoint."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Smart Movie Recommender API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"