"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import date


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    tmdb_configured: bool = Field(..., description="Whether TMDB credentials are configured")


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class SearchRequest(BaseModel):
    """Movie/TV search request."""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    type: Literal["multi", "movie", "tv"] = Field("multi", description="Search type")
    page: int = Field(1, ge=1, le=1000, description="Page number")
    include_adult: bool = Field(False, description="Include adult content")
    language: str = Field("en-US", description="Language code (ISO 639-1)")


class SearchResultItem(BaseModel):
    """Single search result item."""

    id: int
    title: str
    media_type: Literal["movie", "tv"]
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: str
    genre_ids: list[int] = []


class SearchResponse(BaseModel):
    """Search response."""

    results: list[SearchResultItem]
    page: int
    total_pages: int
    total_results: int
    query: str
    search_type: str
    intent: Optional[Dict[str, Any]] = None


# Detailed media schemas
class GenreItem(BaseModel):
    """Genre with id and name."""

    id: int
    name: str


class ProductionCompanyItem(BaseModel):
    """Production company."""

    id: int
    name: str
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None
    origin_country: Optional[str] = None


class ProductionCountryItem(BaseModel):
    """Production country."""

    iso_3166_1: str
    name: str


class SpokenLanguageItem(BaseModel):
    """Spoken language."""

    english_name: str
    iso_639_1: str
    name: str


class CastMemberItem(BaseModel):
    """Cast member."""

    id: int
    name: str
    character: Optional[str] = None
    profile_path: Optional[str] = None
    profile_url: Optional[str] = None
    order: int = 0
    known_for_department: str = "Acting"


class CrewMemberItem(BaseModel):
    """Crew member."""

    id: int
    name: str
    job: str
    department: str
    profile_path: Optional[str] = None
    profile_url: Optional[str] = None


class KeywordItem(BaseModel):
    """Keyword."""

    id: int
    name: str


class MediaDetailsResponse(BaseModel):
    """Detailed media information."""

    id: int
    title: str
    media_type: Literal["movie", "tv"]
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: str
    genres: List[GenreItem] = []
    runtime: Optional[int] = None
    episode_run_time: List[int] = []
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    status: Optional[str] = None
    tagline: Optional[str] = None
    homepage: Optional[str] = None
    production_companies: List[ProductionCompanyItem] = []
    production_countries: List[ProductionCountryItem] = []
    spoken_languages: List[SpokenLanguageItem] = []
    cast: List[CastMemberItem] = []
    crew: List[CrewMemberItem] = []
    keywords: List[KeywordItem] = []
    directors: List[CrewMemberItem] = []


# Favorites resolution schemas
class FavoriteTitleRequest(BaseModel):
    """Request to resolve a favorite title."""

    media_type: Literal["movie", "tv"]
    item_id: int = Field(..., ge=1, description="TMDB ID")


class FavoritesResolveRequest(BaseModel):
    """Request to resolve multiple favorite titles."""

    titles: List[FavoriteTitleRequest] = Field(
        ..., min_length=1, max_length=50, description="List of favorite titles to resolve"
    )


class FavoritesResolveResponse(BaseModel):
    """Response with resolved favorite titles."""

    resolved: List[MediaDetailsResponse]
    failed: List[Dict[str, Any]] = []


class FavoritesStoreRequest(BaseModel):
    """Request to store favorites (for frontend localStorage sync)."""

    favorites: List[FavoriteTitleRequest]


# Recommendation schemas
class EraRange(BaseModel):
    """Release era range."""

    start_year: Optional[int] = Field(None, ge=1900, le=2100)
    end_year: Optional[int] = Field(None, ge=1900, le=2100)


