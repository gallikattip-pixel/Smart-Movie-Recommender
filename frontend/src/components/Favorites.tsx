/** Favorites component for managing user's favorite movies/TV series. */

import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { getFavorites, removeFavorite, clearFavorites } from "../services/favorites";
import { resolveFavorites } from "../services/details";
import type { FavoriteTitleRequest, MediaDetailsResponse } from "../types/details";

export function Favorites() {
  const [favorites, setFavorites] = useState<FavoriteTitleRequest[]>([]);
  const [resolved, setResolved] = useState<MediaDetailsResponse[]>([]);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFavorites = useCallback(() => {
    const stored = getFavorites();
    setFavorites(stored);
  }, []);

  const resolveAll = useCallback(async () => {
    if (favorites.length === 0) return;

    setResolving(true);
    setError(null);
    try {
      const response = await resolveFavorites({ titles: favorites });
      setResolved(response.resolved);
      if (response.failed.length > 0) {
        setError(
          `${response.failed.length} favorite(s) could not be loaded`
        );
      }
    } catch (err) {
      const error = err as Error & { status?: number };
      setError(error.message || "Failed to load favorite details");
    } finally {
      setResolving(false);
    }
  }, [favorites]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  useEffect(() => {
    if (favorites.length > 0) {
      resolveAll();
    } else {
      setResolved([]);
    }
  }, [favorites, resolveAll]);

  const handleRemove = useCallback((mediaType: "movie" | "tv", itemId: number) => {
    removeFavorite(mediaType, itemId);
    loadFavorites();
  }, [loadFavorites]);

  const handleClear = useCallback(() => {
    clearFavorites();
    loadFavorites();
    setResolved([]);
  }, [loadFavorites]);

  const getMediaTypeLabel = (type: "movie" | "tv") => type === "movie" ? "Movie" : "TV Series";

  return (
    <section className="section page-transition" aria-labelledby="favorites-heading">
      {/* Header */}
      <header className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 id="favorites-heading" className="text-2xl font-bold text-surface-900">Your Favorites</h2>
          <p className="text-sm text-surface-500">{favorites.length} favorite{favorites.length !== 1 ? "s" : ""} saved</p>
        </div>
        <div className="flex items-center gap-2">
          {favorites.length > 0 && !resolving && (
            <button
              onClick={resolveAll}
              disabled={resolving}
              className="btn-secondary"
            >
              Refresh Details
            </button>
          )}
          {favorites.length > 0 && (
            <button
              onClick={handleClear}
              className="btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              Clear All
            </button>
          )}
        </div>
      </header>

      {/* Error */}
      {error && (
        <div className="error-state mb-6" role="alert">
          {error}
        </div>
      )}

      {/* Empty State */}
      {favorites.length === 0 && !resolving && (
        <div className="empty-state" role="status">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <h3>No favorites yet</h3>
          <p className="mt-1">Search for movies or TV series and click the heart icon to add them here</p>
          <Link to="/" className="mt-4 inline-block link">
            Start searching
          </Link>
        </div>
      )}

      {/* Resolving State */}
      {resolving && favorites.length > 0 && resolved.length === 0 && (
        <div className="loading-state" role="status" aria-label="Loading favorite details">
          <svg className="loading-spinner" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="ml-3">Loading favorite details…</span>
        </div>
      )}

      {/* Favorites Grid */}
      {resolved.length > 0 && (
        <div className="results-grid" role="list" aria-label="Favorite movies and TV series">
          {resolved.map((item, index) => (
            <article
              key={`${item.media_type}-${item.id}`}
              className="card-interactive card-enter"
              style={{ animationDelay: `${index * 50}ms` }}
              role="listitem"
            >
              <Link to={`/${item.media_type}/${item.id}`} className="block" aria-label={`${item.title} — view details`}>
                {item.poster_url ? (
                  <img
                    src={item.poster_url}
                    alt=""
                    className="poster-img"
                    loading="lazy"
                    aria-hidden="true"
                  />
                ) : (
                  <div className="w-full h-64 bg-surface-200 flex items-center justify-center text-surface-400" aria-hidden="true">
                    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}

                <div className="p-4">
                  <h3 className="font-medium text-surface-900 line-clamp-2 mb-1">{item.title}</h3>
                  <div className="flex items-center gap-2 text-sm text-surface-500 mb-2">
                    <span className="badge badge-gray capitalize">{getMediaTypeLabel(item.media_type)}</span>
                    <span aria-hidden="true">•</span>
                    <span>
                      {item.media_type === "movie" && item.release_date
                        ? new Date(item.release_date).getFullYear()
                        : item.media_type === "tv" && item.first_air_date
                        ? new Date(item.first_air_date).getFullYear()
                        : "Unknown"}
                    </span>
                  </div>
                  {item.vote_average !== null && item.vote_average > 0 && (
                    <div className="flex items-center gap-1 text-sm text-brand-600 mb-2">
                      <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                      <span>{item.vote_average.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              </Link>
              <div className="px-4 pb-4 pt-0 border-t border-surface-200">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleRemove(item.media_type, item.id);
                  }}
                  className="w-full px-3 py-2 text-sm text-red-600 hover:text-red-700 font-medium flex items-center justify-center gap-2 transition-colors rounded-lg hover:bg-red-50"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v10m10-10v10M5 7h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h14z" />
                  </svg>
                  Remove
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}