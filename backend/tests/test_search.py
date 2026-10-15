"""Tests for search API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.tmdb import (
    TMDBClient,
    TMDBConfigError,
    TMDBAuthError,
    TMDBRateLimitError,
    TMDBUpstreamError,
    TMDBTimeoutError,
    TMDBNetworkError,
)
from app.tmdb.models import (
    TMDBMultiSearchResult,
    TMDBPaginatedResponse,
)


class TestSearchValidation:
    """Tests for search parameter validation."""

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_422(self, async_client):
        """Empty query should return 422 (FastAPI validation)."""
        response = await async_client.get("/api/search?query=&type=multi")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_whitespace_query_returns_400(self, async_client):
        """Whitespace-only query should return 400 (custom validation)."""
        response = await async_client.get("/api/search?query=   &type=multi")
        assert response.status_code == 400
        data = response.json()
        assert "empty or whitespace" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_missing_query_returns_422(self, async_client):
        """Missing query parameter should return 422."""
        response = await async_client.get("/api/search?type=multi")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_invalid_type_returns_422(self, async_client):
        """Invalid search type should return 422 (FastAPI pattern validation)."""
        response = await async_client.get("/api/search?query=test&type=invalid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_valid_types_accepted(self, async_client):
        """Valid search types should be accepted (but fail on missing creds)."""
        for search_type in ["multi", "movie", "tv"]:
            response = await async_client.get(f"/api/search?query=test&type={search_type}")
            # Should not be 422 for valid type
            assert response.status_code != 422

    @pytest.mark.asyncio
    async def test_search_page_validation(self, async_client):
        """Page parameter validation."""
        # Page 0 should fail
        response = await async_client.get("/api/search?query=test&page=0")
        assert response.status_code == 422

        # Page > 1000 should fail
        response = await async_client.get("/api/search?query=test&page=1001")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_language_format(self, async_client):
        """Language parameter format validation."""
        response = await async_client.get("/api/search?query=test&language=invalid")
        assert response.status_code == 422


class TestSearchMissingCredentials:
    """Tests for missing TMDB credentials."""

    @pytest.mark.asyncio
    async def test_search_without_credentials_returns_503(self, async_client, mock_tmdb_client_unconfigured):
        """Search without TMDB token should return 503."""
        response = await async_client.get("/api/search?query=inception&type=multi")
        assert response.status_code == 503
        data = response.json()
        assert "TMDB API credentials not configured" in data["detail"]
        # Error code is in X-Error-Code header
        assert response.headers.get("X-Error-Code") == "TMDB_NOT_CONFIGURED"


class TestSearchNormalization:
    """Tests for search result normalization."""

    @pytest.fixture
    def mock_tmdb_client(self):
        """Create a mock TMDB client."""
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_movie_result_normalization(self, async_client, mock_tmdb_client):
        """Movie results should be normalized correctly."""
        mock_response = TMDBPaginatedResponse(
            page=1,
            results=[
                TMDBMultiSearchResult(
                    id=123,
                    media_type="movie",
                    title="Inception",
                    original_title="Inception",
                    overview="A thief who steals corporate secrets...",
                    release_date="2010-07-16",
                    poster_path="/path/to/poster.jpg",
                    vote_average=8.8,
                    vote_count=1000,
                    popularity=100.0,
                    original_language="en",
                    genre_ids=[28, 878],
                )
            ],
            total_pages=1,
            total_results=1,
        )
        mock_tmdb_client.search_multi = AsyncMock(return_value=mock_response)
        mock_tmdb_client.get_poster_url = MagicMock(
            return_value="https://image.tmdb.org/t/p/w342/path/to/poster.jpg"
        )

        response = await async_client.get("/api/search?query=inception&type=multi")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["id"] == 123
        assert result["title"] == "Inception"
        assert result["media_type"] == "movie"
        assert result["release_date"] == "2010-07-16"
        assert result["first_air_date"] is None
        assert result["overview"] == "A thief who steals corporate secrets..."
        assert result["poster_path"] == "/path/to/poster.jpg"
        assert result["poster_url"] == "https://image.tmdb.org/t/p/w342/path/to/poster.jpg"
        assert result["vote_average"] == 8.8
        assert result["genre_ids"] == [28, 878]

    @pytest.mark.asyncio
    async def test_tv_result_normalization(self, async_client, mock_tmdb_client):
        """TV series results should be normalized correctly."""
        mock_response = TMDBPaginatedResponse(
            page=1,
            results=[
                TMDBMultiSearchResult(
                    id=456,
                    media_type="tv",
                    name="Breaking Bad",
                    original_name="Breaking Bad",
                    overview="A chemistry teacher diagnosed with cancer...",
                    first_air_date="2008-01-20",
                    poster_path="/path/to/tv_poster.jpg",
                    vote_average=9.5,
                    vote_count=2000,
                    popularity=200.0,
                    original_language="en",
                    genre_ids=[18, 80],
                    origin_country=["US"],
                )
            ],
            total_pages=1,
            total_results=1,
        )
        mock_tmdb_client.search_multi = AsyncMock(return_value=mock_response)
        mock_tmdb_client.get_poster_url = MagicMock(
            return_value="https://image.tmdb.org/t/p/w342/path/to/tv_poster.jpg"
        )

        response = await async_client.get("/api/search?query=breaking bad&type=multi")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["id"] == 456
        assert result["title"] == "Breaking Bad"
        assert result["media_type"] == "tv"
        assert result["release_date"] is None
        assert result["first_air_date"] == "2008-01-20"

    @pytest.mark.asyncio
    async def test_person_results_excluded(self, async_client, mock_tmdb_client):
        """Person results should be excluded from multi-search."""
        mock_response = TMDBPaginatedResponse(
            page=1,
            results=[
                TMDBMultiSearchResult(
                    id=1,
                    media_type="movie",
                    title="Movie Result",
                    release_date="2020-01-01",
                    poster_path=None,
                    vote_average=7.0,
                    vote_count=100,
                    popularity=50.0,
                    original_language="en",
                    genre_ids=[18],
                ),
                TMDBMultiSearchResult(
                    id=999,
                    media_type="person",
                    name="Leonardo DiCaprio",
                    known_for_department="Acting",
                    popularity=100.0,
                    original_language="en",  # Required field
                ),
                TMDBMultiSearchResult(
                    id=2,
                    media_type="tv",
                    name="TV Result",
                    first_air_date="2019-01-01",
                    poster_path=None,
                    vote_average=8.0,
                    vote_count=50,
                    popularity=30.0,
                    original_language="en",
                    genre_ids=[35],
                    origin_country=["US"],
                ),
            ],
            total_pages=1,
            total_results=3,
        )
        mock_tmdb_client.search_multi = AsyncMock(return_value=mock_response)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 200
        data = response.json()

        # Should only have 2 results (movie + tv), person excluded
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "Movie Result"
        assert data["results"][1]["title"] == "TV Result"

    @pytest.mark.asyncio
    async def test_missing_poster_handled(self, async_client, mock_tmdb_client):
        """Missing poster path should result in null poster_url."""
        mock_response = TMDBPaginatedResponse(
            page=1,
            results=[
                TMDBMultiSearchResult(
                    id=1,
                    media_type="movie",
                    title="No Poster Movie",
                    release_date="2020-01-01",
                    poster_path=None,
                    vote_average=7.0,
                    vote_count=100,
                    popularity=50.0,
                    original_language="en",
                    genre_ids=[18],
                )
            ],
            total_pages=1,
            total_results=1,
        )
        mock_tmdb_client.search_multi = AsyncMock(return_value=mock_response)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 200
        data = response.json()

        assert data["results"][0]["poster_path"] is None
        assert data["results"][0]["poster_url"] is None


class TestSearchPagination:
    """Tests for search pagination."""

    @pytest.fixture
    def mock_tmdb_client(self):
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_search_pagination_passed_to_tmdb(self, async_client, mock_tmdb_client):
        """Page parameter should be passed to TMDB client."""
        mock_response = TMDBPaginatedResponse(
            page=2,
            results=[],
            total_pages=10,
            total_results=200,
        )
        mock_tmdb_client.search_multi = AsyncMock(return_value=mock_response)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search?query=test&type=multi&page=2")
        assert response.status_code == 200

        # Verify the mock was called with page=2
        mock_tmdb_client.search_multi.assert_called_once()
        call_args = mock_tmdb_client.search_multi.call_args
        assert call_args[1]["page"] == 2


class TestSearchErrorHandling:
    """Tests for TMDB error handling."""

    @pytest.fixture
    def mock_tmdb_client(self):
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_auth_error_returns_401(self, async_client, mock_tmdb_client):
        """TMDB auth error should return 401."""
        mock_tmdb_client.search_multi = AsyncMock(
            side_effect=TMDBAuthError("Invalid token")
        )

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 401
        data = response.json()
        assert "authentication failed" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, async_client, mock_tmdb_client):
        """TMDB rate limit should return 429 with Retry-After."""
        mock_tmdb_client.search_multi = AsyncMock(
            side_effect=TMDBRateLimitError("Rate limited", retry_after=30)
        )

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 429
        data = response.json()
        assert "rate limit" in data["detail"].lower()
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_upstream_error_returns_502(self, async_client, mock_tmdb_client):
        """TMDB upstream error should return 502."""
        mock_tmdb_client.search_multi = AsyncMock(
            side_effect=TMDBUpstreamError("TMDB server error")
        )

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_timeout_returns_504(self, async_client, mock_tmdb_client):
        """TMDB timeout should return 504."""
        mock_tmdb_client.search_multi = AsyncMock(
            side_effect=TMDBTimeoutError("Timeout")
        )

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 504

    @pytest.mark.asyncio
    async def test_network_error_returns_503(self, async_client, mock_tmdb_client):
        """Network error should return 503."""
        mock_tmdb_client.search_multi = AsyncMock(
            side_effect=TMDBNetworkError("Network error")
        )

        response = await async_client.get("/api/search?query=test&type=multi")
        assert response.status_code == 503


class TestTMDBClient:
    """Tests for TMDBClient class."""

    def test_client_requires_token_on_request(self):
        """Client should allow creation without token but fail on request."""
        client = TMDBClient(access_token="")
        assert client.is_configured is False

        # Should raise TMDBConfigError when making request
        import asyncio
        async def test_request():
            try:
                await client.search_multi("test")
                assert False, "Should have raised TMDBConfigError"
            except TMDBConfigError:
                pass

        asyncio.run(test_request())

    def test_client_with_token_is_configured(self):
        """Client with token should be configured."""
        client = TMDBClient(access_token="test_token")
        assert client.is_configured is True

    def test_poster_url_without_config_returns_none(self):
        """Poster URL should return None without image config."""
        client = TMDBClient(access_token="test")
        # Don't call start(), so _image_config is None
        url = client.get_poster_url("/some/path.jpg")
        assert url is None

    def test_poster_url_with_path_and_config(self):
        """Poster URL should build correctly with config."""
        client = TMDBClient(access_token="test")
        # Manually set image config for testing
        from app.tmdb.models import TMDBImageConfig, TMDBConfiguration
        client._image_config = TMDBConfiguration(
            images=TMDBImageConfig(
                base_url="http://example.com/t/p/",
                secure_base_url="https://image.tmdb.org/t/p/",
                backdrop_sizes=["w780"],
                logo_sizes=["w185"],
                poster_sizes=["w342", "w500"],
                profile_sizes=["w185"],
                still_sizes=["w185"],
            )
        )
        url = client.get_poster_url("/abc123.jpg", size="w342")
        assert url == "https://image.tmdb.org/t/p/w342/abc123.jpg"


class TestSearchResultNormalizationEdgeCases:
    """Regression tests for specific normalization issues."""

    @pytest.mark.asyncio
    async def test_search_movie_type_uses_tmdbmovie_model(self, async_client):
        """Regression test: search with type=movie should handle TMDBMovie results correctly.
        
        Previously this failed with: AttributeError: 'TMDBMovie' object has no attribute 'media_type'
        """
        from app.tmdb.models import TMDBMovie, TMDBPaginatedResponse
        
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client

            mock_response = TMDBPaginatedResponse(
                page=1,
                results=[
                    TMDBMovie(
                        id=123,
                        title="Inception",
                        original_title="Inception",
                        overview="A thief who steals corporate secrets...",
                        release_date="2010-07-16",
                        poster_path="/path/to/poster.jpg",
                        vote_average=8.8,
                        vote_count=1000,
                        popularity=100.0,
                        original_language="en",
                        genre_ids=[28, 878],
                        adult=False,
                        video=False,
                    )
                ],
                total_pages=1,
                total_results=1,
            )
            mock_client.search_movies = AsyncMock(return_value=mock_response)
            mock_client.get_poster_url = MagicMock(
                return_value="https://image.tmdb.org/t/p/w342/path/to/poster.jpg"
            )

            response = await async_client.get("/api/search?query=inception&type=movie")
            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 1
            result = data["results"][0]
            assert result["id"] == 123
            assert result["title"] == "Inception"
            assert result["media_type"] == "movie"
            assert result["release_date"] == "2010-07-16"
            assert result["first_air_date"] is None

    @pytest.mark.asyncio
    async def test_search_tv_type_uses_tmdbtvseries_model(self, async_client):
        """Regression test: search with type=tv should handle TMDBTVSeries results correctly.
        
        Previously this failed with: AttributeError: 'TMDBTVSeries' object has no attribute 'media_type'
        """
        from app.tmdb.models import TMDBTVSeries, TMDBPaginatedResponse
        
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client

            mock_response = TMDBPaginatedResponse(
                page=1,
                results=[
                    TMDBTVSeries(
                        id=456,
                        name="Breaking Bad",
                        original_name="Breaking Bad",
                        overview="A chemistry teacher diagnosed with cancer...",
                        first_air_date="2008-01-20",
                        poster_path="/path/to/tv_poster.jpg",
                        vote_average=9.5,
                        vote_count=2000,
                        popularity=200.0,
                        original_language="en",
                        genre_ids=[18, 80],
                        origin_country=["US"],
                    )
                ],
                total_pages=1,
                total_results=1,
            )
            mock_client.search_tv = AsyncMock(return_value=mock_response)
            mock_client.get_poster_url = MagicMock(
                return_value="https://image.tmdb.org/t/p/w342/path/to/tv_poster.jpg"
            )

            response = await async_client.get("/api/search?query=breaking+bad&type=tv")
            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 1
            result = data["results"][0]
            assert result["id"] == 456
            assert result["title"] == "Breaking Bad"
            assert result["media_type"] == "tv"
            assert result["release_date"] is None
            assert result["first_air_date"] == "2008-01-20"

    @pytest.mark.asyncio
    async def test_search_multi_excludes_person_results(self, async_client):
        """Regression test: multi search should exclude person results."""
        from app.tmdb.models import TMDBMultiSearchResult, TMDBPaginatedResponse
        
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client

            mock_response = TMDBPaginatedResponse(
                page=1,
                results=[
                    TMDBMultiSearchResult(
                        id=1,
                        media_type="movie",
                        title="Movie Result",
                        release_date="2020-01-01",
                        poster_path=None,
                        vote_average=7.0,
                        vote_count=100,
                        popularity=50.0,
                        original_language="en",
                        genre_ids=[18],
                    ),
                    TMDBMultiSearchResult(
                        id=999,
                        media_type="person",
                        name="Leonardo DiCaprio",
                        known_for_department="Acting",
                        popularity=100.0,
                        original_language="en",
                    ),
                    TMDBMultiSearchResult(
                        id=2,
                        media_type="tv",
                        name="TV Result",
                        first_air_date="2019-01-01",
                        poster_path=None,
                        vote_average=8.0,
                        vote_count=50,
                        popularity=30.0,
                        original_language="en",
                        genre_ids=[35],
                        origin_country=["US"],
                    ),
                ],
                total_pages=1,
                total_results=3,
            )
            mock_client.search_multi = AsyncMock(return_value=mock_response)
            mock_client.get_poster_url = MagicMock(return_value=None)

            response = await async_client.get("/api/search?query=test&type=multi")
            assert response.status_code == 200
            data = response.json()

            # Should only have 2 results (movie + tv), person excluded
            assert len(data["results"]) == 2
            assert data["results"][0]["title"] == "Movie Result"
            assert data["results"][1]["title"] == "TV Result"