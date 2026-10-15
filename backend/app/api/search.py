"""Search API routes with TMDB integration."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from app.schemas import (
    SearchResponse,
    SearchResultItem,
    ErrorResponse,
    MediaDetailsResponse,
    GenreItem,
    ProductionCompanyItem,
    ProductionCountryItem,
    SpokenLanguageItem,
    CastMemberItem,
    CrewMemberItem,
    KeywordItem,
)
from app.tmdb import (
    get_tmdb_client,
    TMDBConfigError,
    TMDBAuthError,
    TMDBRateLimitError,
    TMDBUpstreamError,
    TMDBTimeoutError,
    TMDBNetworkError,
    TMDBNotFoundError,
    TMDBMultiSearchResult,
    TMDBMovie,
    TMDBTVSeries,
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

router = APIRouter(prefix="/search", tags=["search"])


def _normalize_result(item, client) -> Optional[SearchResultItem]:
    """
    Normalize TMDB search result to our response schema.

    Excludes person results and handles missing fields honestly.
    Handles TMDBMultiSearchResult, TMDBMovie, and TMDBTVSeries.
    """
    # Determine media type
    media_type = getattr(item, "media_type", None)
    
    # Skip person results
    if media_type == "person":
        return None

    # Determine title and release date based on media type
    if isinstance(item, TMDBMovie) or media_type == "movie":
        title = item.title or item.original_title or "Unknown Title"
        release_date = item.release_date
        first_air_date = None
        final_media_type = "movie"
    elif isinstance(item, TMDBTVSeries) or media_type == "tv":
        title = item.name or item.original_name or "Unknown Title"
        release_date = None
        first_air_date = item.first_air_date
        final_media_type = "tv"
    else:
        return None

    # Build poster URL if path exists
    poster_url = None
    if item.poster_path:
        poster_url = client.get_poster_url(item.poster_path)

    return SearchResultItem(
        id=item.id,
        title=title,
        media_type=final_media_type,  # type: ignore
        release_date=release_date,
        first_air_date=first_air_date,
        overview=item.overview,
        poster_path=item.poster_path,
        poster_url=poster_url,
        vote_average=item.vote_average,
        vote_count=item.vote_count or 0,
        popularity=item.popularity or 0.0,
        original_language=item.original_language,
        genre_ids=item.genre_ids or [],
    )


def _handle_tmdb_error(e: Exception) -> HTTPException:
    """Convert TMDB exceptions to appropriate HTTP exceptions."""
    if isinstance(e, TMDBConfigError):
        return HTTPException(
            status_code=503,
            detail=e.args[0] if e.args else "TMDB not configured",
            headers={"X-Error-Code": e.code},
        )
    elif isinstance(e, TMDBAuthError):
        return HTTPException(
            status_code=401,
            detail="TMDB authentication failed. Check API token.",
            headers={"X-Error-Code": e.code},
        )
    elif isinstance(e, TMDBRateLimitError):
        return HTTPException(
            status_code=429,
            detail="TMDB rate limit exceeded. Please try again later.",
            headers={
                "X-Error-Code": e.code,
                "Retry-After": str(e.retry_after or 60),
            },
        )
    elif isinstance(e, TMDBNotFoundError):
        return HTTPException(
            status_code=404,
            detail="Media not found.",
            headers={"X-Error-Code": e.code},
        )
    elif isinstance(e, TMDBUpstreamError):
        return HTTPException(
            status_code=502,
            detail="TMDB service temporarily unavailable.",
            headers={"X-Error-Code": e.code},
        )
    elif isinstance(e, TMDBTimeoutError):
        return HTTPException(
            status_code=504,
            detail="TMDB request timed out. Please try again.",
            headers={"X-Error-Code": e.code},
        )
    elif isinstance(e, TMDBNetworkError):
        return HTTPException(
            status_code=503,
            detail="Unable to connect to TMDB. Please check network.",
            headers={"X-Error-Code": e.code},
        )
    else:
        return HTTPException(
            status_code=500,
            detail="Internal server error during search.",
            headers={"X-Error-Code": "SEARCH_ERROR"},
        )


def _normalize_genres(genres: List[TMDBGenre]) -> List[GenreItem]:
    """Normalize TMDB genres to our schema."""
    return [GenreItem(id=g.id, name=g.name) for g in genres]


def _normalize_production_companies(
    companies: List[TMDBProductionCompany], client
) -> List[ProductionCompanyItem]:
    """Normalize TMDB production companies to our schema."""
    result = []
    for c in companies:
        logo_url = None
        if c.logo_path:
            logo_url = client.get_profile_url(c.logo_path)
        result.append(
            ProductionCompanyItem(
                id=c.id,
                name=c.name,
                logo_path=c.logo_path,
                logo_url=logo_url,
                origin_country=c.origin_country,
            )
        )
    return result


def _normalize_production_countries(
    countries: List[TMDBProductionCountry]
) -> List[ProductionCountryItem]:
    """Normalize TMDB production countries to our schema."""
    return [
        ProductionCountryItem(iso_3166_1=c.iso_3166_1, name=c.name)
        for c in countries
    ]


def _normalize_spoken_languages(
    languages: List[TMDBSpokenLanguage]
) -> List[SpokenLanguageItem]:
    """Normalize TMDB spoken languages to our schema."""
    return [
        SpokenLanguageItem(
            english_name=l.english_name,
            iso_639_1=l.iso_639_1,
            name=l.name,
        )
        for l in languages
    ]


def _normalize_cast(cast: List[TMDBCastMember], client) -> List[CastMemberItem]:
    """Normalize TMDB cast to our schema."""
    result = []
    for c in cast:
        profile_url = None
        if c.profile_path:
            profile_url = client.get_profile_url(c.profile_path)
        result.append(
            CastMemberItem(
                id=c.id,
                name=c.name,
                character=c.character,
                profile_path=c.profile_path,
                profile_url=profile_url,
                order=c.order,
                known_for_department=c.known_for_department,
            )
        )
    return result


def _normalize_crew(crew: List[TMDBCrewMember], client) -> List[CrewMemberItem]:
    """Normalize TMDB crew to our schema."""
    result = []
    for c in crew:
        profile_url = None
        if c.profile_path:
            profile_url = client.get_profile_url(c.profile_path)
        result.append(
            CrewMemberItem(
                id=c.id,
                name=c.name,
                job=c.job,
                department=c.department,
                profile_path=c.profile_path,
                profile_url=profile_url,
            )
        )
    return result


def _normalize_keywords(keywords: List[TMDBKeyword]) -> List[KeywordItem]:
    """Normalize TMDB keywords to our schema."""
    return [KeywordItem(id=k.id, name=k.name) for k in keywords]


def _extract_directors(crew: List[CrewMemberItem]) -> List[CrewMemberItem]:
    """Extract directors from crew."""
    return [c for c in crew if c.job == "Director" and c.department == "Directing"]


@router.get(
    "",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid search parameters"},
        401: {"model": ErrorResponse, "description": "TMDB authentication failed"},
        429: {"model": ErrorResponse, "description": "TMDB rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "TMDB service error"},
        503: {"model": ErrorResponse, "description": "TMDB not configured or network error"},
        504: {"model": ErrorResponse, "description": "TMDB request timeout"},
    },
)
async def search_media(
    query: str = Query(..., min_length=1, max_length=200, description="Search query"),
    type: str = Query("multi", pattern="^(multi|movie|tv)$", description="Search type"),
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    include_adult: bool = Query(False, description="Include adult content"),
    language: str = Query("en-US", pattern="^[a-z]{2}-[A-Z]{2}$", description="Language code"),
) -> SearchResponse:
    """
    Search for movies and TV series using TMDB.

    - **multi**: Search movies, TV series, and people (people excluded from results)
    - **movie**: Search movies only
    - **tv**: Search TV series only

    Returns normalized results with poster URLs when available.
    """
    # Validate query is not just whitespace
    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty or whitespace only",
            headers={"X-Error-Code": "INVALID_QUERY"},
        )

    client = get_tmdb_client()
    if not client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="TMDB API credentials not configured. Set TMDB_ACCESS_TOKEN in environment.",
            headers={"X-Error-Code": "TMDB_NOT_CONFIGURED"},
        )

    from app.recommender.intent import parse_query_intent
    intent = parse_query_intent(query)

    # For similar-title queries, search TMDB using the extracted seed title
    effective_query = intent.clean_title if (intent.intent_type == "similar_title" and intent.clean_title) else query.strip()
    effective_type = intent.media_type if (type == "multi" and intent.media_type in ("movie", "tv")) else type

    try:
        if effective_type == "multi":
            response = await client.search_multi(
                query=effective_query,
                page=page,
                include_adult=include_adult,
                language=language,
            )
        elif effective_type == "movie":
            response = await client.search_movies(
                query=effective_query,
                page=page,
                include_adult=include_adult,
                language=language,
            )
        elif effective_type == "tv":
            response = await client.search_tv(
                query=effective_query,
                page=page,
                include_adult=include_adult,
                language=language,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid search type. Must be 'multi', 'movie', or 'tv'",
                headers={"X-Error-Code": "INVALID_TYPE"},
            )

    except (TMDBConfigError, TMDBAuthError, TMDBRateLimitError, TMDBUpstreamError,
            TMDBTimeoutError, TMDBNetworkError) as e:
        raise _handle_tmdb_error(e)

    except Exception as e:
        # Diagnostic: log exception type and message for debugging
        import traceback
        print("SEARCH ENDPOINT EXCEPTION: {}: {}".format(type(e).__name__, str(e)[:500]))
        traceback.print_exc()
        raise

    # Normalize results, excluding person results
    normalized_results = []
    for item in response.results:
        normalized = _normalize_result(item, client)
        if normalized:
            normalized_results.append(normalized)

    return SearchResponse(
        results=normalized_results,
        page=response.page,
        total_pages=response.total_pages,
        total_results=response.total_results,
        query=query.strip(),
        search_type=type,
        intent=intent.model_dump(),
    )


@router.get(
    "/{media_type}/{item_id}",
    response_model=MediaDetailsResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Media not found"},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def get_media_details(
    media_type: str,
    item_id: int,
) -> MediaDetailsResponse:
    """
    Get detailed information for a specific movie or TV series.

    Includes genres, production companies, countries, languages,
    cast, crew (including directors), and keywords.
    """
    if media_type not in ("movie", "tv"):
        raise HTTPException(
            status_code=400,
            detail="media_type must be 'movie' or 'tv'",
            headers={"X-Error-Code": "INVALID_MEDIA_TYPE"},
        )

    client = get_tmdb_client()
    if not client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="TMDB API credentials not configured. Set TMDB_ACCESS_TOKEN in environment.",
            headers={"X-Error-Code": "TMDB_NOT_CONFIGURED"},
        )

    try:
        if media_type == "movie":
            # Fetch movie details, credits, and keywords in parallel
            import asyncio
            details_task = client.get_movie_details(item_id)
            credits_task = client.get_movie_credits(item_id)
            keywords_task = client.get_movie_keywords(item_id)

            details, credits, keywords = await asyncio.gather(
                details_task, credits_task, keywords_task
            )

            # Normalize all data
            genres = _normalize_genres(details.genres)
            production_companies = _normalize_production_companies(details.production_companies, client)
            production_countries = _normalize_production_countries(details.production_countries)
            spoken_languages = _normalize_spoken_languages(details.spoken_languages)
            cast = _normalize_cast(credits.cast, client)
            crew = _normalize_crew(credits.crew, client)
            directors = _extract_directors(crew)
            keywords_list = _normalize_keywords(keywords.keywords)

            poster_url = None
            if details.poster_path:
                poster_url = client.get_poster_url(details.poster_path)

            backdrop_url = None
            if details.backdrop_path:
                backdrop_url = client.get_backdrop_url(details.backdrop_path)

            return MediaDetailsResponse(
                id=details.id,
                title=details.title,
                media_type="movie",
                release_date=details.release_date,
                first_air_date=None,
                overview=details.overview,
                poster_path=details.poster_path,
                poster_url=poster_url,
                backdrop_path=details.backdrop_path,
                backdrop_url=backdrop_url,
                vote_average=details.vote_average,
                vote_count=details.vote_count,
                popularity=details.popularity,
                original_language=details.original_language,
                genres=genres,
                runtime=details.runtime,
                episode_run_time=[],
                number_of_seasons=None,
                number_of_episodes=None,
                status=details.status,
                tagline=details.tagline,
                homepage=details.homepage,
                production_companies=production_companies,
                production_countries=production_countries,
                spoken_languages=spoken_languages,
                cast=cast,
                crew=crew,
                keywords=keywords_list,
                directors=directors,
            )

        else:  # tv
            # Fetch TV details, credits, and keywords in parallel
            import asyncio
            details_task = client.get_tv_details(item_id)
            credits_task = client.get_tv_credits(item_id)
            keywords_task = client.get_tv_keywords(item_id)

            details, credits, keywords = await asyncio.gather(
                details_task, credits_task, keywords_task
            )

            # Normalize all data
            genres = _normalize_genres(details.genres)
            production_companies = _normalize_production_companies(details.production_companies, client)
            production_countries = _normalize_production_countries(details.production_countries)
            spoken_languages = _normalize_spoken_languages(details.spoken_languages)
            cast = _normalize_cast(credits.cast, client)
            crew = _normalize_crew(credits.crew, client)
            directors = _extract_directors(crew)
            keywords_list = _normalize_keywords(keywords.keywords)

            poster_url = None
            if details.poster_path:
                poster_url = client.get_poster_url(details.poster_path)

            backdrop_url = None
            if details.backdrop_path:
                backdrop_url = client.get_backdrop_url(details.backdrop_path)

            return MediaDetailsResponse(
                id=details.id,
                title=details.name,
                media_type="tv",
                release_date=None,
                first_air_date=details.first_air_date,
                overview=details.overview,
                poster_path=details.poster_path,
                poster_url=poster_url,
                backdrop_path=details.backdrop_path,
                backdrop_url=backdrop_url,
                vote_average=details.vote_average,
                vote_count=details.vote_count,
                popularity=details.popularity,
                original_language=details.original_language,
                genres=genres,
                runtime=None,
                episode_run_time=details.episode_run_time,
                number_of_seasons=details.number_of_seasons,
                number_of_episodes=details.number_of_episodes,
                status=details.status,
                tagline=details.tagline,
                homepage=details.homepage,
                production_companies=production_companies,
                production_countries=production_countries,
                spoken_languages=spoken_languages,
                cast=cast,
                crew=crew,
                keywords=keywords_list,
                directors=directors,
            )

    except (TMDBConfigError, TMDBAuthError, TMDBRateLimitError, TMDBUpstreamError,
            TMDBTimeoutError, TMDBNetworkError, TMDBNotFoundError) as e:
        raise _handle_tmdb_error(e)