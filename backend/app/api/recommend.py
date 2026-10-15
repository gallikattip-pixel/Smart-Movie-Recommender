"""Recommendation API routes with full implementation."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import time
import asyncio

from app.schemas import (
    RecommendRequest,
    RecommendResponse,
    RecommendationItem,
    ErrorResponse,
    MediaDetailsResponse,
    UserPreference,
    FavoriteTitleRequest,
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
    TMDBClient,
)
from app.recommender import (
    validate_preferences,
    build_profile_from_favorites,
    merge_preferences,
    apply_hard_exclusions,
    build_graph_from_favorites_and_candidates,
    bfs,
    dfs,
    ucs,
    greedy_best_first,
    astar,
    hybrid_search,
    rank_candidates,
    get_all_candidates,
    filter_candidates_by_preferences,
    SearchConfig,
)
from app.recommender.profile import build_profile_from_favorites
from app.recommender.ranking import compute_preference_score

router = APIRouter(prefix="/recommend", tags=["recommend"])


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
            detail="Internal server error during recommendation generation.",
            headers={"X-Error-Code": "RECOMMEND_ERROR"},
        )


async def _resolve_favorites_async(
    client: TMDBClient,
    favorites: List[FavoriteTitleRequest],
) -> List[MediaDetailsResponse]:
    """
    Resolve favorite titles asynchronously using asyncio.gather for parallelism.
    """
    async def resolve_one(fav: FavoriteTitleRequest):
        try:
            if fav.media_type == "movie":
                details_task = client.get_movie_details(fav.item_id)
                credits_task = client.get_movie_credits(fav.item_id)
                keywords_task = client.get_movie_keywords(fav.item_id)
            else:
                details_task = client.get_tv_details(fav.item_id)
                credits_task = client.get_tv_credits(fav.item_id)
                keywords_task = client.get_tv_keywords(fav.item_id)

            details, credits, keywords = await asyncio.gather(
                details_task, credits_task, keywords_task
            )

            # Build MediaDetailsResponse
            from app.recommender.profile import (
                _normalize_genres,
                _normalize_production_companies,
                _normalize_production_countries,
                _normalize_spoken_languages,
                _normalize_cast,
                _normalize_crew,
                _normalize_keywords,
                _extract_directors,
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

            if fav.media_type == "movie":
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
            else:
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
                TMDBTimeoutError, TMDBNetworkError, TMDBNotFoundError):
            return None

    tasks = [resolve_one(fav) for fav in favorites]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    resolved = []
    for result in results:
        if isinstance(result, MediaDetailsResponse):
            resolved.append(result)

    return resolved


def _build_preference_heuristic(prefs):
    """Build a heuristic function for A*/Greedy search based on preferences."""
    # Convert preference lists to sets for efficient intersection
    preferred_genres_set = set(prefs.preferred_genres) if prefs.preferred_genres else set()
    preferred_languages_set = set(prefs.preferred_languages) if prefs.preferred_languages else set()
    preferred_countries_set = set(prefs.preferred_countries) if prefs.preferred_countries else set()

    def heuristic(node):
        score = 0.0

        # Genre match
        if preferred_genres_set:
            node_genres = node.genres
            matches = len(preferred_genres_set & node_genres)
            score += matches * 2.0

        # Language match
        if preferred_languages_set and node.original_language in preferred_languages_set:
            score += 1.0

        # Country match
        if preferred_countries_set:
            node_countries = node.production_countries
            matches = len(preferred_countries_set & node_countries)
            score += matches * 1.0

        # Rating
        if prefs.min_vote_average and node.vote_average:
            if node.vote_average >= prefs.min_vote_average:
                score += (node.vote_average - prefs.min_vote_average) * 0.5

        # Hidden gems
        if prefs.prefer_hidden_gems:
            score += max(0, (50 - node.popularity) / 50.0)

        # Heuristic should be admissible (never overestimate true cost)
        # We negate for min-heap behavior: lower f = better
        return -min(score, 10.0)

    return heuristic


def _run_search_algorithm(
    algorithm: str,
    graph,
    start_nodes: List[int],
    candidate_ids: set,
    heuristic,
    config,
) -> tuple:
    """
    Run the specified search algorithm and return (search_result, algorithm_name).
    """
    if algorithm == "bfs":
        result = bfs(graph, start_nodes, config)
        return result, "bfs"
    elif algorithm == "dfs":
        result = dfs(graph, start_nodes, config)
        return result, "dfs"
    elif algorithm == "ucs":
        result = ucs(graph, start_nodes, config)
        return result, "ucs"
    elif algorithm == "greedy":
        result = greedy_best_first(graph, start_nodes, heuristic, config)
        return result, "greedy"
    elif algorithm == "astar":
        result = astar(graph, start_nodes, heuristic, config)
        return result, "astar"
    else:  # hybrid (default)
        result = hybrid_search(graph, start_nodes, candidate_ids, heuristic, config)
        return result, "hybrid"


@router.post(
    "",
    response_model=RecommendResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "TMDB authentication failed"},
        429: {"model": ErrorResponse, "description": "TMDB rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "TMDB service error"},
        503: {"model": ErrorResponse, "description": "TMDB not configured or network error"},
        504: {"model": ErrorResponse, "description": "TMDB request timeout"},
    },
)
async def get_recommendations(
    request: RecommendRequest,
) -> RecommendResponse:
    """
    Generate personalized movie/TV recommendations.

    Pipeline:
    1. Validate user preferences
    2. Resolve favorite titles to full metadata
    3. Build preference profile (explicit + inferred from favorites)
    4. Discover candidate titles from TMDB
    5. Apply hard exclusions
    6. Build metadata relationship graph
    7. Search graph using specified algorithm
    8. Rank candidates with TF-IDF + preference scoring
    9. Return top recommendations with explanations
    """
    start_time = time.time()

    # Validate preferences
    warnings = validate_preferences(request.preferences)

    client = get_tmdb_client()

    # Check TMDB configuration
    if not client.is_configured:
        raise _handle_tmdb_error(TMDBConfigError())

    # Step 1: Resolve favorite titles
    favorites = []
    if request.preferences.favorite_titles:
        try:
            favorites = await _resolve_favorites_async(client, request.preferences.favorite_titles)
        except (TMDBConfigError, TMDBAuthError, TMDBRateLimitError, TMDBUpstreamError,
                TMDBTimeoutError, TMDBNetworkError, TMDBNotFoundError) as e:
            raise _handle_tmdb_error(e)

    # Step 2: Build preference profile (explicit + inferred + natural language intent)
    inferred_prefs = build_profile_from_favorites(favorites)
    merged_prefs = merge_preferences(request.preferences, inferred_prefs)

    # Extract natural language intent if query is present
    if hasattr(merged_prefs, "query") and merged_prefs.query:
        from app.recommender.intent import parse_query_intent
        intent = parse_query_intent(merged_prefs.query)
        if intent.is_recommendation or intent.intent_type != "exact_title":
            if intent.genre_ids:
                merged_prefs.preferred_genres = list(dict.fromkeys(merged_prefs.preferred_genres + intent.genre_ids))
            if intent.excluded_genre_ids:
                merged_prefs.excluded_genres = list(dict.fromkeys(merged_prefs.excluded_genres + intent.excluded_genre_ids))
            if intent.languages and not merged_prefs.preferred_languages:
                merged_prefs.preferred_languages = intent.languages
            if intent.countries and not merged_prefs.preferred_countries:
                merged_prefs.preferred_countries = intent.countries
            if intent.themes:
                merged_prefs.preferred_themes = list(dict.fromkeys(merged_prefs.preferred_themes + intent.themes))
            if intent.excluded_themes:
                merged_prefs.excluded_themes = list(dict.fromkeys(merged_prefs.excluded_themes + intent.excluded_themes))
            if intent.moods:
                merged_prefs.preferred_moods = list(dict.fromkeys(merged_prefs.preferred_moods + intent.moods))
            if intent.pacing:
                merged_prefs.preferred_pacing = list(dict.fromkeys(merged_prefs.preferred_pacing + intent.pacing))
            if intent.endings:
                merged_prefs.preferred_endings = list(dict.fromkeys(merged_prefs.preferred_endings + intent.endings))
            if intent.era and not merged_prefs.era:
                merged_prefs.era = intent.era
            if intent.min_rating and not merged_prefs.min_vote_average:
                merged_prefs.min_vote_average = intent.min_rating
            if intent.prefer_hidden_gems:
                merged_prefs.prefer_hidden_gems = True

    # Step 3: Discover candidates
    try:
        candidates = await get_all_candidates(
            client=client,
            favorites=favorites,
            prefs=merged_prefs,
            max_total=200,
        )
    except (TMDBConfigError, TMDBAuthError, TMDBRateLimitError, TMDBUpstreamError,
            TMDBTimeoutError, TMDBNetworkError, TMDBNotFoundError) as e:
        raise _handle_tmdb_error(e)

    # Step 4: Apply hard exclusions
    candidates = filter_candidates_by_preferences(candidates, merged_prefs)

    if not candidates:
        return RecommendResponse(
            recommendations=[],
            algorithm_used=request.algorithm,
            total_candidates_considered=0,
            total_excluded=0,
            search_time_ms=round((time.time() - start_time) * 1000, 2),
        )

    # Step 5: Build metadata graph
    graph = build_graph_from_favorites_and_candidates(favorites, candidates)

    # Step 6: Search graph using specified algorithm
    favorite_ids = {f.id for f in favorites}
    candidate_ids = {c.id for c in candidates}

    search_config = SearchConfig(
        max_depth=3,
        max_nodes=100,
        max_cost=10.0,
        target_nodes=candidate_ids,
    )

    heuristic = _build_preference_heuristic(merged_prefs)

    # Start from favorites if present, otherwise top candidates as seeds
    start_nodes = list(favorite_ids) if favorite_ids else [c.id for c in candidates[:3]]

    # Run the specified search algorithm
    search_result, algorithm_used = _run_search_algorithm(
        request.algorithm,
        graph,
        start_nodes,
        candidate_ids,
        heuristic,
        search_config,
    )

    # Step 7: Filter candidates to those discovered by search
    discovered_ids = set(search_result.visited)
    final_candidates = [c for c in candidates if c.id in discovered_ids]
    if len(final_candidates) < min(len(candidates), request.limit):
        seen = {c.id for c in final_candidates}
        for c in candidates:
            if c.id not in seen:
                final_candidates.append(c)
                seen.add(c.id)
                if len(final_candidates) >= request.limit:
                    break
    if not final_candidates:
        final_candidates = candidates

    # Step 8: Rank candidates
    ranked = rank_candidates(
        candidates=final_candidates,
        prefs=merged_prefs,
        graph=graph,
        favorite_ids=favorite_ids,
    )

    # Limit results
    recommendations = ranked[:request.limit]

    # Add graph path info to recommendations
    for rec in recommendations:
        if rec.graph_path is None and rec.media.id in search_result.paths:
            # Find path from any favorite
            for fav_id in favorite_ids:
                if fav_id in search_result.paths and rec.media.id in search_result.paths:
                    rec.graph_path = search_result.paths[rec.media.id]

    search_time_ms = round((time.time() - start_time) * 1000, 2)

    return RecommendResponse(
        recommendations=recommendations,
        algorithm_used=algorithm_used,
        total_candidates_considered=len(candidates),
        total_excluded=len(candidates) - len(final_candidates),
        search_time_ms=search_time_ms,
    )


@router.post(
    "/from-favorites",
    response_model=RecommendResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def get_recommendations_from_favorites(
    favorites: List[FavoriteTitleRequest],
    limit: int = Query(20, ge=1, le=50),
    algorithm: str = Query("hybrid", pattern="^(bfs|dfs|ucs|greedy|astar|hybrid)$"),
) -> RecommendResponse:
    """
    Simplified recommendation endpoint using only favorite titles.

    Accepts a list of favorite TMDB IDs and returns recommendations.
    Preferences are inferred entirely from the favorites.
    """
    if not favorites:
        raise HTTPException(
            status_code=400,
            detail="At least one favorite title is required",
            headers={"X-Error-Code": "NO_FAVORITES"},
        )

    # Build minimal request and delegate to main endpoint
    request = RecommendRequest(
        preferences=UserPreference(favorite_titles=favorites),
        limit=limit,
        algorithm=algorithm,
    )

    return await get_recommendations(request)