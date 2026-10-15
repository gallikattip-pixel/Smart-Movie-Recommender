"""Candidate discovery for recommendations."""

import asyncio
from typing import List, Set, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.schemas import MediaDetailsResponse, UserPreference, FavoriteTitleRequest, GenreItem, ProductionCountryItem
from app.tmdb.client import get_tmdb_client, TMDBClient
from app.tmdb import TMDBConfigError, TMDBNotFoundError
from app.tmdb.models import TMDBPaginatedResponse, TMDBSimilarResult, TMDBDiscoverResult


# Maximum candidates to fetch from TMDB
MAX_CANDIDATES_PER_SOURCE = 40
MAX_TOTAL_CANDIDATES = 100


# Standard TMDB Movie and TV Genres mapping
TMDB_ALL_GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
    10759: "Action & Adventure",
    10762: "Kids",
    10763: "News",
    10764: "Reality",
    10765: "Sci-Fi & Fantasy",
    10766: "Soap",
    10767: "Talk",
    10768: "War & Politics",
}


@dataclass
class CandidateSource:
    """Source of candidate titles."""
    name: str
    media_type: str  # "movie" or "tv"
    candidates: List[MediaDetailsResponse]


def _build_candidate_from_tmdb_result(
    tmdb_result,
    client: TMDBClient,
    media_type: str,
) -> Optional[MediaDetailsResponse]:
    """Convert any TMDB result item directly to MediaDetailsResponse without extra API calls."""
    if tmdb_result is None:
        return None
    if isinstance(tmdb_result, MediaDetailsResponse):
        return tmdb_result

    try:
        item_id = getattr(tmdb_result, "id", None)
        if not item_id:
            return None

        # Determine title
        title = (
            getattr(tmdb_result, "title", None)
            or getattr(tmdb_result, "name", None)
            or getattr(tmdb_result, "original_title", None)
            or getattr(tmdb_result, "original_name", None)
            or "Untitled"
        )

        resolved_media_type = getattr(tmdb_result, "media_type", None) or media_type
        if resolved_media_type not in ("movie", "tv"):
            resolved_media_type = media_type if media_type in ("movie", "tv") else "movie"

        release_date = getattr(tmdb_result, "release_date", None)
        first_air_date = getattr(tmdb_result, "first_air_date", None)

        poster_path = getattr(tmdb_result, "poster_path", None)
        backdrop_path = getattr(tmdb_result, "backdrop_path", None)
        poster_url = client.get_poster_url(poster_path) if poster_path else None
        backdrop_url = client.get_backdrop_url(backdrop_path) if backdrop_path else None

        vote_average = getattr(tmdb_result, "vote_average", 0.0)
        vote_count = getattr(tmdb_result, "vote_count", 0) or 0
        popularity = getattr(tmdb_result, "popularity", 0.0) or 0.0
        original_language = getattr(tmdb_result, "original_language", "en") or "en"
        overview = getattr(tmdb_result, "overview", "") or ""

        # Normalize genres
        genres: List[GenreItem] = []
        if hasattr(tmdb_result, "genres") and tmdb_result.genres:
            for g in tmdb_result.genres:
                if isinstance(g, dict):
                    genres.append(GenreItem(id=g.get("id", 0), name=g.get("name", "Unknown")))
                elif hasattr(g, "id") and hasattr(g, "name"):
                    genres.append(GenreItem(id=g.id, name=g.name))
        elif hasattr(tmdb_result, "genre_ids") and tmdb_result.genre_ids:
            for gid in tmdb_result.genre_ids:
                genres.append(GenreItem(id=gid, name=TMDB_ALL_GENRES.get(gid, "Unknown")))

        countries: List[ProductionCountryItem] = []
        origin_countries = getattr(tmdb_result, "origin_country", []) or []
        for c in origin_countries:
            if c:
                countries.append(ProductionCountryItem(iso_3166_1=str(c), name=str(c)))

        return MediaDetailsResponse(
            id=item_id,
            title=title,
            media_type=resolved_media_type,
            release_date=release_date,
            first_air_date=first_air_date,
            overview=overview,
            poster_path=poster_path,
            poster_url=poster_url,
            backdrop_path=backdrop_path,
            backdrop_url=backdrop_url,
            vote_average=vote_average,
            vote_count=vote_count,
            popularity=popularity,
            original_language=original_language,
            genres=genres,
            runtime=getattr(tmdb_result, "runtime", None),
            episode_run_time=[],
            number_of_seasons=None,
            number_of_episodes=None,
            status="Released",
            tagline=getattr(tmdb_result, "tagline", None),
            homepage=getattr(tmdb_result, "homepage", None),
            production_companies=[],
            production_countries=countries,
            spoken_languages=[],
            cast=[],
            crew=[],
            keywords=[],
            directors=[],
        )
    except Exception:
        return None


