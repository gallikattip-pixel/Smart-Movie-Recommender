"""TMDB API response models for normalization."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class TMDBGenre(BaseModel):
    """TMDB genre object."""

    id: int
    name: str


class TMDBProductionCompany(BaseModel):
    """TMDB production company object."""

    id: int
    name: str
    logo_path: Optional[str] = None
    origin_country: Optional[str] = None


class TMDBProductionCountry(BaseModel):
    """TMDB production country object."""

    iso_3166_1: str
    name: str


class TMDBSpokenLanguage(BaseModel):
    """TMDB spoken language object."""

    english_name: str
    iso_639_1: str
    name: str


class TMDBMovie(BaseModel):
    """TMDB movie search result."""

    id: int
    title: str
    original_title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: Optional[str] = None
    genre_ids: List[int] = []
    adult: bool = False
    video: bool = False


class TMDBTVSeries(BaseModel):
    """TMDB TV series search result."""

    id: int
    name: str
    original_name: str
    overview: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: Optional[str] = None
    genre_ids: List[int] = []
    origin_country: List[str] = []


class TMDBPerson(BaseModel):
    """TMDB person search result (excluded from our results)."""

    id: int
    name: str
    known_for_department: str
    popularity: float


class TMDBMultiSearchResult(BaseModel):
    """TMDB multi-search result - can be movie, tv, or person."""

    id: int
    media_type: Optional[str] = None  # "movie" | "tv" | "person"
    title: Optional[str] = None  # for movies
    name: Optional[str] = None  # for tv series
    original_title: Optional[str] = None
    original_name: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: Optional[str] = None
    genre_ids: List[int] = []
    adult: bool = False
    video: bool = False
    known_for_department: Optional[str] = None
    origin_country: List[str] = []


class TMDBPaginatedResponse(BaseModel):
    """TMDB paginated response wrapper."""

    page: int
    results: List["TMDBMultiSearchResult | TMDBSimilarResult | TMDBDiscoverResult | TMDBMovie | TMDBTVSeries"]
    total_pages: int
    total_results: int


# Detailed models
class TMDBMovieDetails(BaseModel):
    """TMDB movie details response."""

    id: int
    title: str
    original_title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: str
    genres: List[TMDBGenre] = []
    runtime: Optional[int] = None
    tagline: Optional[str] = None
    homepage: Optional[str] = None
    production_companies: List[TMDBProductionCompany] = []
    production_countries: List[TMDBProductionCountry] = []
    spoken_languages: List[TMDBSpokenLanguage] = []
    status: Optional[str] = None
    adult: bool = False
    video: bool = False


class TMDBTVSeriesDetails(BaseModel):
    """TMDB TV series details response."""

    id: int
    name: str
    original_name: str
    overview: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: str
    genres: List[TMDBGenre] = []
    episode_run_time: List[int] = []
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    status: Optional[str] = None
    tagline: Optional[str] = None
    homepage: Optional[str] = None
    production_companies: List[TMDBProductionCompany] = []
    production_countries: List[TMDBProductionCountry] = []
    spoken_languages: List[TMDBSpokenLanguage] = []
    origin_country: List[str] = []
    networks: List[dict] = []
    created_by: List[dict] = []


class TMDBCastMember(BaseModel):
    """TMDB cast member."""

    id: int
    name: str
    character: Optional[str] = None
    profile_path: Optional[str] = None
    order: int = 0
    known_for_department: str = "Acting"


class TMDBCrewMember(BaseModel):
    """TMDB crew member."""

    id: int
    name: str
    job: str
    department: str
    profile_path: Optional[str] = None


class TMDBCredits(BaseModel):
    """TMDB credits response."""

    id: int
    cast: List[TMDBCastMember] = []
    crew: List[TMDBCrewMember] = []


class TMDBKeyword(BaseModel):
    """TMDB keyword."""

    id: int
    name: str


class TMDBKeywords(BaseModel):
    """TMDB keywords response."""

    id: int
    keywords: List[TMDBKeyword] = []


# Similar/Recommendations models
class TMDBSimilarResult(BaseModel):
    """TMDB similar movie/TV result."""

    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    original_title: Optional[str] = None
    original_name: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: Optional[str] = None
    genre_ids: List[int] = []
    adult: bool = False
    media_type: Optional[str] = "movie"


class TMDBDiscoverResult(BaseModel):
    """TMDB discover result."""

    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    original_title: Optional[str] = None
    original_name: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: int = 0
    popularity: float = 0.0
    original_language: Optional[str] = None
    genre_ids: List[int] = []
    adult: bool = False
    video: bool = False
    origin_country: List[str] = []


class TMDBImageConfig(BaseModel):
    """TMDB image configuration."""

    base_url: str
    secure_base_url: str
    backdrop_sizes: List[str]
    logo_sizes: List[str]
    poster_sizes: List[str]
    profile_sizes: List[str]
    still_sizes: List[str]


class TMDBConfiguration(BaseModel):
    """TMDB configuration response."""

    images: TMDBImageConfig
    change_keys: List[str] = []


class TMDBErrorResponse(BaseModel):
    """TMDB error response."""

    status_code: int
    status_message: str
    success: bool = False