"""User preference profile construction and validation."""

from typing import List, Optional, Set
from app.schemas import (
    UserPreference,
    FavoriteTitleRequest,
    MediaDetailsResponse,
    EraRange,
    GenreItem,
    ProductionCompanyItem,
    ProductionCountryItem,
    SpokenLanguageItem,
    CastMemberItem,
    CrewMemberItem,
    KeywordItem,
)
from app.tmdb.models import (
    TMDBGenre,
    TMDBProductionCompany,
    TMDBProductionCountry,
    TMDBSpokenLanguage,
    TMDBCastMember,
    TMDBCrewMember,
    TMDBKeyword,
)


# TMDB genre ID to name mapping (subset of common genres)
TMDB_GENRE_NAMES = {
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
}


def validate_preferences(prefs: UserPreference) -> List[str]:
    """
    Validate user preferences and return list of warnings.
    
    Does not raise - preferences are optional and warnings inform the user.
    """
    warnings = []

    if not prefs.favorite_titles and not any([
        prefs.preferred_genres,
        prefs.preferred_languages,
        prefs.preferred_countries,
        prefs.content_types != ["movie", "tv"],
        prefs.era,
        prefs.min_vote_average,
        prefs.preferred_themes,
        prefs.preferred_moods,
    ]):
        warnings.append(
            "No preferences specified. Recommendations will be based on general popularity."
        )

    if prefs.favorite_titles:
        if len(prefs.favorite_titles) > 20:
            warnings.append("Many favorite titles may slow down recommendation generation.")

    if prefs.excluded_genres and prefs.preferred_genres:
        overlap = set(prefs.excluded_genres) & set(prefs.preferred_genres)
        if overlap:
            warnings.append(
                f"Genres both preferred and excluded: {overlap}. Exclusions take precedence."
            )

    if prefs.min_vote_average is not None and prefs.min_vote_average > 8.0:
        warnings.append("High minimum rating may severely limit results.")

    if prefs.era:
        if prefs.era.start_year and prefs.era.end_year and prefs.era.start_year > prefs.era.end_year:
            warnings.append("Era start year is after end year. Ignoring era filter.")

    return warnings


def extract_genres_from_favorites(favorites: List[MediaDetailsResponse]) -> List[int]:
    """Extract unique genre IDs from favorite titles."""
    genre_ids: Set[int] = set()
    for fav in favorites:
        for genre in fav.genres:
            genre_ids.add(genre.id)
    return list(genre_ids)


def extract_keywords_from_favorites(favorites: List[MediaDetailsResponse]) -> List[str]:
    """Extract unique keyword names from favorite titles."""
    keywords: Set[str] = set()
    for fav in favorites:
        for kw in fav.keywords:
            keywords.add(kw.name.lower())
    return list(keywords)


def extract_languages_from_favorites(favorites: List[MediaDetailsResponse]) -> List[str]:
    """Extract unique original languages from favorite titles."""
    langs: Set[str] = set()
    for fav in favorites:
        if fav.original_language:
            langs.add(fav.original_language)
    return list(langs)


def extract_countries_from_favorites(favorites: List[MediaDetailsResponse]) -> List[str]:
    """Extract unique production countries from favorite titles."""
    countries: Set[str] = set()
    for fav in favorites:
        for country in fav.production_countries:
            if country.iso_3166_1:
                countries.add(country.iso_3166_1)
    return list(countries)


def extract_directors_from_favorites(favorites: List[MediaDetailsResponse]) -> List[str]:
    """Extract unique director names from favorite titles."""
    directors: Set[str] = set()
    for fav in favorites:
        for director in fav.directors:
            directors.add(director.name)
    return list(directors)


def extract_cast_from_favorites(favorites: List[MediaDetailsResponse], top_n: int = 5) -> List[str]:
    """Extract top cast members from favorite titles."""
    from collections import Counter
    cast_counter: Counter[str] = Counter()
    for fav in favorites:
        for cast in fav.cast[:top_n]:
            cast_counter[cast.name] += 1
    return [name for name, _ in cast_counter.most_common(10)]


def extract_eras_from_favorites(favorites: List[MediaDetailsResponse]) -> Optional[EraRange]:
    """Extract era range from favorite titles."""
    years = []
    for fav in favorites:
        if fav.media_type == "movie" and fav.release_date:
            try:
                year = int(fav.release_date[:4])
                years.append(year)
            except (ValueError, IndexError):
                pass
        elif fav.media_type == "tv" and fav.first_air_date:
            try:
                year = int(fav.first_air_date[:4])
                years.append(year)
            except (ValueError, IndexError):
                pass

    if not years:
        return None

    return EraRange(start_year=min(years), end_year=max(years))


def build_profile_from_favorites(favorites: List[MediaDetailsResponse]) -> UserPreference:
    """
    Build a user preference profile from resolved favorite titles.
    
    This infers preferences from actual metadata of liked titles.
    """
    if not favorites:
        return UserPreference()

    return UserPreference(
        favorite_titles=[
            FavoriteTitleRequest(media_type=f.media_type, item_id=f.id)
            for f in favorites
        ],
        preferred_genres=extract_genres_from_favorites(favorites),
        preferred_languages=extract_languages_from_favorites(favorites),
        preferred_countries=extract_countries_from_favorites(favorites),
        era=extract_eras_from_favorites(favorites),
        # These would need explicit user input
        preferred_themes=[],
        preferred_moods=[],
        preferred_pacing=[],
        preferred_endings=[],
        content_types=["movie", "tv"],
    )


