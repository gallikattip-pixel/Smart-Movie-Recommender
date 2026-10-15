"""Favorites API routes for resolving favorite titles."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Set, Tuple, Optional

from app.schemas import (
    FavoritesResolveRequest,
    FavoritesResolveResponse,
    MediaDetailsResponse,
    FavoriteTitleRequest,
    ErrorResponse,
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
    TMDBMovieDetails,
    TMDBTVSeriesDetails,
    TMDBCredits,
    TMDBKeywords,
    TMDBGenre,
    TMDBProductionCompany,
    TMDBProductionCountry,
    TMDBSpokenLanguage,
    TMDBCastMember,
    TMDBCrewMember,
    TMDBKeyword,
)

router = APIRouter(prefix="/favorites", tags=["favorites"])

# Maximum number of favorites that can be resolved in one request
MAX_FAVORITES_PER_REQUEST = 50


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
            detail="Internal server error.",
            headers={"X-Error-Code": "FAVORITES_ERROR"},
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


async def _resolve_single_title(
    client,
    request: FavoriteTitleRequest,
) -> Tuple[Optional[MediaDetailsResponse], Optional[Dict[str, Any]]]:
    """
    Resolve a single favorite title.

    Returns (resolved_details, error_info).
    If successful, error_info is None.
    If failed, resolved_details is None and error_info contains error details.
    """
    media_type = request.media_type
    item_id = request.item_id

    try:
        if media_type == "movie":
            import asyncio
            details_task = client.get_movie_details(item_id)
            credits_task = client.get_movie_credits(item_id)
            keywords_task = client.get_movie_keywords(item_id)

            details, credits, keywords = await asyncio.gather(
                details_task, credits_task, keywords_task
            )

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

            resolved = MediaDetailsResponse(
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
            return (resolved, None)

        else:  # tv
            import asyncio
            details_task = client.get_tv_details(item_id)
            credits_task = client.get_tv_credits(item_id)
            keywords_task = client.get_tv_keywords(item_id)

            details, credits, keywords = await asyncio.gather(
                details_task, credits_task, keywords_task
            )

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

            resolved = MediaDetailsResponse(
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
            return (resolved, None)

    except (TMDBConfigError, TMDBAuthError, TMDBRateLimitError, TMDBUpstreamError,
            TMDBTimeoutError, TMDBNetworkError, TMDBNotFoundError) as e:
        # Convert error to dict for response
        error_info = {
            "media_type": media_type,
            "item_id": item_id,
            "error": str(e),
            "code": getattr(e, "code", "UNKNOWN_ERROR"),
            "status_code": getattr(e, "status_code", 500),
        }
        return (None, error_info)


@router.post(
    "/resolve",
    response_model=FavoritesResolveResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "TMDB authentication failed"},
        429: {"model": ErrorResponse, "description": "TMDB rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "TMDB service error"},
        503: {"model": ErrorResponse, "description": "TMDB not configured or network error"},
        504: {"model": ErrorResponse, "description": "TMDB request timeout"},
    },
)
async def resolve_favorites(
    request: FavoritesResolveRequest,
) -> FavoritesResolveResponse:
    """
    Resolve multiple favorite titles to their full TMDB metadata.

    Accepts a list of {media_type, item_id} pairs and returns detailed
    metadata for each. Handles partial failures gracefully.

    - Validates input and limits to 50 titles per request
    - Removes duplicates while preserving order
    - Returns resolved titles and failed titles separately
    """
    # Validate request
    if not request.titles:
        raise HTTPException(
            status_code=400,
            detail="At least one favorite title is required",
            headers={"X-Error-Code": "EMPTY_FAVORITES"},
        )

    if len(request.titles) > MAX_FAVORITES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many favorites. Maximum is {MAX_FAVORITES_PER_REQUEST} per request",
            headers={"X-Error-Code": "TOO_MANY_FAVORITES"},
        )

    # Deduplicate while preserving order (first occurrence wins)
    seen: Set[Tuple[str, int]] = set()
    unique_titles: List[FavoriteTitleRequest] = []
    for title in request.titles:
        key = (title.media_type, title.item_id)
        if key not in seen:
            seen.add(key)
            unique_titles.append(title)

    client = get_tmdb_client()

    # Resolve all titles
    import asyncio
    resolved_list: List[MediaDetailsResponse] = []
    failed_list: List[Dict[str, Any]] = []

    # Process in batches to avoid overwhelming the API
    # Process 5 at a time
    batch_size = 5
    for i in range(0, len(unique_titles), batch_size):
        batch = unique_titles[i:i + batch_size]
        tasks = [_resolve_single_title(client, title) for title in batch]
        results = await asyncio.gather(*tasks)

        for resolved, error in results:
            if resolved:
                resolved_list.append(resolved)
            else:
                failed_list.append(error)

    return FavoritesResolveResponse(
        resolved=resolved_list,
        failed=failed_list,
    )