"""Regression test for Baahubali recommendation issue.

This test simulates the full recommendation pipeline with Baahubali as a favorite
to diagnose why no recommendations are produced.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.tmdb import (
    TMDBClient,
    TMDBConfigError,
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
    TMDBSimilarResult,
    TMDBPaginatedResponse,
    TMDBDiscoverResult,
    TMDBMovie,
)
from app.schemas import (
    MediaDetailsResponse,
    UserPreference,
    FavoriteTitleRequest,
    RecommendRequest,
    GenreItem,
)


@pytest.fixture
async def async_client():
    """Create async test client with lifespan."""
    from app.tmdb import init_tmdb_client, close_tmdb_client
    await init_tmdb_client()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_tmdb_client()


@pytest.fixture
def mock_tmdb_client():
    """Mock TMDB client for Baahubali test."""
    import app.tmdb.client as tmdb_client_module
    tmdb_client_module._tmdb_client = None

    with patch("app.api.recommend.get_tmdb_client") as mock_get_recommend, \
         patch("app.api.search.get_tmdb_client") as mock_get_search, \
         patch("app.api.favorites.get_tmdb_client") as mock_get_favorites, \
         patch("app.tmdb.get_tmdb_client") as mock_get_tmdb:
        mock_client = MagicMock(spec=TMDBClient)
        mock_client.is_configured = True
        mock_get_recommend.return_value = mock_client
        mock_get_search.return_value = mock_client
        mock_get_favorites.return_value = mock_client
        mock_get_tmdb.return_value = mock_client
        yield mock_client

    tmdb_client_module._tmdb_client = None


class TestBaahubaliRecommendation:
    """Test Baahubali recommendation pipeline with mocked TMDB responses."""

    @pytest.mark.asyncio
    async def test_baahubali_recommendation_pipeline(self, async_client, mock_tmdb_client):
        """Test full recommendation pipeline with Baahubali as favorite.
        
        This test traces through the entire pipeline:
        1. Favorite resolution for Baahubali: The Beginning (TMDB ID 264644)
        2. Similar/recommendations endpoints returning known similar Indian epics
        3. Candidate discovery, filtering, graph search, and ranking
        """
        mock_tmdb_client.is_configured = True

        # --- Setup mock responses ---

        # 1. Favorite resolution: Baahubali: The Beginning (TMDB ID 264644)
        baahubali1_details = TMDBMovieDetails(
            id=264644,
            title="Baahubali: The Beginning",
            original_title="Baahubali: The Beginning",
            overview="The young Shivudu discovers his royal heritage.",
            release_date="2015-07-10",
            poster_path="/baahubali1.jpg",
            backdrop_path="/baahubali1_bg.jpg",
            vote_average=8.0,
            vote_count=5000,
            popularity=150.0,
            original_language="te",
            genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=14, name="Fantasy")],
            runtime=159,
            tagline="",
            homepage="",
            production_companies=[TMDBProductionCompany(id=1, name="Arka Media Works", logo_path="/arka.jpg", origin_country="IN")],
            production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
            spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
            status="Released",
            adult=False,
            video=False,
        )
        baahubali1_credits = TMDBCredits(
            id=264644,
            cast=[
                TMDBCastMember(id=1, name="Prabhas", character="Shivudu/Baahubali", profile_path="/prabhas.jpg", order=0),
                TMDBCastMember(id=2, name="Rana Daggubati", character="Bhallaladeva", profile_path="/rana.jpg", order=1),
                TMDBCastMember(id=3, name="Anushka Shetty", character="Devasena", profile_path="/anushka.jpg", order=2),
            ],
            crew=[
                TMDBCrewMember(id=10, name="S.S. Rajamouli", job="Director", department="Directing", profile_path="/rajamouli.jpg"),
            ]
        )
        baahubali1_keywords = TMDBKeywords(
            id=264644,
            keywords=[
                TMDBKeyword(id=1, name="epic"),
                TMDBKeyword(id=2, name="indian cinema"),
                TMDBKeyword(id=3, name="fantasy action"),
                TMDBKeyword(id=4, name="royal family"),
            ]
        )

        # 2. Similar movies for Baahubali 1
        similar_movies = [
            TMDBMovie(
                id=340949,  # Baahubali 2
                title="Baahubali 2: The Conclusion",
                original_title="Baahubali 2: The Conclusion",
                overview="The conclusion of the epic saga.",
                release_date="2017-04-28",
                poster_path="/baahubali2.jpg",
                backdrop_path="/baahubali2_bg.jpg",
                vote_average=8.2,
                vote_count=4000,
                popularity=200.0,
                original_language="te",
                genre_ids=[28, 12, 14],
                adult=False,
                video=False,
            ),
            TMDBMovie(
                id=441234,  # RRR
                title="RRR",
                original_title="RRR",
                overview="A fictional story about two Indian revolutionaries.",
                release_date="2022-03-25",
                poster_path="/rrr.jpg",
                backdrop_path="/rrr_bg.jpg",
                vote_average=7.8,
                vote_count=3000,
                popularity=180.0,
                original_language="te",
                genre_ids=[28, 12, 18],
                adult=False,
                video=False,
            ),
            TMDBMovie(
                id=556789,  # Magadheera
                title="Magadheera",
                original_title="Magadheera",
                overview="A warrior's reincarnation story.",
                release_date="2009-07-31",
                poster_path="/magadheera.jpg",
                backdrop_path="/magadheera_bg.jpg",
                vote_average=7.7,
                vote_count=2000,
                popularity=100.0,
                original_language="te",
                genre_ids=[28, 14, 10749],
                adult=False,
                video=False,
            ),
        ]

        # 3. Recommendations for Baahubali 1
        rec_movies = [
            TMDBMovie(
                id=778899,  # Eega
                title="Eega",
                original_title="Eega",
                overview="A fly seeks revenge.",
                release_date="2012-07-06",
                poster_path="/eega.jpg",
                backdrop_path="/eega_bg.jpg",
                vote_average=7.5,
                vote_count=1500,
                popularity=90.0,
                original_language="te",
                genre_ids=[14, 28, 10749],
                adult=False,
                video=False,
            ),
        ]

        # 4. Similar/Recommendations for Baahubali 2 (if also in favorites)
        similar_baahubali2 = [
            TMDBMovie(
                id=264644,  # Baahubali 1 (should be filtered as favorite)
                title="Baahubali: The Beginning",
                original_title="Baahubali: The Beginning",
                overview="The young Shivudu discovers his royal heritage.",
                release_date="2015-07-10",
                poster_path="/baahubali1.jpg",
                backdrop_path="/baahubali1_bg.jpg",
                vote_average=8.0,
                vote_count=5000,
                popularity=150.0,
                original_language="te",
                genre_ids=[28, 12, 14],
                adult=False,
                video=False,
            ),
        ]

        # --- Setup mock client responses ---

        # Favorite resolution
        async def resolve_favorite(fav_request):
            if fav_request.item_id == 264644 and fav_request.media_type == "movie":
                return (baahubali1_details, baahubali1_credits, baahubali1_keywords)
            elif fav_request.item_id == 340949 and fav_request.media_type == "movie":
                # Baahubali 2 details
                baahubali2_details = TMDBMovieDetails(
                    id=340949,
                    title="Baahubali 2: The Conclusion",
                    original_title="Baahubali 2: The Conclusion",
                    overview="The conclusion of the epic saga.",
                    release_date="2017-04-28",
                    poster_path="/baahubali2.jpg",
                    backdrop_path="/baahubali2_bg.jpg",
                    vote_average=8.2,
                    vote_count=4000,
                    popularity=200.0,
                    original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=14, name="Fantasy")],
                    runtime=171,
                    tagline="",
                    homepage="",
                    production_companies=[TMDBProductionCompany(id=1, name="Arka Media Works", logo_path="/arka.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released",
                    adult=False,
                    video=False,
                )
                baahubali2_credits = TMDBCredits(id=340949, cast=[], crew=[])
                baahubali2_keywords = TMDBKeywords(id=340949, keywords=[])
                return (baahubali2_details, baahubali2_credits, baahubali2_keywords)
            return (None, None, None)

        # Mock _resolve_favorites_async behavior
        async def mock_get_movie_details(movie_id):
            if movie_id == 264644:
                return baahubali1_details
            elif movie_id == 340949:
                baahubali2_details = TMDBMovieDetails(
                    id=340949, title="Baahubali 2: The Conclusion", original_title="Baahubali 2: The Conclusion",
                    overview="The conclusion of the epic saga.", release_date="2017-04-28",
                    poster_path="/baahubali2.jpg", backdrop_path="/baahubali2_bg.jpg",
                    vote_average=8.2, vote_count=4000, popularity=200.0, original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=14, name="Fantasy")],
                    runtime=171, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=1, name="Arka Media Works", logo_path="/arka.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
                return baahubali2_details
            elif movie_id == 340949:  # Baahubali 2
                return baahubali2_details
            elif movie_id == 441234:  # RRR
                return TMDBMovieDetails(
                    id=441234, title="RRR", original_title="RRR",
                    overview="A fictional story about two Indian revolutionaries.",
                    release_date="2022-03-25", poster_path="/rrr.jpg", backdrop_path="/rrr_bg.jpg",
                    vote_average=7.8, vote_count=3000, popularity=180.0, original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=18, name="Drama")],
                    runtime=187, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=2, name="DVV Entertainment", logo_path="/dvv.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
            elif movie_id == 556789:  # Magadheera
                return TMDBMovieDetails(
                    id=556789, title="Magadheera", original_title="Magadheera",
                    overview="A warrior's reincarnation story.",
                    release_date="2009-07-31", poster_path="/magadheera.jpg", backdrop_path="/magadheera_bg.jpg",
                    vote_average=7.7, vote_count=2000, popularity=100.0, original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=14, name="Fantasy"), TMDBGenre(id=10749, name="Romance")],
                    runtime=156, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=3, name="Geetha Arts", logo_path="/geetha.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
            elif movie_id == 778899:  # Eega
                return TMDBMovieDetails(
                    id=778899, title="Eega", original_title="Eega",
                    overview="A fly seeks revenge.",
                    release_date="2012-07-06", poster_path="/eega.jpg", backdrop_path="/eega_bg.jpg",
                    vote_average=7.5, vote_count=1500, popularity=90.0, original_language="te",
                    genres=[TMDBGenre(id=14, name="Fantasy"), TMDBGenre(id=28, name="Action"), TMDBGenre(id=10749, name="Romance")],
                    runtime=145, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=4, name="Vyjayanthi Movies", logo_path="/vyjayanthi.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
            return None

        # Setup mocks
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=mock_get_movie_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=TMDBCredits(id=0, cast=[], crew=[]))
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=TMDBKeywords(id=0, keywords=[]))
        mock_tmdb_client.get_poster_url = MagicMock(return_value="https://image.tmdb.org/t/p/w342/test.jpg")
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value="https://image.tmdb.org/t/p/w780/test_bg.jpg")
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/test_profile.jpg")

        # Similar endpoint responses
        mock_tmdb_client.get_movie_similar = AsyncMock(side_effect=[
            TMDBPaginatedResponse(page=1, results=similar_movies, total_pages=1, total_results=len(similar_movies)),  # For Baahubali 1
            TMDBPaginatedResponse(page=1, results=similar_baahubali2, total_pages=1, total_results=len(similar_baahubali2)),  # For Baahubali 2
        ])

        # Recommendations endpoint responses
        mock_tmdb_client.get_movie_recommendations = AsyncMock(side_effect=[
            TMDBPaginatedResponse(page=1, results=rec_movies, total_pages=1, total_results=len(rec_movies)),  # For Baahubali 1
            TMDBPaginatedResponse(page=1, results=[], total_pages=1, total_results=0),  # For Baahubali 2
        ])

        # Discover by genre (Action=28, Adventure=12, Fantasy=14)
        mock_tmdb_client.discover_movies = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))

        # Search multi for keywords
        mock_tmdb_client.search_multi = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))

        # Discover by language
        mock_tmdb_client.discover_movies = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))

        # --- Make the request ---
        response = await async_client.post(
            "/api/recommend/from-favorites",
            json=[
                {"media_type": "movie", "item_id": 264644},  # Baahubali: The Beginning
                {"media_type": "movie", "item_id": 340949},  # Baahubali 2: The Conclusion
            ],
            params={"limit": 10, "algorithm": "hybrid"}
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Recommendations: {data.get('recommendations', [])}")
        print(f"Algorithm used: {data.get('algorithm_used')}")
        print(f"Total candidates considered: {data.get('total_candidates_considered')}")
        print(f"Total excluded: {data.get('total_excluded')}")

        # Verify we get recommendations
        recommendations = data.get('recommendations', [])
        assert len(recommendations) > 0, f"Expected recommendations, got empty list. Full response: {data}"

        # Verify recommendations don't include the favorites
        favorite_ids = {264644, 340949}
        for rec in recommendations:
            assert rec['media']['id'] not in favorite_ids, f"Favorite {rec['media']['id']} should not be in recommendations"

        # Verify expected similar movies are in results
        rec_ids = {rec['media']['id'] for rec in recommendations}
        # Should include Baahubali 2 (if only Baahubali 1 was favorite) or RRR, Magadheera, Eega
        assert len(rec_ids) > 0

    @pytest.mark.asyncio
    async def test_single_baahubali_favorite(self, async_client, mock_tmdb_client):
        """Test with only Baahubali: The Beginning as favorite."""
        mock_tmdb_client.is_configured = True

        # Favorite resolution for Baahubali 1
        baahubali1_details = TMDBMovieDetails(
            id=264644, title="Baahubali: The Beginning", original_title="Baahubali: The Beginning",
            overview="The young Shivudu discovers his royal heritage.", release_date="2015-07-10",
            poster_path="/baahubali1.jpg", backdrop_path="/baahubali1_bg.jpg",
            vote_average=8.0, vote_count=5000, popularity=150.0, original_language="te",
            genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=14, name="Fantasy")],
            runtime=159, tagline="", homepage="",
            production_companies=[TMDBProductionCompany(id=1, name="Arka Media Works", logo_path="/arka.jpg", origin_country="IN")],
            production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
            spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
            status="Released", adult=False, video=False,
        )

        similar_movies = [
            TMDBMovie(
                id=340949, title="Baahubali 2: The Conclusion", original_title="Baahubali 2: The Conclusion",
                overview="The conclusion of the epic saga.", release_date="2017-04-28",
                poster_path="/baahubali2.jpg", backdrop_path="/baahubali2_bg.jpg",
                vote_average=8.2, vote_count=4000, popularity=200.0, original_language="te",
                genre_ids=[28, 12, 14], adult=False, video=False,
            ),
            TMDBMovie(
                id=441234, title="RRR", original_title="RRR",
                overview="A fictional story about two Indian revolutionaries.",
                release_date="2022-03-25", poster_path="/rrr.jpg", backdrop_path="/rrr_bg.jpg",
                vote_average=7.8, vote_count=3000, popularity=180.0, original_language="te",
                genre_ids=[28, 12, 18], adult=False, video=False,
            ),
        ]

        async def mock_get_movie_details(movie_id):
            if movie_id == 264644:
                return baahubali1_details
            elif movie_id == 340949:
                return TMDBMovieDetails(
                    id=340949, title="Baahubali 2: The Conclusion", original_title="Baahubali 2: The Conclusion",
                    overview="The conclusion of the epic saga.", release_date="2017-04-28",
                    poster_path="/baahubali2.jpg", backdrop_path="/baahubali2_bg.jpg",
                    vote_average=8.2, vote_count=4000, popularity=200.0, original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=14, name="Fantasy")],
                    runtime=171, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=1, name="Arka Media Works", logo_path="/arka.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
            elif movie_id == 441234:
                return TMDBMovieDetails(
                    id=441234, title="RRR", original_title="RRR",
                    overview="A fictional story about two Indian revolutionaries.",
                    release_date="2022-03-25", poster_path="/rrr.jpg", backdrop_path="/rrr_bg.jpg",
                    vote_average=7.8, vote_count=3000, popularity=180.0, original_language="te",
                    genres=[TMDBGenre(id=28, name="Action"), TMDBGenre(id=12, name="Adventure"), TMDBGenre(id=18, name="Drama")],
                    runtime=187, tagline="", homepage="",
                    production_companies=[TMDBProductionCompany(id=2, name="DVV Entertainment", logo_path="/dvv.jpg", origin_country="IN")],
                    production_countries=[TMDBProductionCountry(iso_3166_1="IN", name="India")],
                    spoken_languages=[TMDBSpokenLanguage(english_name="Telugu", iso_639_1="te", name="Telugu")],
                    status="Released", adult=False, video=False,
                )
            return None

        mock_tmdb_client.is_configured = True
        mock_tmdb_client.get_movie_details = AsyncMock(side_effect=mock_get_movie_details)
        mock_tmdb_client.get_movie_credits = AsyncMock(return_value=TMDBCredits(id=0, cast=[], crew=[]))
        mock_tmdb_client.get_movie_keywords = AsyncMock(return_value=TMDBKeywords(id=0, keywords=[]))
        mock_tmdb_client.get_poster_url = MagicMock(return_value="https://image.tmdb.org/t/p/w342/test.jpg")
        mock_tmdb_client.get_backdrop_url = MagicMock(return_value="https://image.tmdb.org/t/p/w780/test_bg.jpg")
        mock_tmdb_client.get_profile_url = MagicMock(return_value="https://image.tmdb.org/t/p/w185/test_profile.jpg")

        mock_tmdb_client.get_movie_similar = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=similar_movies, total_pages=1, total_results=len(similar_movies)
        ))
        mock_tmdb_client.get_movie_recommendations = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))
        mock_tmdb_client.discover_movies = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))
        mock_tmdb_client.search_multi = AsyncMock(return_value=TMDBPaginatedResponse(
            page=1, results=[], total_pages=1, total_results=0
        ))

        response = await async_client.post(
            "/api/recommend/from-favorites",
            json=[{"media_type": "movie", "item_id": 264644}],
            params={"limit": 10, "algorithm": "hybrid"}
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200
        data = response.json()
        print(f"Recommendations: {data.get('recommendations', [])}")

        recommendations = data.get('recommendations', [])
        assert len(recommendations) > 0, f"Expected recommendations, got empty. Full response: {data}"

        # Should not include the favorite
        for rec in recommendations:
            assert rec['media']['id'] != 264644


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])