def merge_preferences(explicit: UserPreference, inferred: UserPreference) -> UserPreference:
    """
    Merge explicit user preferences with inferred preferences from favorites.
    
    Explicit preferences take precedence; inferred fills gaps.
    """
    # Start with explicit
    merged = explicit.model_copy(deep=True)

    # Fill in missing preferences from inferred
    if not merged.favorite_titles:
        merged.favorite_titles = inferred.favorite_titles

    if not merged.preferred_genres:
        merged.preferred_genres = inferred.preferred_genres

    if not merged.preferred_languages:
        merged.preferred_languages = inferred.preferred_languages

    if not merged.preferred_countries:
        merged.preferred_countries = inferred.preferred_countries

    if not merged.era and inferred.era:
        # Widen inferred era by 10 years on each side to avoid over-filtering
        from app.schemas import EraRange
        start = inferred.era.start_year - 10 if inferred.era.start_year else None
        end = inferred.era.end_year + 10 if inferred.era.end_year else None
        merged.era = EraRange(start_year=start, end_year=end)

    if not merged.content_types or merged.content_types == ["movie", "tv"]:
        merged.content_types = inferred.content_types or ["movie", "tv"]

    return merged


def genre_id_to_name(genre_id: int) -> str:
    """Convert TMDB genre ID to human-readable name."""
    return TMDB_GENRE_NAMES.get(genre_id, f"Genre {genre_id}")


def apply_hard_exclusions(
    candidates: List[MediaDetailsResponse],
    prefs: UserPreference,
) -> List[MediaDetailsResponse]:
    """
    Apply hard exclusions that must never be violated.
    
    Returns filtered list of candidates.
    """
    excluded_genre_set = set(prefs.excluded_genres)
    excluded_lang_set = set(prefs.excluded_languages)
    excluded_country_set = set(prefs.excluded_countries)
    allowed_types = set(prefs.content_types)
    min_rating = prefs.min_vote_average
    excluded_theme_set = set(t.lower() for t in prefs.excluded_themes)

    filtered = []
    for candidate in candidates:
        # Check content type
        if candidate.media_type not in allowed_types:
            continue

        # Check excluded genres
        candidate_genre_ids = {g.id for g in candidate.genres}
        if excluded_genre_set & candidate_genre_ids:
            continue

        # Check excluded languages
        if candidate.original_language in excluded_lang_set:
            continue

        # Check excluded countries
        candidate_countries = {c.iso_3166_1 for c in candidate.production_countries if c.iso_3166_1}
        if excluded_country_set & candidate_countries:
            continue

        # Check minimum rating
        if min_rating is not None:
            if candidate.vote_average is None or candidate.vote_average < min_rating:
                continue

        # Check excluded themes (from keywords)
        if excluded_theme_set:
            candidate_keywords = {k.name.lower() for k in candidate.keywords}
            if excluded_theme_set & candidate_keywords:
                continue

        # Check era
        if prefs.era:
            year = None
            if candidate.media_type == "movie" and candidate.release_date:
                try:
                    year = int(candidate.release_date[:4])
                except (ValueError, IndexError):
                    pass
            elif candidate.media_type == "tv" and candidate.first_air_date:
                try:
                    year = int(candidate.first_air_date[:4])
                except (ValueError, IndexError):
                    pass

            if year is not None:
                if prefs.era.start_year and year < prefs.era.start_year:
                    continue
                if prefs.era.end_year and year > prefs.era.end_year:
                    continue

        filtered.append(candidate)

    return filtered


# --- TMDB data normalization helpers ---

def _normalize_genres(genres: List[TMDBGenre]) -> List[GenreItem]:
    """Normalize TMDB genres to our schema."""
    from app.schemas import GenreItem
    return [GenreItem(id=g.id, name=g.name) for g in genres]


def _normalize_production_companies(
    companies: List[TMDBProductionCompany], client
) -> List[ProductionCompanyItem]:
    """Normalize TMDB production companies to our schema."""
    from app.schemas import ProductionCompanyItem
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
    from app.schemas import ProductionCountryItem
    return [
        ProductionCountryItem(iso_3166_1=c.iso_3166_1, name=c.name)
        for c in countries
    ]


def _normalize_spoken_languages(
    languages: List[TMDBSpokenLanguage]
) -> List[SpokenLanguageItem]:
    """Normalize TMDB spoken languages to our schema."""
    from app.schemas import SpokenLanguageItem
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
    from app.schemas import CastMemberItem
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
    from app.schemas import CrewMemberItem
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
    from app.schemas import KeywordItem
    return [KeywordItem(id=k.id, name=k.name) for k in keywords]


def _extract_directors(crew: List[CrewMemberItem]) -> List[CrewMemberItem]:
    """Extract directors from crew."""
    return [c for c in crew if c.job == "Director" and c.department == "Directing"]