async def _normalize_tmdb_result(
    tmdb_result,
    client,
    media_type: str,
):
    """Normalize TMDB similar/discover result to MediaDetailsResponse without redundant HTTP requests."""
    return _build_candidate_from_tmdb_result(tmdb_result, client, media_type)


async def discover_candidates_from_favorites(
    client: TMDBClient,
    favorites: List[MediaDetailsResponse],
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> List[MediaDetailsResponse]:
    """
    Discover candidates based on favorite titles using concurrent TMDB similar and recommendations calls.
    """
    candidates: Dict[int, MediaDetailsResponse] = {}

    async def _fetch_for_fav(fav):
        found = []
        try:
            sim_resp, rec_resp = await asyncio.gather(
                _get_similar(client, fav.media_type, fav.id, limit=10),
                _get_recommendations(client, fav.media_type, fav.id, limit=10),
                return_exceptions=True
            )
            if not isinstance(sim_resp, Exception) and hasattr(sim_resp, "results"):
                for c in sim_resp.results:
                    media = _build_candidate_from_tmdb_result(c, client, fav.media_type)
                    if media:
                        found.append(media)
            if not isinstance(rec_resp, Exception) and hasattr(rec_resp, "results"):
                for c in rec_resp.results:
                    media = _build_candidate_from_tmdb_result(c, client, fav.media_type)
                    if media:
                        found.append(media)
        except Exception:
            pass
        return found

    tasks = [_fetch_for_fav(fav) for fav in favorites[:4]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            for media in res:
                if media.id not in candidates:
                    candidates[media.id] = media

    return list(candidates.values())[:limit]


async def discover_candidates_by_genre(
    client: TMDBClient,
    genre_ids: List[int],
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> List[MediaDetailsResponse]:
    """Discover candidates by preferred genres using TMDB discover endpoint concurrently."""
    if not genre_ids:
        return []

    candidates: Dict[int, MediaDetailsResponse] = {}

    async def _fetch_genre_type(genre_id, media_type):
        try:
            results = await _discover_by_genre(client, media_type, genre_id, limit=15)
            return [
                _build_candidate_from_tmdb_result(c, client, media_type)
                for c in getattr(results, "results", [])
            ]
        except Exception:
            return []

    content_types = getattr(prefs, "content_types", ["movie", "tv"]) or ["movie", "tv"]
    tasks = [
        _fetch_genre_type(gid, mtype)
        for gid in genre_ids[:3]
        for mtype in content_types
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            for media in res:
                if media and media.id not in candidates:
                    candidates[media.id] = media

    return list(candidates.values())[:limit]


async def discover_candidates_by_keyword(
    client: TMDBClient,
    keywords: List[str],
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> List[MediaDetailsResponse]:
    """Discover candidates by keywords from favorites concurrently."""
    if not keywords:
        return []

    candidates: Dict[int, MediaDetailsResponse] = {}

    async def _fetch_keyword(kw, media_type):
        try:
            results = await _search_by_keyword(client, media_type, kw, limit=10)
            return [
                _build_candidate_from_tmdb_result(c, client, media_type)
                for c in getattr(results, "results", [])
                if getattr(c, "media_type", media_type) in ("movie", "tv")
            ]
        except Exception:
            return []

    content_types = getattr(prefs, "content_types", ["movie", "tv"]) or ["movie", "tv"]
    tasks = [
        _fetch_keyword(kw, mtype)
        for kw in keywords[:3]
        for mtype in content_types
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            for media in res:
                if media and media.id not in candidates:
                    candidates[media.id] = media

    return list(candidates.values())[:limit]


async def discover_candidates_by_cast_director(
    client: TMDBClient,
    favorites: List[MediaDetailsResponse],
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> List[MediaDetailsResponse]:
    """Discover candidates by favorite cast and directors."""
    candidates: Dict[int, MediaDetailsResponse] = {}
    content_types = getattr(prefs, "content_types", ["movie", "tv"]) or ["movie", "tv"]

    cast_names = _get_top_cast(favorites, 3)
    director_names = _get_directors(favorites, 2)
    names = cast_names + director_names

    async def _fetch_person(name):
        found = []
        try:
            results = await client.search_multi(name, page=1)
            for item in getattr(results, "results", []):
                item_media_type = getattr(item, "media_type", None)
                if item_media_type in ("movie", "tv") and item_media_type in content_types:
                    cand = _build_candidate_from_tmdb_result(item, client, item_media_type)
                    if cand:
                        found.append(cand)
        except Exception:
            pass
        return found

    tasks = [_fetch_person(name) for name in names[:4]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            for media in res:
                if media and media.id not in candidates:
                    candidates[media.id] = media

    return list(candidates.values())[:limit]


async def discover_candidates_by_language_country(
    client: TMDBClient,
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> List[MediaDetailsResponse]:
    """Discover candidates by preferred language using TMDB discover."""
    languages = getattr(prefs, "preferred_languages", []) or []
    if not languages and not getattr(prefs, "preferred_countries", []):
        return []

    candidates: Dict[int, MediaDetailsResponse] = {}
    content_types = getattr(prefs, "content_types", ["movie", "tv"]) or ["movie", "tv"]

    async def _fetch_lang(lang, media_type):
        try:
            results = await _discover_by_language(client, media_type, lang, limit=15)
            return [
                _build_candidate_from_tmdb_result(c, client, media_type)
                for c in getattr(results, "results", [])
            ]
        except Exception:
            return []

    tasks = [
        _fetch_lang(lang, mtype)
        for lang in languages[:2]
        for mtype in content_types
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            for media in res:
                if media and media.id not in candidates:
                    candidates[media.id] = media

    return list(candidates.values())[:limit]


async def discover_candidates_from_intent(
    client: TMDBClient,
    intent,
    prefs,
    limit: int = MAX_CANDIDATES_PER_SOURCE,
) -> Tuple[List[MediaDetailsResponse], List[MediaDetailsResponse]]:
    """
    Discover candidates based on parsed QueryIntent.
    Returns (seed_titles, candidate_titles).
    """
    seeds: List[MediaDetailsResponse] = []
    candidates: Dict[int, MediaDetailsResponse] = {}

    seed_titles = getattr(intent, "seed_titles", []) or []
    if not seed_titles and getattr(intent, "clean_title", None) and getattr(intent, "intent_type", "") == "similar_title":
        seed_titles = [intent.clean_title]

    # 1. Discover from seeds concurrently
    async def _process_seed(title: str):
        found_seeds = []
        found_cands = []
        try:
            search_res = await client.search_multi(title, page=1)
            for item in getattr(search_res, "results", []):
                item_media_type = getattr(item, "media_type", None)
                if item_media_type in ("movie", "tv"):
                    seed_details = _build_candidate_from_tmdb_result(item, client, item_media_type)
                    if seed_details:
                        found_seeds.append(seed_details)
                        try:
                            sim_resp, rec_resp = await asyncio.gather(
                                _get_similar(client, item_media_type, item.id, limit=12),
                                _get_recommendations(client, item_media_type, item.id, limit=12),
                                return_exceptions=True
                            )
                            if not isinstance(sim_resp, Exception) and hasattr(sim_resp, "results"):
                                for c in sim_resp.results:
                                    if c.id != item.id:
                                        cand = _build_candidate_from_tmdb_result(c, client, item_media_type)
                                        if cand:
                                            found_cands.append(cand)
                            if not isinstance(rec_resp, Exception) and hasattr(rec_resp, "results"):
                                for c in rec_resp.results:
                                    if c.id != item.id:
                                        cand = _build_candidate_from_tmdb_result(c, client, item_media_type)
                                        if cand:
                                            found_cands.append(cand)
                        except Exception:
                            pass
                        break
        except Exception:
            pass
        return found_seeds, found_cands

    seed_tasks = [_process_seed(t) for t in seed_titles[:2]]

    # 2. Discover by genre/language/era concurrently
    genre_ids = getattr(intent, "genre_ids", []) or []
    languages = getattr(intent, "languages", []) or []
    countries = getattr(intent, "countries", []) or []
    era = getattr(intent, "era", None)
    min_rating = getattr(intent, "min_rating", None)

    target_types = ["movie", "tv"]
    intent_media_type = getattr(intent, "media_type", "multi")
    if intent_media_type in ("movie", "tv"):
        target_types = [intent_media_type]

    # Map movie-specific genres to TV genre IDs if discovering TV
    _MOVIE_TO_TV_GENRES = {28: 10759, 878: 10765, 12: 10759}

    async def _discover_media_type(m_type: str):
        found = []
        try:
            kw: Dict[str, Any] = {"page": 1, "sort_by": "popularity.desc"}
            if genre_ids:
                if m_type == "tv":
                    tv_gids = [_MOVIE_TO_TV_GENRES.get(g, g) for g in genre_ids[:3]]
                    kw["with_genres"] = "|".join(str(g) for g in tv_gids)
                else:
                    kw["with_genres"] = "|".join(str(g) for g in genre_ids[:3])

            if languages:
                kw["with_original_language"] = languages[0]

            if m_type == "movie":
                if era and era.start_year:
                    kw["primary_release_date.gte"] = f"{era.start_year}-01-01"
                if era and era.end_year:
                    kw["primary_release_date.lte"] = f"{era.end_year}-12-31"
                if min_rating:
                    kw["vote_average.gte"] = min_rating
                disc_res = await client.discover_movies(**kw)
            else:
                if era and era.start_year:
                    kw["first_air_date.gte"] = f"{era.start_year}-01-01"
                if era and era.end_year:
                    kw["first_air_date.lte"] = f"{era.end_year}-12-31"
                if min_rating:
                    kw["vote_average.gte"] = min_rating
                disc_res = await client.discover_tv(**kw)

            for item in getattr(disc_res, "results", [])[:20]:
                cand = _build_candidate_from_tmdb_result(item, client, m_type)
                if cand:
                    found.append(cand)
        except Exception:
            pass
        return found

    disc_tasks = [_discover_media_type(m) for m in target_types]

    # 3. Discover by themes / keywords concurrently
    search_keywords = list(getattr(intent, "themes", [])) + list(getattr(intent, "characters", []))
    async def _search_kw(kw_term: str):
        found = []
        try:
            res = await client.search_multi(kw_term, page=1)
            for item in getattr(res, "results", [])[:10]:
                item_type = getattr(item, "media_type", None)
                if item_type in ("movie", "tv"):
                    cand = _build_candidate_from_tmdb_result(item, client, item_type)
                    if cand:
                        found.append(cand)
        except Exception:
            pass
        return found

    kw_tasks = [_search_kw(kw) for kw in search_keywords[:2]]

    # Run all intent tasks concurrently
    all_results = await asyncio.gather(*seed_tasks, *disc_tasks, *kw_tasks, return_exceptions=True)

    for res in all_results:
        if isinstance(res, tuple):
            s_list, c_list = res
            seeds.extend(s_list)
            for c in c_list:
                candidates[c.id] = c
        elif isinstance(res, list):
            for c in res:
                candidates[c.id] = c

    return seeds, list(candidates.values())[:limit]


async def get_all_candidates(
    client: TMDBClient,
    favorites: List[MediaDetailsResponse],
    prefs,
    max_total: int = MAX_TOTAL_CANDIDATES,
) -> List[MediaDetailsResponse]:
    """
    Get candidates from all sources concurrently and combine.
    """
    all_candidates: Dict[int, MediaDetailsResponse] = {}

    async def _run_intent():
        if hasattr(prefs, "query") and prefs.query:
            from app.recommender.intent import parse_query_intent
            intent = parse_query_intent(prefs.query)
            seeds, intent_cands = await discover_candidates_from_intent(client, intent, prefs)
            for s in seeds:
                if not any(f.id == s.id for f in favorites):
                    favorites.append(s)
            return intent_cands
        return []

    async def _run_favorites():
        if favorites:
            return await discover_candidates_from_favorites(client, favorites, prefs)
        return []

    async def _run_feedback():
        if hasattr(prefs, "feedback_more_like_this") and prefs.feedback_more_like_this:
            fb_cands = []
            for item in prefs.feedback_more_like_this[:3]:
                try:
                    sim_res = await _get_similar(client, item.media_type, item.item_id, limit=10)
                    for c in getattr(sim_res, "results", []):
                        cand = _build_candidate_from_tmdb_result(c, client, item.media_type)
                        if cand:
                            fb_cands.append(cand)
                except Exception:
                    pass
            return fb_cands
        return []

    async def _run_genres():
        if getattr(prefs, "preferred_genres", None):
            return await discover_candidates_by_genre(client, prefs.preferred_genres, prefs)
        return []

    async def _run_keywords():
        keywords = _get_keywords(favorites)
        if keywords:
            return await discover_candidates_by_keyword(client, keywords, prefs)
        return []

    async def _run_cast_directors():
        if favorites:
            return await discover_candidates_by_cast_director(client, favorites, prefs)
        return []

    async def _run_languages():
        if getattr(prefs, "preferred_languages", None) or getattr(prefs, "preferred_countries", None):
            return await discover_candidates_by_language_country(client, prefs)
        return []

    results = await asyncio.gather(
        _run_intent(),
        _run_favorites(),
        _run_feedback(),
        _run_genres(),
        _run_keywords(),
        _run_cast_directors(),
        _run_languages(),
        return_exceptions=True
    )

    for res in results:
        if isinstance(res, list):
            for c in res:
                if c and c.id not in all_candidates:
                    all_candidates[c.id] = c

    # Fallback source: If still no candidates found, fetch popular titles concurrently
    if not all_candidates:
        content_types = getattr(prefs, "content_types", ["movie", "tv"]) or ["movie", "tv"]
        try:
            tasks = []
            for m_type in content_types:
                if m_type == "movie":
                    tasks.append(client.discover_movies(page=1, sort_by="popularity.desc"))
                else:
                    tasks.append(client.discover_tv(page=1, sort_by="popularity.desc"))
            pop_results = await asyncio.gather(*tasks, return_exceptions=True)
            for m_type, pop_res in zip(content_types, pop_results):
                if not isinstance(pop_res, Exception) and hasattr(pop_res, "results"):
                    for item in pop_res.results[:15]:
                        cand = _build_candidate_from_tmdb_result(item, client, m_type)
                        if cand and cand.id not in all_candidates:
                            all_candidates[cand.id] = cand
        except Exception:
            pass

    # Convert to list
    candidates = list(all_candidates.values())

    # Remove favorites and disliked titles from candidates
    favorite_ids = {f.id for f in favorites}
    disliked_ids = {d.item_id for d in getattr(prefs, "feedback_dislikes", [])}
    candidates = [c for c in candidates if c.id not in favorite_ids and c.id not in disliked_ids]

    return candidates[:max_total]


# Helper functions using real TMDB endpoints

async def _get_similar(client: TMDBClient, media_type: str, item_id: int, limit: int = 10):
    """Get similar titles from TMDB /similar endpoint."""
    if media_type == "movie":
        return await client.get_movie_similar(item_id, page=1)
    else:
        return await client.get_tv_similar(item_id, page=1)


async def _get_recommendations(client: TMDBClient, media_type: str, item_id: int, limit: int = 10):
    """Get recommendations from TMDB /recommendations endpoint."""
    if media_type == "movie":
        return await client.get_movie_recommendations(item_id, page=1)
    else:
        return await client.get_tv_recommendations(item_id, page=1)


async def _discover_by_genre(client: TMDBClient, media_type: str, genre_id: int, limit: int = 10):
    """Discover titles by genre using TMDB discover endpoint."""
    genre_str = str(genre_id)
    if media_type == "movie":
        return await client.discover_movies(
            page=1,
            with_genres=genre_str,
            sort_by="popularity.desc",
        )
    else:
        return await client.discover_tv(
            page=1,
            with_genres=genre_str,
            sort_by="popularity.desc",
        )


async def _search_by_keyword(client: TMDBClient, media_type: str, keyword: str, limit: int = 10):
    """Search titles by keyword using TMDB multi search."""
    return await client.search_multi(keyword, page=1)


async def _discover_by_language(client: TMDBClient, media_type: str, language: str, limit: int = 10):
    """Discover titles by language using TMDB discover endpoint."""
    if media_type == "movie":
        return await client.discover_movies(
            page=1,
            with_original_language=language,
            sort_by="popularity.desc",
        )
    else:
        return await client.discover_tv(
            page=1,
            with_original_language=language,
            sort_by="popularity.desc",
        )


async def _get_details(client: TMDBClient, media_type: str, item_id: int):
    """Get full media details."""
    if media_type == "movie":
        return await client.get_movie_details(item_id)
    else:
        return await client.get_tv_details(item_id)


def _get_top_cast(favorites: List[MediaDetailsResponse], top_n: int = 5) -> List[str]:
    """Extract top cast names from favorites."""
    from collections import Counter
    cast_counter = Counter()
    for fav in favorites:
        for cast in getattr(fav, "cast", [])[:top_n]:
            cast_counter[cast.name] += 1
    return [name for name, _ in cast_counter.most_common(5)]


def _get_directors(favorites: List[MediaDetailsResponse], top_n: int = 3) -> List[str]:
    """Extract director names from favorites."""
    from collections import Counter
    dir_counter = Counter()
    for fav in favorites:
        for dir in getattr(fav, "directors", [])[:top_n]:
            dir_counter[dir.name] += 1
    return [name for name, _ in dir_counter.most_common(3)]


def _get_keywords(favorites: List[MediaDetailsResponse]) -> List[str]:
    """Extract keywords from favorites."""
    from collections import Counter
    kw_counter = Counter()
    for fav in favorites:
        for kw in getattr(fav, "keywords", []):
            kw_counter[kw.name.lower()] += 1
    return [kw for kw, _ in kw_counter.most_common(10)]


def get_candidates_sync(
    favorites: List[MediaDetailsResponse],
    prefs,
    max_total: int = MAX_TOTAL_CANDIDATES,
) -> List[MediaDetailsResponse]:
    """Synchronous candidate discovery placeholder."""
    return []


def filter_candidates_by_preferences(
    candidates: List[MediaDetailsResponse],
    prefs,
) -> List[MediaDetailsResponse]:
    """Apply hard exclusions to candidates."""
    from app.recommender.profile import apply_hard_exclusions
    return apply_hard_exclusions(candidates, prefs)