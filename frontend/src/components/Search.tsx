/** Search component with loading, error, and results states. */

import { useState, useCallback, FormEvent, ChangeEvent } from "react";
import { Link } from "react-router-dom";
import type { SearchType, SearchState, SearchResultItem } from "../types/search";
import { searchMedia, getDisplayTitle, getReleaseYear } from "../services/search";
import { isFavorite, toggleFavorite } from "../services/favorites";

const SEARCH_TYPES: { value: SearchType; label: string }[] = [
  { value: "multi", label: "All" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV Series" },
];

export function Search() {
  const [state, setState] = useState<SearchState>({
    query: "",
    type: "multi",
    page: 1,
    loading: false,
    error: null,
    results: [],
    total_pages: 0,
    total_results: 0,
    hasSearched: false,
  });

  // Track favorite status for each result
  const [favoriteStatus, setFavoriteStatus] = useState<Record<string, boolean>>({});

  const handleQueryChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setState((prev) => ({ ...prev, query: e.target.value }));
  }, []);

  const handleTypeChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setState((prev) => ({ ...prev, type: e.target.value as SearchType, page: 1 }));
  }, []);

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    const trimmedQuery = state.query.trim();
    if (!trimmedQuery) return;

    setState((prev) => ({
      ...prev,
      loading: true,
      error: null,
      page: 1,
      hasSearched: true,
    }));

    try {
      const response = await searchMedia({
        query: trimmedQuery,
        type: state.type,
        page: 1,
      });

      // Update favorite status for new results
      const newFavoriteStatus: Record<string, boolean> = {};
      response.results.forEach((item) => {
        const key = `${item.media_type}-${item.id}`;
        newFavoriteStatus[key] = isFavorite(item.media_type, item.id);
      });

      setState((prev) => ({
        ...prev,
        loading: false,
        results: response.results,
        total_pages: response.total_pages,
        total_results: response.total_results,
      }));
      setFavoriteStatus(newFavoriteStatus);
    } catch (err) {
      const error = err as Error & { status?: number; code?: string };
      let errorMessage = error.message || "Search failed";

      if (error.status === 503 && error.code === "TMDB_NOT_CONFIGURED") {
        errorMessage = "Search service is not configured. Please contact support.";
      } else if (error.status === 503) {
        errorMessage = "Unable to reach the movie database (TMDB). Please check your network connection or try again later.";
      } else if (error.status === 401) {
        errorMessage = "Authentication failed. Please try again later.";
      } else if (error.status === 429) {
        errorMessage = "Too many requests. Please wait a moment and try again.";
      } else if (error.status === 502) {
        errorMessage = "Search service temporarily unavailable. Please try again later.";
      } else if (error.status === 504) {
        errorMessage = "Search request timed out. The movie database may be unreachable — please check your network and try again.";
      } else if (error.status === 400) {
        errorMessage = error.message;
      }

      setState((prev) => ({
        ...prev,
        loading: false,
        error: errorMessage,
        results: [],
      }));
      setFavoriteStatus({});
    }
  }, [state.query, state.type]);

  const handlePageChange = useCallback(async (newPage: number) => {
    if (newPage < 1 || newPage > state.total_pages || state.loading) return;

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await searchMedia({
        query: state.query.trim(),
        type: state.type,
        page: newPage,
      });

      // Update favorite status for new results
      const newFavoriteStatus: Record<string, boolean> = {};
      response.results.forEach((item) => {
        const key = `${item.media_type}-${item.id}`;
        newFavoriteStatus[key] = isFavorite(item.media_type, item.id);
      });

      setState((prev) => ({
        ...prev,
        loading: false,
        page: newPage,
        results: response.results,
      }));
      setFavoriteStatus(newFavoriteStatus);
    } catch (err) {
      const error = err as Error;
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error.message || "Failed to load page",
      }));
    }
  }, [state.query, state.type, state.total_pages, state.loading]);

  const handleFavoriteToggle = useCallback((item: SearchResultItem) => {
    toggleFavorite({ media_type: item.media_type, item_id: item.id });
    setFavoriteStatus((prev) => ({
      ...prev,
      [`${item.media_type}-${item.id}`]: !prev[`${item.media_type}-${item.id}`],
    }));
  }, []);

  return (
    <section className="section page-transition" aria-labelledby="search-heading">
      <header className="page-header">
        <h2 id="search-heading" className="text-2xl font-bold text-surface-900">Search Movies & TV Series</h2>
        <p className="text-sm text-surface-500">Find titles to add to your favorites or explore directly</p>
      </header>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label htmlFor="search-query" className="sr-only">Search query</label>
            <input
              id="search-query"
              type="text"
              value={state.query}
              onChange={handleQueryChange}
              placeholder="Enter a movie or TV series title…"
              className="input-field"
              disabled={state.loading}
              autoComplete="off"
              aria-describedby="search-hint"
            />
            <p id="search-hint" className="form-hint">Press Enter to search</p>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="search-type" className="sr-only">Search type</label>
            <select
              id="search-type"
              value={state.type}
              onChange={handleTypeChange}
              className="select-field min-w-[140px]"
              disabled={state.loading}
            >
              {SEARCH_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={state.loading || !state.query.trim()}
              className="btn-primary whitespace-nowrap"
              aria-label={state.loading ? "Searching…" : "Search"}
            >
              {state.loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Searching…
                </span>
              ) : (
                "Search"
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Error State */}
      {state.error && (
        <div className="error-state mb-8" role="alert">
          <p className="font-medium">Search failed</p>
          <p className="mt-1 text-sm">{state.error}</p>
        </div>
      )}

      {/* Results */}
      {state.hasSearched && !state.loading && !state.error && (
        <>
          <div className="mb-6 text-sm text-surface-600">
            {state.total_results > 0 ? (
              <>
                Showing <strong>{state.results.length}</strong> of <strong>{state.total_results}</strong> result{state.total_results !== 1 ? "s" : ""} for{" "}
                <span className="font-medium">"{state.query}"</span>{" "}
                ({SEARCH_TYPES.find((t) => t.value === state.type)?.label})
              </>
            ) : (
              <>
                No results found for <span className="font-medium">"{state.query}"</span>
              </>
            )}
          </div>

          {state.results.length > 0 && (
            <div className="results-grid" role="list" aria-label="Search results">
              {state.results.map((item, index) => {
                const key = `${item.media_type}-${item.id}`;
                const isFav = favoriteStatus[key] || false;

                return (
                  <article
                    key={key}
                    className="card-interactive card-enter"
                    style={{ animationDelay: `${index * 50}ms` }}
                    role="listitem"
                  >
                    <Link to={`/${item.media_type}/${item.id}`} className="block" aria-label={`${getDisplayTitle(item)} — view details`}>
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

                      <div className="p-4 relative">
                        {/* Favorite button */}
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleFavoriteToggle(item);
                          }}
                          className={`favorite-btn absolute top-3 right-3 ${isFav ? "favorite-btn-active" : "favorite-btn-inactive"}`}
                          aria-label={isFav ? `Remove "${getDisplayTitle(item)}" from favorites` : `Add "${getDisplayTitle(item)}" to favorites`}
                          aria-pressed={isFav}
                        >
                          <svg className="w-5 h-5" fill={isFav ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                          </svg>
                        </button>

                        <h3 className="font-medium text-surface-900 line-clamp-2 mb-1 pr-12">{getDisplayTitle(item)}</h3>
                        <div className="flex items-center gap-2 text-sm text-surface-500 mb-2">
                          <span className="badge badge-gray capitalize">{item.media_type}</span>
                          <span aria-hidden="true">•</span>
                          <span>{getReleaseYear(item)}</span>
                        </div>
                        {item.vote_average !== null && item.vote_average > 0 && (
                          <div className="flex items-center gap-1 text-sm text-brand-600 mb-2">
                            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                            <span>{item.vote_average.toFixed(1)}</span>
                            <span className="text-surface-400">({item.vote_count.toLocaleString()})</span>
                          </div>
                        )}
                        {item.overview && (
                          <p className="text-sm text-surface-600 line-clamp-3">{item.overview}</p>
                        )}
                        {!item.overview && (
                          <p className="text-sm text-surface-400 italic">No overview available</p>
                        )}
                      </div>
                    </Link>
                  </article>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {state.total_pages > 1 && (
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={() => handlePageChange(state.page - 1)}
                disabled={state.page === 1 || state.loading}
                className="btn-secondary"
                aria-label="Previous page"
              >
                Previous
              </button>
              <span className="flex items-center px-4 text-sm text-surface-600" aria-live="polite">
                Page {state.page} of {state.total_pages}
              </span>
              <button
                onClick={() => handlePageChange(state.page + 1)}
                disabled={state.page >= state.total_pages || state.loading}
                className="btn-secondary"
                aria-label="Next page"
              >
                Next
              </button>
            </div>
          )}

          {/* Empty State */}
          {state.results.length === 0 && state.total_results === 0 && !state.error && (
            <div className="empty-state" role="status">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3>No results found</h3>
              <p className="mt-1">Try a different search term or search type</p>
            </div>
          )}
        </>
      )}

      {/* Initial State */}
      {!state.hasSearched && !state.loading && !state.error && (
        <div className="empty-state" role="status">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3>Search for movies and TV series</h3>
          <p className="mt-1 text-sm">Enter a title above to get started</p>
        </div>
      )}
    </section>
  );
}