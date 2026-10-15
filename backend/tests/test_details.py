"""Tests for media details and favorites resolution endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.tmdb import (
    TMDBClient,
    TMDBConfigError,
    TMDBAuthError,
    TMDBRateLimitError,
    TMDBUpstreamError,
    TMDBTimeoutError,
    TMDBNetworkError,
    TMDBNotFoundError,
)
from app.tmdb.models import (
    TMDBMovieDetails,
    TMDBTVSeriesDetails,
    TMDBCredits,
    TMDBKeywords,
    TMDBCastMember,
    TMDBCrewMember,
    TMDBKeyword,
    TMDBGenre,
    TMDBProductionCompany,
    TMDBProductionCountry,
    TMDBSpokenLanguage,
)


class TestMediaDetails:
    """Tests for media details endpoint."""

    @pytest.fixture
    def mock_tmdb_client(self):
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_movie_details_success(self, async_client, mock_tmdb_client):
        """Movie details should return full normalized metadata."""
        mock_details = TMDBMovieDetails(
            id=123,
            title="Inception",
            original_title="Inception",
            overview="A thief who steals corporate secrets...",
            release_date="2010-07-16",
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
            vote_average=8.8,
            vote_count=1000,
            popularity=100.0,
            original_language="en",
            genres=[
                TMDBGenre(id=28, name="Action"),
                TMDBGenre(id=878, name="Science Fiction"),
            ],
            runtime=148,
            tagline="Your mind is the scene of the crime",
            homepage="http://example.com",
            production_companies=[
                TMDBProductionCompany(id=1, name="Warner Bros", logo_path="/logo.jpg", origin_country="US"),
            ],
            production_countries=[
                TMDBProductionCountry(iso_3166_1="US", name="United States"),
            ],
            spoken_languages=[
                TMDBSpokenLanguage(english_name="English", iso_639_1="en", name="English"),
            ],
            status="Released",
            adult=False,
            video=False,
        )
        mock_credits = TMDBCredits(
            id=123,
            cast=[
                TMDBCastMember(id=1, name="Leonardo DiCaprio", character="Cobb", profile_path="/actor.jpg", order=0),
            ],
            crew=[
                TMDBCrewMember(id=2, name="Christopher Nolan", job="Director", department="Directing", profile_path="/director.jpg"),
                TMDBCrewMember(id=3, name="Emma Thomas", job="Producer", department="Production", profile_path=None),
            ],
        )
        mock_keywords = TMDBKeywords(
            id=123,
            keywords=[
                TMDBKeyword(id=1, name="dream"),
                TMDBKeyword(id=2, name="heist"),
            ],
        )

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value="https://image.tmdb.org/t/p/w342/poster.jpg")
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value="https://image.tmdb.org/t/p/w780/backdrop.jpg")
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/profile.jpg")

        response = await async_client.get("/api/search/movie/123")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 123
        assert data["title"] == "Inception"
        assert data["media_type"] == "movie"
        assert data["release_date"] == "2010-07-16"
        assert data["overview"] == "A thief who steals corporate secrets..."
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
        assert data["backdrop_url"] == "https://image.tmdb.org/t/p/w780/backdrop.jpg"
        assert data["vote_average"] == 8.8
        assert data["runtime"] == 148
        assert len(data["genres"]) == 2
        assert data["genres"][0]["name"] == "Action"
        assert len(data["production_companies"]) == 1
        assert data["production_companies"][0]["name"] == "Warner Bros"
        assert len(data["cast"]) == 1
        assert data["cast"][0]["name"] == "Leonardo DiCaprio"
        assert data["cast"][0]["character"] == "Cobb"
        assert len(data["crew"]) == 2
        assert len(data["directors"]) == 1
        assert data["directors"][0]["name"] == "Christopher Nolan"
        assert len(data["keywords"]) == 2
        assert data["keywords"][0]["name"] == "dream"

    @pytest.mark.asyncio
    async def test_tv_details_success(self, async_client, mock_tmdb_client):
        """TV series details should return full normalized metadata."""
        mock_details = TMDBTVSeriesDetails(
            id=456,
            name="Breaking Bad",
            original_name="Breaking Bad",
            overview="A chemistry teacher diagnosed with cancer...",
            first_air_date="2008-01-20",
            poster_path="/tv_poster.jpg",
            backdrop_path="/tv_backdrop.jpg",
            vote_average=9.5,
            vote_count=2000,
            popularity=200.0,
            original_language="en",
            genres=[
                TMDBGenre(id=18, name="Drama"),
                TMDBGenre(id=80, name="Crime"),
            ],
            episode_run_time=[47],
            number_of_seasons=5,
            number_of_episodes=62,
            status="Ended",
            tagline="",
            homepage="http://example.com",
            production_companies=[
                TMDBProductionCompany(id=2, name="Sony Pictures Television", logo_path="/logo2.jpg", origin_country="US"),
            ],
            production_countries=[
                TMDBProductionCountry(iso_3166_1="US", name="United States"),
            ],
            spoken_languages=[
                TMDBSpokenLanguage(english_name="English", iso_639_1="en", name="English"),
            ],
            origin_country=["US"],
            networks=[],
            created_by=[],
        )
        mock_credits = TMDBCredits(
            id=456,
            cast=[
                TMDBCastMember(id=10, name="Bryan Cranston", character="Walter White", profile_path="/actor2.jpg", order=0),
            ],
            crew=[
                TMDBCrewMember(id=11, name="Vince Gilligan", job="Director", department="Directing", profile_path="/director2.jpg"),
            ],
        )
        mock_keywords = TMDBKeywords(
            id=456,
            keywords=[
                TMDBKeyword(id=10, name="drugs"),
                TMDBKeyword(id=11, name="chemistry"),
            ],
        )

        import asyncio
        mock_tmdb_client.get_tv_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_tv_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_tv_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value="https://image.tmdb.org/t/p/w342/tv_poster.jpg")
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value="https://image.tmdb.org/t/p/w780/tv_backdrop.jpg")
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/profile2.jpg")

        response = await async_client.get("/api/search/tv/456")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 456
        assert data["title"] == "Breaking Bad"
        assert data["media_type"] == "tv"
        assert data["first_air_date"] == "2008-01-20"
        assert data["number_of_seasons"] == 5
        assert data["number_of_episodes"] == 62
        assert data["episode_run_time"] == [47]
        assert len(data["genres"]) == 2
        assert len(data["directors"]) == 1
        assert data["directors"][0]["name"] == "Vince Gilligan"

    @pytest.mark.asyncio
    async def test_movie_details_missing_optional_fields(self, async_client, mock_tmdb_client):
        """Missing optional fields should be null, not fabricated."""
        mock_details = TMDBMovieDetails(
            id=999,
            title="Minimal Movie",
            original_title="Minimal Movie",
            overview=None,
            release_date=None,
            poster_path=None,
            backdrop_path=None,
            vote_average=None,
            vote_count=0,
            popularity=0.0,
            original_language="xx",
            genres=[],
            runtime=None,
            tagline=None,
            homepage=None,
            production_companies=[],
            production_countries=[],
            spoken_languages=[],
            status=None,
        )
        mock_credits = TMDBCredits(id=999, cast=[], crew=[])
        mock_keywords = TMDBKeywords(id=999, keywords=[])

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search/movie/999")
        assert response.status_code == 200
        data = response.json()

        assert data["overview"] is None
        assert data["release_date"] is None
        assert data["poster_url"] is None
        assert data["backdrop_url"] is None
        assert data["vote_average"] is None
        assert data["runtime"] is None
        assert data["genres"] == []
        assert data["cast"] == []
        assert data["keywords"] == []

    @pytest.mark.asyncio
    async def test_tv_details_missing_optional_fields(self, async_client, mock_tmdb_client):
        """TV missing optional fields should be null."""
        mock_details = TMDBTVSeriesDetails(
            id=888,
            name="Minimal TV",
            original_name="Minimal TV",
            overview=None,
            first_air_date=None,
            poster_path=None,
            backdrop_path=None,
            vote_average=None,
            vote_count=0,
            popularity=0.0,
            original_language="xx",
            genres=[],
            episode_run_time=[],
            number_of_seasons=0,
            number_of_episodes=0,
            status=None,
            tagline=None,
            homepage=None,
            production_companies=[],
            production_countries=[],
            spoken_languages=[],
            origin_country=[],
            networks=[],
            created_by=[],
        )
        mock_credits = TMDBCredits(id=888, cast=[], crew=[])
        mock_keywords = TMDBKeywords(id=888, keywords=[])

        import asyncio
        mock_tmdb_client.get_tv_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_tv_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_tv_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search/tv/888")
        assert response.status_code == 200
        data = response.json()

        assert data["first_air_date"] is None
        assert data["number_of_seasons"] == 0
        assert data["episode_run_time"] == []
        assert data["overview"] is None

    @pytest.mark.asyncio
    async def test_invalid_media_type_returns_400(self, async_client):
        """Invalid media type should return 400."""
        response = await async_client.get("/api/search/invalid/123")
        assert response.status_code == 400
        data = response.json()
        assert "media_type must be 'movie' or 'tv'" in data["detail"]

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, async_client, mock_tmdb_client):
        """Not found should return 404."""
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=TMDBNotFoundError("Not found"))

        response = await async_client.get("/api/search/movie/999999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_auth_error_returns_401(self, async_client, mock_tmdb_client):
        """Auth error should return 401."""
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=TMDBAuthError("Invalid token"))

        response = await async_client.get("/api/search/movie/123")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, async_client, mock_tmdb_client):
        """Rate limit should return 429."""
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=TMDBRateLimitError("Rate limited", retry_after=30))

        response = await async_client.get("/api/search/movie/123")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_without_credentials_returns_503(self, async_client, mock_tmdb_client_unconfigured):
        """Without credentials should return 503."""
        response = await async_client.get("/api/search/movie/123")
        assert response.status_code == 503


class TestFavoritesResolution:
    """Tests for favorites resolution endpoint."""

    @pytest.fixture
    def mock_tmdb_client(self):
        # Need to patch at the source (app.tmdb) and reset the global cache
        import app.tmdb.client as tmdb_client_module
        tmdb_client_module._tmdb_client = None
        
        # Patch where it's used in favorites module
        with patch("app.api.favorites.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client
        
        # Cleanup
        tmdb_client_module._tmdb_client = None

    @pytest.mark.asyncio
    async def test_resolve_favorites_success(self, async_client, mock_tmdb_client):
        """Resolve favorites should return resolved titles."""
        mock_details = TMDBMovieDetails(
            id=123,
            title="Inception",
            original_title="Inception",
            overview="A thief...",
            release_date="2010-07-16",
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
            vote_average=8.8,
            vote_count=1000,
            popularity=100.0,
            original_language="en",
            genres=[TMDBGenre(id=28, name="Action")],
            runtime=148,
            tagline="Tagline",
            homepage="http://example.com",
            production_companies=[
                TMDBProductionCompany(id=1, name="Warner Bros", logo_path="/logo.jpg", origin_country="US"),
            ],
            production_countries=[TMDBProductionCountry(iso_3166_1="US", name="United States")],
            spoken_languages=[TMDBSpokenLanguage(english_name="English", iso_639_1="en", name="English")],
            status="Released",
        )
        mock_credits = TMDBCredits(
            id=123,
            cast=[TMDBCastMember(id=1, name="Leonardo DiCaprio", character="Cobb", order=0)],
            crew=[TMDBCrewMember(id=2, name="Christopher Nolan", job="Director", department="Directing")],
        )
        mock_keywords = TMDBKeywords(
            id=123,
            keywords=[TMDBKeyword(id=1, name="dream")],
        )

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value="https://image.tmdb.org/t/p/w342/poster.jpg")
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value="https://image.tmdb.org/t/p/w780/backdrop.jpg")
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/profile.jpg")

        response = await async_client.post(
            "/api/favorites/resolve",
            json={"titles": [{"media_type": "movie", "item_id": 123}]}
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["resolved"]) == 1
        assert data["resolved"][0]["id"] == 123
        assert data["resolved"][0]["title"] == "Inception"
        assert data["failed"] == []

    @pytest.mark.asyncio
    async def test_resolve_favorites_partial_failure(self, async_client, mock_tmdb_client):
        """Resolve favorites should handle partial failures."""
        # First succeeds, second fails
        mock_details = TMDBMovieDetails(
            id=123, title="Success", original_title="Success", original_language="en",
            genres=[], production_companies=[], production_countries=[], spoken_languages=[],
        )
        mock_credits = TMDBCredits(id=123, cast=[], crew=[])
        mock_keywords = TMDBKeywords(id=123, keywords=[])

        import asyncio
        # First call succeeds, second raises error
        call_count = 0

        async def mock_get_details(item_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_details
            raise TMDBNotFoundError("Not found")

        mock_tmdb_client.get_movie_details = mock_get_details
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)

        response = await async_client.post(
            "/api/favorites/resolve",
            json={
                "titles": [
                    {"media_type": "movie", "item_id": 123},
                    {"media_type": "movie", "item_id": 999999},
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["resolved"]) == 1
        assert len(data["failed"]) == 1
        assert data["failed"][0]["item_id"] == 999999
        assert data["failed"][0]["code"] == "TMDB_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_resolve_favorites_deduplication(self, async_client, mock_tmdb_client):
        """Resolve favorites should deduplicate while preserving order."""
        mock_details = TMDBMovieDetails(
            id=123, title="Inception", original_title="Inception", original_language="en",
            genres=[], production_companies=[], production_countries=[], spoken_languages=[],
        )
        mock_credits = TMDBCredits(id=123, cast=[], crew=[])
        mock_keywords = TMDBKeywords(id=123, keywords=[])

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)

        # Request with duplicates
        response = await async_client.post(
            "/api/favorites/resolve",
            json={
                "titles": [
                    {"media_type": "movie", "item_id": 123},
                    {"media_type": "movie", "item_id": 456},
                    {"media_type": "movie", "item_id": 123},  # duplicate
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Should only resolve 2 unique titles
        assert len(data["resolved"]) == 2
        # Verify get_movie_details was only called twice
        assert mock_tmdb_client.get_movie_details.call_count == 2

    @pytest.mark.asyncio
    async def test_resolve_favorites_empty_returns_422(self, async_client):
        """Empty favorites list should return 422 (Pydantic validation)."""
        response = await async_client.post(
            "/api/favorites/resolve",
            json={"titles": []}
        )
        assert response.status_code == 422
        data = response.json()
        # Pydantic validation error format
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_resolve_favorites_too_many_returns_422(self, async_client):
        """Too many favorites should return 422 (Pydantic validation)."""
        titles = [{"media_type": "movie", "item_id": i} for i in range(51)]
        response = await async_client.post(
            "/api/favorites/resolve",
            json={"titles": titles}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_resolve_favorites_without_credentials_returns_failed(self, async_client, mock_tmdb_client):
        """Without credentials should return failed items in response."""
        # Configure mock to raise config error on all three methods
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=TMDBConfigError())
        mock_tmdb_client.get_movie_credits = AsyncMock(side_effect=TMDBConfigError())
        mock_tmdb_client.get_movie_keywords = AsyncMock(side_effect=TMDBConfigError())

        response = await async_client.post(
            "/api/favorites/resolve",
            json={"titles": [{"media_type": "movie", "item_id": 123}]}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["resolved"]) == 0
        assert len(data["failed"]) == 1
        assert data["failed"][0]["code"] == "TMDB_NOT_CONFIGURED"
        assert "TMDB API credentials not configured" in data["failed"][0]["error"]


class TestCreditsAndKeywordsNormalization:
    """Tests for credits and keywords normalization."""

    @pytest.fixture
    def mock_tmdb_client(self):
        with patch("app.api.search.get_tmdb_client") as mock_get_client:
            mock_client = MagicMock(spec=TMDBClient)
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_cast_normalization_includes_profile_urls(self, async_client, mock_tmdb_client):
        """Cast should include profile URLs when available."""
        mock_details = TMDBMovieDetails(
            id=1, title="Test", original_title="Test", original_language="en",
            genres=[], production_companies=[], production_countries=[], spoken_languages=[],
        )
        mock_credits = TMDBCredits(
            id=1,
            cast=[
                TMDBCastMember(id=1, name="Actor One", character="Hero", profile_path="/actor1.jpg", order=0),
                TMDBCastMember(id=2, name="Actor Two", character="Villain", profile_path=None, order=1),
            ],
            crew=[],
        )
        mock_keywords = TMDBKeywords(id=1, keywords=[])

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/actor1.jpg")

        response = await async_client.get("/api/search/movie/1")
        assert response.status_code == 200
        data = response.json()

        assert len(data["cast"]) == 2
        assert data["cast"][0]["profile_url"] == "https://image.tmdb.org/t/p/w185/actor1.jpg"
        assert data["cast"][1]["profile_url"] is None

    @pytest.mark.asyncio
    async def test_directors_extracted_from_crew(self, async_client, mock_tmdb_client):
        """Directors should be extracted from crew."""
        mock_details = TMDBMovieDetails(
            id=1, title="Test", original_title="Test", original_language="en",
            genres=[], production_companies=[], production_countries=[], spoken_languages=[],
        )
        mock_credits = TMDBCredits(
            id=1,
            cast=[],
            crew=[
                TMDBCrewMember(id=1, name="Director One", job="Director", department="Directing"),
                TMDBCrewMember(id=2, name="Producer One", job="Producer", department="Production"),
                TMDBCrewMember(id=3, name="Director Two", job="Director", department="Directing"),
                TMDBCrewMember(id=4, name="Writer One", job="Screenplay", department="Writing"),
            ],
        )
        mock_keywords = TMDBKeywords(id=1, keywords=[])

        import asyncio
        mock_tmdb_client.get_movie_details = AsyncMock(return_value=mock_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=mock_credits)
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=mock_keywords)
        mock_tmdb_client.get_poster_url = MagicMock(return_value=None)
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value=None)

        response = await async_client.get("/api/search/movie/1")
        assert response.status_code == 200
        data = response.json()

        assert len(data["directors"]) == 2
        assert data["directors"][0]["name"] == "Director One"
        assert data["directors"][1]["name"] == "Director Two"
        # Producer and writer should not be in directors
        director_names = {d["name"] for d in data["directors"]}
        assert "Producer One" not in director_names
        assert "Writer One" not in director_names