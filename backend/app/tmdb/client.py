"""TMDB API client with authentication, error handling, and lifecycle management."""

import httpx
import time
import json
import asyncio
import shutil
import urllib.parse
from typing import Optional, List, Dict, Tuple, Any
from contextlib import asynccontextmanager

from app.config import settings
from app.tmdb.models import (
    TMDBMultiSearchResult,
    TMDBPaginatedResponse,
    TMDBConfiguration,
    TMDBErrorResponse,
    TMDBMovieDetails,
    TMDBTVSeriesDetails,
    TMDBCredits,
    TMDBKeywords,
    TMDBSimilarResult,
    TMDBDiscoverResult,
)


class SimpleTTLCache:
    """Thread-safe in-memory TTL cache for TMDB API responses."""

    def __init__(self, default_ttl: float = 300.0, max_entries: int = 2000):
        self._ttl = default_ttl
        self._max_entries = max_entries
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _make_key(self, path: str, params: Optional[dict]) -> str:
        if not params:
            return path
        param_items = sorted((str(k), str(v)) for k, v in params.items())
        return f"{path}?{param_items}"

    def get(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        key = self._make_key(path, params)
        item = self._cache.get(key)
        if item is None:
            return None
        expires_at, data = item
        if time.time() > expires_at:
            self._cache.pop(key, None)
            return None
        return data

    def set(self, path: str, params: Optional[dict], data: Any, ttl: Optional[float] = None) -> None:
        key = self._make_key(path, params)
        now = time.time()
        expires_at = now + (ttl if ttl is not None else self._ttl)

        if len(self._cache) >= self._max_entries:
            expired_keys = [k for k, (exp, _) in self._cache.items() if exp < now]
            for k in expired_keys:
                self._cache.pop(k, None)
            if len(self._cache) >= self._max_entries:
                keys_to_drop = list(self._cache.keys())[:int(self._max_entries * 0.2)]
                for k in keys_to_drop:
                    self._cache.pop(k, None)

        self._cache[key] = (expires_at, data)

    def clear(self) -> None:
        self._cache.clear()


class TMDBError(Exception):
    """Base exception for TMDB API errors."""

    def __init__(self, message: str, status_code: int = 0, code: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class TMDBConfigError(TMDBError):
    """Raised when TMDB credentials are not configured."""

    def __init__(self):
        super().__init__(
            "TMDB API credentials not configured. Set TMDB_ACCESS_TOKEN in environment.",
            status_code=503,
            code="TMDB_NOT_CONFIGURED",
        )


class TMDBAuthError(TMDBError):
    """Raised when TMDB authentication fails."""

    def __init__(self, message: str = "TMDB authentication failed"):
        super().__init__(message, status_code=401, code="TMDB_AUTH_FAILED")


class TMDBRateLimitError(TMDBError):
    """Raised when TMDB rate limit is exceeded."""

    def __init__(self, message: str = "TMDB rate limit exceeded", retry_after: int = 0):
        super().__init__(message, status_code=429, code="TMDB_RATE_LIMITED")
        self.retry_after = retry_after


class TMDBUpstreamError(TMDBError):
    """Raised when TMDB returns a server error."""

    def __init__(self, message: str = "TMDB service error"):
        super().__init__(message, status_code=502, code="TMDB_UPSTREAM_ERROR")


class TMDBTimeoutError(TMDBError):
    """Raised when TMDB request times out."""

    def __init__(self, message: str = "TMDB request timeout"):
        super().__init__(message, status_code=504, code="TMDB_TIMEOUT")


class TMDBNetworkError(TMDBError):
    """Raised when network error occurs."""

    def __init__(self, message: str = "Network error connecting to TMDB"):
        super().__init__(message, status_code=503, code="TMDB_NETWORK_ERROR")


class TMDBNotFoundError(TMDBError):
    """Raised when TMDB resource is not found."""

    def __init__(self, message: str = "Media not found"):
        super().__init__(message, status_code=404, code="TMDB_NOT_FOUND")


class TMDBClient:
    """Async TMDB API client with Bearer token authentication."""

    # Default timeout configuration
    DEFAULT_TIMEOUT = httpx.Timeout(connect=3.5, read=5.0, write=5.0, pool=3.0)

    def __init__(
        self,
        access_token: str = "",
        base_url: str = "https://api.themoviedb.org/3",
        timeout: Optional[httpx.Timeout] = None,
        enable_doh_fallback: bool = False,
    ):
        """
        Initialize TMDB client.

        Args:
            access_token: TMDB v4 Bearer token (empty string means not configured)
            base_url: TMDB API base URL
            timeout: Optional custom timeout configuration
            enable_doh_fallback: Optional local DoH fallback (disabled by default in production)
        """
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._enable_doh_fallback = enable_doh_fallback
        self._client: Optional[httpx.AsyncClient] = None
        self._image_config: Optional[TMDBConfiguration] = None
        self._configured = bool(access_token)
        self._cache = SimpleTTLCache(default_ttl=300.0, max_entries=2000)
        self._use_doh = False

    @property
    def is_configured(self) -> bool:
        """Check if client has valid credentials."""
        return self._configured

    @property
    def _headers(self) -> dict:
        """Request headers with Bearer authentication."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    def _require_configured(self) -> None:
        """Raise error if client is not configured."""
        if not self._configured:
            raise TMDBConfigError()

    async def __aenter__(self) -> "TMDBClient":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Initialize HTTP client with standard HTTPS, TLS verification, and connection pooling."""
        if self._client is None or self._client.is_closed:
            # Create standard HTTP client with bounded connection pool and full TLS verification
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers if self._configured else {"Accept": "application/json"},
                timeout=self._timeout,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                follow_redirects=True,
                verify=True,
            )
            # Pre-fetch image configuration if configured
            if self._configured:
                await self._fetch_image_config()

    async def close(self) -> None:
        """Close HTTP client and clear cache."""
        self._cache.clear()
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            raise RuntimeError("TMDBClient not started. Call start() or use async context manager.")
        return self._client

    async def _fetch_image_config(self) -> None:
        """Fetch and cache TMDB image configuration."""
        try:
            response = await self._ensure_client().get("/configuration")
            response.raise_for_status()
            self._image_config = TMDBConfiguration(**response.json())
        except Exception:
            # Configuration is not critical; use defaults if unavailable
            self._image_config = None

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle TMDB API error responses."""
        status_code = response.status_code

        if status_code == 401:
            raise TMDBAuthError("Invalid or expired TMDB access token")
        elif status_code == 404:
            raise TMDBNotFoundError("Media not found")
        elif status_code == 429:
            retry_after = 0
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except ValueError:
                    pass
            raise TMDBRateLimitError("TMDB rate limit exceeded", retry_after=retry_after)
        elif 500 <= status_code < 600:
            raise TMDBUpstreamError(f"TMDB server error: {status_code}")

        # Try to parse TMDB error format
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "status_message" in error_data:
                raise TMDBError(
                    error_data["status_message"],
                    status_code=error_data.get("status_code", status_code),
                    code="TMDB_API_ERROR",
                )
        except (ValueError, KeyError):
            pass

        # Generic error
        raise TMDBError(
            f"TMDB API error: {status_code}",
            status_code=status_code,
            code="TMDB_API_ERROR",
        )

    async def _curl_fallback(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        """
        Optional local fallback using cross-platform curl with DoH.
        Only called if enable_doh_fallback is explicitly enabled.
        Preserves strict TLS certificate verification (no --insecure).
        """
        if not self._enable_doh_fallback:
            return None

        curl_bin = shutil.which("curl") or shutil.which("curl.exe")
        if not curl_bin:
            return None

        try:
            url = f"{self._base_url}{path}"
            if params:
                url += "?" + urllib.parse.urlencode(params)
            cmd = [
                curl_bin, "-s", "--max-time", "5", "--doh-url", "https://1.1.1.1/dns-query",
                "-H", f"Authorization: Bearer {self._access_token}",
                "-H", "Accept: application/json",
                url
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=6.0)
            if proc.returncode == 0 and stdout:
                parsed = json.loads(stdout.decode())
                if isinstance(parsed, dict) and parsed.get("status_code", 0) in (401, 404):
                    return None
                return parsed
        except Exception:
            pass
        return None

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make authenticated request with error handling and quick retry."""
        self._require_configured()
        client = self._ensure_client()
        for attempt in range(2):
            try:
                response = await client.request(method, path, **kwargs)
                if response.is_success:
                    return response
                if response.status_code in (502, 503, 504) and attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
                self._handle_error(response)
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
                if isinstance(e, httpx.TimeoutException):
                    raise TMDBTimeoutError(f"Request timeout: {e}") from e
                raise TMDBNetworkError(f"Network error: {e}") from e
            except TMDBError:
                raise
            except Exception as e:
                raise TMDBError(f"Unexpected error: {e}", code="TMDB_UNEXPECTED") from e

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make GET request and return parsed JSON with caching and standard error handling."""
        cached = self._cache.get(path, params)
        if cached is not None:
            return cached

        # Fast-path if DoH fallback was explicitly enabled and confirmed active
        if self._enable_doh_fallback and self._use_doh:
            data = await self._curl_fallback(path, params)
            if data is not None:
                self._cache.set(path, params, data)
                return data

        self._require_configured()
        try:
            response = await self._request("GET", path, params=params)
            data = response.json()
            self._cache.set(path, params, data)
            return data
        except (TMDBTimeoutError, TMDBNetworkError):
            if self._enable_doh_fallback:
                data = await self._curl_fallback(path, params)
                if data is not None:
                    self._use_doh = True
                    self._cache.set(path, params, data)
                    return data
            raise

    # Search methods
    async def search_multi(
        self, query: str, page: int = 1, include_adult: bool = False, language: str = "en-US"
    ) -> TMDBPaginatedResponse:
        """Search movies, TV series, and people."""
        params = {
            "query": query,
            "page": page,
            "include_adult": str(include_adult).lower(),
            "language": language,
        }
        data = await self.get("/search/multi", params=params)
        return TMDBPaginatedResponse(**data)

    async def search_movies(
        self, query: str, page: int = 1, include_adult: bool = False, language: str = "en-US"
    ) -> TMDBPaginatedResponse:
        """Search movies only."""
        params = {
            "query": query,
            "page": page,
            "include_adult": str(include_adult).lower(),
            "language": language,
        }
        data = await self.get("/search/movie", params=params)
        # Parse with TMDBMovie model for movie search results
        from app.tmdb.models import TMDBMovie, TMDBPaginatedResponse
        results = [TMDBMovie(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    async def search_tv(
        self, query: str, page: int = 1, include_adult: bool = False, language: str = "en-US"
    ) -> TMDBPaginatedResponse:
        """Search TV series only."""
        params = {
            "query": query,
            "page": page,
            "include_adult": str(include_adult).lower(),
            "language": language,
        }
        data = await self.get("/search/tv", params=params)
        # Parse with TMDBTVSeries model for TV search results
        from app.tmdb.models import TMDBTVSeries, TMDBPaginatedResponse
        results = [TMDBTVSeries(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    # Details methods
    async def get_movie_details(
        self, movie_id: int, language: str = "en-US", append_to_response: Optional[str] = None
    ):
        """Get detailed movie information."""
        params = {"language": language}
        if append_to_response:
            params["append_to_response"] = append_to_response
        data = await self.get(f"/movie/{movie_id}", params=params)
        from app.tmdb.models import TMDBMovieDetails
        return TMDBMovieDetails(**data)

    async def get_tv_details(
        self, tv_id: int, language: str = "en-US", append_to_response: Optional[str] = None
    ):
        """Get detailed TV series information."""
        params = {"language": language}
        if append_to_response:
            params["append_to_response"] = append_to_response
        data = await self.get(f"/tv/{tv_id}", params=params)
        from app.tmdb.models import TMDBTVSeriesDetails
        return TMDBTVSeriesDetails(**data)

    # Credits methods
    async def get_movie_credits(self, movie_id: int, language: str = "en-US"):
        """Get movie credits (cast and crew)."""
        params = {"language": language}
        data = await self.get(f"/movie/{movie_id}/credits", params=params)
        from app.tmdb.models import TMDBCredits
        return TMDBCredits(**data)

    async def get_tv_credits(self, tv_id: int, language: str = "en-US"):
        """Get TV series credits (cast and crew)."""
        params = {"language": language}
        data = await self.get(f"/tv/{tv_id}/credits", params=params)
        from app.tmdb.models import TMDBCredits
        return TMDBCredits(**data)

    # Keywords methods
    async def get_movie_keywords(self, movie_id: int):
        """Get movie keywords."""
        data = await self.get(f"/movie/{movie_id}/keywords")
        from app.tmdb.models import TMDBKeywords
        return TMDBKeywords(**data)

    async def get_tv_keywords(self, tv_id: int):
        """Get TV series keywords."""
        data = await self.get(f"/tv/{tv_id}/keywords")
        from app.tmdb.models import TMDBKeywords
        return TMDBKeywords(**data)

    # Similar/Recommendations methods
    async def get_movie_similar(
        self, movie_id: int, page: int = 1, language: str = "en-US"
    ):
        """Get movies similar to the given movie."""
        from app.tmdb.models import TMDBSimilarResult, TMDBPaginatedResponse
        params = {"page": page, "language": language}
        data = await self.get(f"/movie/{movie_id}/similar", params=params)
        results = [TMDBSimilarResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    async def get_tv_similar(
        self, tv_id: int, page: int = 1, language: str = "en-US"
    ):
        """Get TV series similar to the given TV series."""
        from app.tmdb.models import TMDBSimilarResult, TMDBPaginatedResponse
        params = {"page": page, "language": language}
        data = await self.get(f"/tv/{tv_id}/similar", params=params)
        results = [TMDBSimilarResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    async def get_movie_recommendations(
        self, movie_id: int, page: int = 1, language: str = "en-US"
    ):
        """Get movie recommendations."""
        from app.tmdb.models import TMDBSimilarResult, TMDBPaginatedResponse
        params = {"page": page, "language": language}
        data = await self.get(f"/movie/{movie_id}/recommendations", params=params)
        results = [TMDBSimilarResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    async def get_tv_recommendations(
        self, tv_id: int, page: int = 1, language: str = "en-US"
    ):
        """Get TV series recommendations."""
        from app.tmdb.models import TMDBSimilarResult, TMDBPaginatedResponse
        params = {"page": page, "language": language}
        data = await self.get(f"/tv/{tv_id}/recommendations", params=params)
        results = [TMDBSimilarResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    # Discover methods
    async def discover_movies(
        self,
        page: int = 1,
        language: str = "en-US",
        sort_by: str = "popularity.desc",
        with_genres: Optional[str] = None,
        with_keywords: Optional[str] = None,
        with_original_language: Optional[str] = None,
        with_origin_country: Optional[str] = None,
        vote_average_gte: Optional[float] = None,
        vote_count_gte: Optional[int] = None,
        release_date_gte: Optional[str] = None,
        release_date_lte: Optional[str] = None,
    ):
        """Discover movies with filters."""
        from app.tmdb.models import TMDBDiscoverResult, TMDBPaginatedResponse
        params = {
            "page": page,
            "language": language,
            "sort_by": sort_by,
        }
        if with_genres:
            params["with_genres"] = with_genres
        if with_keywords:
            params["with_keywords"] = with_keywords
        if with_original_language:
            params["with_original_language"] = with_original_language
        if with_origin_country:
            params["with_origin_country"] = with_origin_country
        if vote_average_gte is not None:
            params["vote_average.gte"] = vote_average_gte
        if vote_count_gte is not None:
            params["vote_count.gte"] = vote_count_gte
        if release_date_gte:
            params["release_date.gte"] = release_date_gte
        if release_date_lte:
            params["release_date.lte"] = release_date_lte
        data = await self.get("/discover/movie", params=params)
        results = [TMDBDiscoverResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    async def discover_tv(
        self,
        page: int = 1,
        language: str = "en-US",
        sort_by: str = "popularity.desc",
        with_genres: Optional[str] = None,
        with_keywords: Optional[str] = None,
        with_original_language: Optional[str] = None,
        with_origin_country: Optional[str] = None,
        vote_average_gte: Optional[float] = None,
        vote_count_gte: Optional[int] = None,
        first_air_date_gte: Optional[str] = None,
        first_air_date_lte: Optional[str] = None,
    ):
        """Discover TV series with filters."""
        from app.tmdb.models import TMDBDiscoverResult, TMDBPaginatedResponse
        params = {
            "page": page,
            "language": language,
            "sort_by": sort_by,
        }
        if with_genres:
            params["with_genres"] = with_genres
        if with_keywords:
            params["with_keywords"] = with_keywords
        if with_original_language:
            params["with_original_language"] = with_original_language
        if with_origin_country:
            params["with_origin_country"] = with_origin_country
        if vote_average_gte is not None:
            params["vote_average.gte"] = vote_average_gte
        if vote_count_gte is not None:
            params["vote_count.gte"] = vote_count_gte
        if first_air_date_gte:
            params["first_air_date.gte"] = first_air_date_gte
        if first_air_date_lte:
            params["first_air_date.lte"] = first_air_date_lte
        data = await self.get("/discover/tv", params=params)
        results = [TMDBDiscoverResult(**item) for item in data.get("results", [])]
        data["results"] = results
        return TMDBPaginatedResponse(**data)

    # Image URL helpers
    def get_poster_url(self, poster_path: Optional[str], size: str = "w342") -> Optional[str]:
        """
        Build full poster URL from path.

        Common poster sizes: w92, w154, w185, w342, w500, w780, original
        """
        if not poster_path or not self._image_config:
            return None
        base = self._image_config.images.secure_base_url
        return f"{base}{size}{poster_path}"

    def get_backdrop_url(self, backdrop_path: Optional[str], size: str = "w780") -> Optional[str]:
        """
        Build full backdrop URL from path.

        Common backdrop sizes: w300, w780, w1280, original
        """
        if not backdrop_path or not self._image_config:
            return None
        base = self._image_config.images.secure_base_url
        return f"{base}{size}{backdrop_path}"

    def get_profile_url(self, profile_path: Optional[str], size: str = "w185") -> Optional[str]:
        """
        Build full profile URL from path.

        Common profile sizes: w45, w185, h632, original
        """
        if not profile_path or not self._image_config:
            return None
        base = self._image_config.images.secure_base_url
        return f"{base}{size}{profile_path}"


# Global client instance for FastAPI lifespan management
_tmdb_client: Optional[TMDBClient] = None


def get_tmdb_client() -> TMDBClient:
    """Get the global TMDB client instance."""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = TMDBClient(
            access_token=settings.tmdb_access_token,
            base_url=settings.tmdb_base_url,
            enable_doh_fallback=settings.tmdb_enable_doh_fallback,
        )
    return _tmdb_client


async def init_tmdb_client() -> None:
    """Initialize global TMDB client (for lifespan)."""
    global _tmdb_client
    _tmdb_client = TMDBClient(
        access_token=settings.tmdb_access_token,
        base_url=settings.tmdb_base_url,
        enable_doh_fallback=settings.tmdb_enable_doh_fallback,
    )
    await _tmdb_client.start()


async def close_tmdb_client() -> None:
    """Close global TMDB client (for lifespan)."""
    global _tmdb_client
    if _tmdb_client:
        await _tmdb_client.close()
        _tmdb_client = None