class UserPreference(BaseModel):
    """Structured user preference profile."""

    # Query context (for intent-driven recommendations)
    query: Optional[str] = Field(None, description="Current search or recommendation query")

    # Favorite titles (resolved to TMDB IDs)
    favorite_titles: List[FavoriteTitleRequest] = Field(
        default_factory=list, description="Favorite movie/TV IDs"
    )

    # Interactive feedback lists
    feedback_likes: List[FavoriteTitleRequest] = Field(
        default_factory=list, description="Titles the user liked"
    )
    feedback_dislikes: List[FavoriteTitleRequest] = Field(
        default_factory=list, description="Titles the user disliked"
    )
    feedback_watched: List[FavoriteTitleRequest] = Field(
        default_factory=list, description="Titles the user already watched"
    )
    feedback_more_like_this: List[FavoriteTitleRequest] = Field(
        default_factory=list, description="Titles the user wants more like"
    )

    # Genre preferences
    preferred_genres: List[int] = Field(default_factory=list, description="Preferred genre IDs")
    excluded_genres: List[int] = Field(default_factory=list, description="Excluded genre IDs")

    # Language preferences
    preferred_languages: List[str] = Field(default_factory=list, description="Preferred language codes (ISO 639-1)")
    excluded_languages: List[str] = Field(default_factory=list, description="Excluded language codes")

    # Country preferences
    preferred_countries: List[str] = Field(default_factory=list, description="Preferred country codes (ISO 3166-1)")
    excluded_countries: List[str] = Field(default_factory=list, description="Excluded country codes")

    # Content type
    content_types: List[Literal["movie", "tv"]] = Field(
        default_factory=lambda: ["movie", "tv"], description="Allowed content types"
    )

    # Release era
    era: Optional[EraRange] = Field(None, description="Preferred release era")

    # Rating
    min_vote_average: Optional[float] = Field(None, ge=0.0, le=10.0, description="Minimum TMDB vote average")

    # Themes/moods (user-specified, not from TMDB)
    preferred_themes: List[str] = Field(default_factory=list, description="Preferred story themes")
    excluded_themes: List[str] = Field(default_factory=list, description="Excluded story themes")
    preferred_moods: List[str] = Field(default_factory=list, description="Preferred moods")
    excluded_moods: List[str] = Field(default_factory=list, description="Excluded moods")

    # Pacing/ending preferences (user-specified)
    preferred_pacing: List[str] = Field(default_factory=list, description="Preferred pacing (slow, medium, fast)")
    preferred_endings: List[str] = Field(default_factory=list, description="Preferred ending types")

    # Discovery mode
    prefer_hidden_gems: bool = Field(False, description="Prefer less popular titles")
    prefer_similar: bool = Field(True, description="Prefer similar to favorites vs new discoveries")


class RecommendRequest(BaseModel):
    """Recommendation request."""

    preferences: UserPreference = Field(..., description="User preference profile")
    limit: int = Field(20, ge=1, le=50, description="Number of recommendations to return")
    algorithm: Literal["bfs", "dfs", "ucs", "greedy", "astar", "hybrid"] = Field(
        "hybrid", description="Search algorithm to use for candidate discovery"
    )
    exclude_favorites: bool = Field(True, description="Exclude favorite titles from recommendations")
    include_explanations: bool = Field(True, description="Include explanation for each recommendation")


class ExplanationReason(BaseModel):
    """Single explanation reason."""

    type: Literal["genre", "keyword", "cast", "director", "language", "country", "era", "rating", "theme", "mood", "content_type", "hidden_gem", "similar_to_favorite"]
    description: str
    weight: float = Field(..., ge=0.0, le=1.0)


class RecommendationItem(BaseModel):
    """Single recommendation with scoring and explanation."""

    media: MediaDetailsResponse
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Content similarity score")
    preference_score: float = Field(..., ge=0.0, le=1.0, description="Weighted preference match score")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final combined ranking score")
    explanation: List[ExplanationReason] = Field(default_factory=list, description="Why this was recommended")
    graph_path: Optional[List[int]] = Field(None, description="Graph path from favorite to this title (if applicable)")


class RecommendResponse(BaseModel):
    """Recommendation response."""

    recommendations: List[RecommendationItem]
    algorithm_used: str
    total_candidates_considered: int
    total_excluded: int
    search_time_ms: float