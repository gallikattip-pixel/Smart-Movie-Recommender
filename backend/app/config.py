"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # TMDB API Configuration
    # Use "Access Token (v4 auth)" for TMDB_ACCESS_TOKEN
    tmdb_access_token: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # Set to True only in restricted local environments where ISP DNS poisons api.themoviedb.org without a VPN.
    # Default is False: in production, standard HTTPS and system DNS resolution are used.
    tmdb_enable_doh_fallback: bool = False

    # Backend Configuration
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # CORS
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins supporting comma-separated list or single frontend_url."""
        origins = [self.frontend_url.strip()] if self.frontend_url else []
        if self.allowed_origins:
            for o in self.allowed_origins.split(","):
                o = o.strip()
                if o and o not in origins:
                    origins.append(o)
        return origins

    @property
    def has_tmdb_credentials(self) -> bool:
        """Check if TMDB credentials are configured."""
        return bool(self.tmdb_access_token)


settings = Settings()