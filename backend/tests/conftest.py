"""Test configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.tmdb import init_tmdb_client, close_tmdb_client, TMDBClient
from app.tmdb import TMDBConfigError


@pytest.fixture
async def async_client():
    """Create a test client with proper lifespan management."""
    await init_tmdb_client()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_tmdb_client()


@pytest.fixture
def mock_tmdb_client():
    """Mock TMDB client for tests (configured)."""
    import app.tmdb.client as tmdb_client_module
    tmdb_client_module._tmdb_client = None

    with patch("app.api.search.get_tmdb_client") as mock_search, \
         patch("app.api.recommend.get_tmdb_client") as mock_recommend, \
         patch("app.api.favorites.get_tmdb_client") as mock_favorites, \
         patch("app.tmdb.get_tmdb_client") as mock_tmdb:
        mock_client = MagicMock(spec=TMDBClient)
        mock_client.is_configured = True
        mock_search.return_value = mock_client
        mock_recommend.return_value = mock_client
        mock_favorites.return_value = mock_client
        mock_tmdb.return_value = mock_client
        yield mock_client

    tmdb_client_module._tmdb_client = None


@pytest.fixture
def mock_tmdb_client_unconfigured():
    """Mock TMDB client without credentials."""
    import app.tmdb.client as tmdb_client_module
    tmdb_client_module._tmdb_client = None

    with patch("app.api.search.get_tmdb_client") as mock_search, \
         patch("app.api.recommend.get_tmdb_client") as mock_recommend, \
         patch("app.api.favorites.get_tmdb_client") as mock_favorites, \
         patch("app.tmdb.get_tmdb_client") as mock_tmdb:
        mock_client = MagicMock(spec=TMDBClient)
        mock_client.is_configured = False
        mock_search.return_value = mock_client
        mock_recommend.return_value = mock_client
        mock_favorites.return_value = mock_client
        mock_tmdb.return_value = mock_client
        yield mock_client

    tmdb_client_module._tmdb_client = None