/** Recommendations component for generating and displaying personalized recommendations. */

import { useState, useEffect, useCallback, FormEvent, ChangeEvent } from "react";
import { Link } from "react-router-dom";
import {
  getRecommendationsFromFavorites,
  type RecommendResponse,
  type RecommendRequest,
} from "../services/recommend";
import { getFavorites } from "../services/favorites";
import type { MediaDetailsResponse } from "../types/details";
import {
  type UserPreference,
  ALL_GENRES,
  COMMON_LANGUAGES,
  COMMON_COUNTRIES,
  type EraRange,
} from "../types/recommend";
import { toggleFeedback, hasFeedback, getFeedbackLabel, getFeedbackColor, getFeedbackIcon, type FeedbackType } from "../services/feedback";

const DEFAULT_PREFERENCES: UserPreference = {
  favorite_titles: [],
  preferred_genres: [],
  excluded_genres: [],
  preferred_languages: [],
  excluded_languages: [],
  preferred_countries: [],
  excluded_countries: [],
  content_types: ["movie", "tv"],
  era: null,
  min_vote_average: null,
  preferred_themes: [],
  excluded_themes: [],
  preferred_moods: [],
  excluded_moods: [],
  preferred_pacing: [],
  preferred_endings: [],
  prefer_hidden_gems: false,
  prefer_similar: true,
};

interface RecommendationItem {
  media: MediaDetailsResponse;
  similarity_score: number;
  preference_score: number;
  final_score: number;
  explanation: Array<{ type: string; description: string; weight: number }>;
  graph_path: number[] | null;
}

export function Recommendations() {
  const [preferences, setPreferences] = useState<UserPreference>(DEFAULT_PREFERENCES);
  const [limit, setLimit] = useState(20);
  const [excludeFavorites, setExcludeFavorites] = useState(true);
  const [includeExplanations, setIncludeExplanations] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RecommendResponse | null>(null);

  // Load favorites on mount
  useEffect(() => {
    const storedFavorites = getFavorites();
    setPreferences((prev) => ({ ...prev, favorite_titles: storedFavorites }));
  }, []);

  const handleGenreToggle = useCallback((genreId: string | number, list: "preferred" | "excluded") => {
    const id = typeof genreId === "string" ? parseInt(genreId, 10) : genreId;
    setPreferences((prev) => {
      const preferred = list === "preferred" ? prev.preferred_genres : prev.excluded_genres;
      const excluded = list === "excluded" ? prev.excluded_genres : prev.preferred_genres;
      const newPreferred = preferred.includes(id)
        ? preferred.filter((g) => g !== id)
        : [...preferred, id];
      const newExcluded = excluded.filter((g) => g !== id);
      return {
        ...prev,
        preferred_genres: list === "preferred" ? newPreferred : newExcluded,
        excluded_genres: list === "excluded" ? newPreferred : newExcluded,
      };
    });
  }, []);

  const handleLanguageToggle = useCallback((langCode: string | number, list: "preferred" | "excluded") => {
    const id = String(langCode);
    setPreferences((prev) => {
      const preferred = list === "preferred" ? prev.preferred_languages : prev.excluded_languages;
      const excluded = list === "excluded" ? prev.excluded_languages : prev.preferred_languages;
      const newPreferred = preferred.includes(id)
        ? preferred.filter((l) => l !== id)
        : [...preferred, id];
      const newExcluded = excluded.filter((l) => l !== id);
      return {
        ...prev,
        preferred_languages: list === "preferred" ? newPreferred : newExcluded,
        excluded_languages: list === "excluded" ? newPreferred : newExcluded,
      };
    });
  }, []);

  const handleCountryToggle = useCallback((countryCode: string | number, list: "preferred" | "excluded") => {
    const id = String(countryCode);
    setPreferences((prev) => {
      const preferred = list === "preferred" ? prev.preferred_countries : prev.excluded_countries;
      const excluded = list === "excluded" ? prev.excluded_countries : prev.preferred_countries;
      const newPreferred = preferred.includes(id)
        ? preferred.filter((c) => c !== id)
        : [...preferred, id];
      const newExcluded = excluded.filter((c) => c !== id);
      return {
        ...prev,
        preferred_countries: list === "preferred" ? newPreferred : newExcluded,
        excluded_countries: list === "excluded" ? newPreferred : newExcluded,
      };
    });
  }, []);

  const handleContentTypeToggle = useCallback((type: "movie" | "tv") => {
    setPreferences((prev) => ({
      ...prev,
      content_types: prev.content_types.includes(type)
        ? prev.content_types.filter((t) => t !== type)
        : [...prev.content_types, type],
    }));
  }, []);

  const handleEraChange = useCallback((field: "start_year" | "end_year", value: string) => {
    setPreferences((prev) => {
      const era: EraRange = prev.era || {};
      const numValue = value ? parseInt(value, 10) : undefined;
      if (numValue && (numValue < 1900 || numValue > 2100)) return prev;
      return { ...prev, era: { ...era, [field]: numValue } };
    });
  }, []);

  const handleMinVoteChange = useCallback((value: string) => {
    const num = value ? parseFloat(value) : null;
    if (num !== null && (num < 0 || num > 10)) return;
    setPreferences((prev) => ({ ...prev, min_vote_average: num }));
  }, []);

  const handleHiddenGemsToggle = useCallback(() => {
    setPreferences((prev) => ({ ...prev, prefer_hidden_gems: !prev.prefer_hidden_gems }));
  }, []);

  const handlePreferSimilarToggle = useCallback(() => {
    setPreferences((prev) => ({ ...prev, prefer_similar: !prev.prefer_similar }));
  }, []);

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const _request: RecommendRequest = {
      preferences: {
        ...preferences,
        favorite_titles: preferences.favorite_titles,
      },
      limit,
      algorithm: "hybrid" as const,
      exclude_favorites: excludeFavorites,
      include_explanations: includeExplanations,
    };
    void _request;

    try {
      const data = await getRecommendationsFromFavorites(
        preferences.favorite_titles,
        limit,
        "hybrid"
      );
      setResponse(data);
    } catch (err) {
      const error = err as Error & { status?: number; code?: string };
      let errorMessage = error.message || "Failed to get recommendations";

      if (error.status === 503 && error.code === "TMDB_NOT_CONFIGURED") {
        errorMessage = "Recommendation service is not configured. Please contact support.";
      } else if (error.status === 401) {
        errorMessage = "Authentication failed. Please try again later.";
      } else if (error.status === 429) {
        errorMessage = "Too many requests. Please wait a moment and try again.";
      } else if (error.status === 502) {
        errorMessage = "Service temporarily unavailable. Please try again later.";
      } else if (error.status === 504) {
        errorMessage = "Request timed out. Please try again.";
      } else if (error.status === 400) {
        errorMessage = error.message;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [preferences, limit, excludeFavorites, includeExplanations]);

  const handleFeedback = useCallback(
    (mediaType: "movie" | "tv", itemId: number, type: FeedbackType) => {
      toggleFeedback(mediaType, itemId, type);
      setResponse((prev) => (prev ? { ...prev } : null));
    },
    []
  );

  const canSubmit = preferences.favorite_titles.length > 0;

  const renderToggleChips = <T extends { id: string | number; label: string; code?: string }>(
    items: T[],
    preferred: string[],
    excluded: string[],
    onToggle: (id: string | number, list: "preferred" | "excluded") => void,
    getId: (item: T) => string | number
  ) => {
    return items.map((item) => {
      const id = getId(item);
      const isPreferred = preferred.includes(String(id));
      const isExcluded = excluded.includes(String(id));
      let variant: "toggle-chip-selected" | "toggle-chip-excluded" | "toggle-chip-default" = "toggle-chip-default";
      if (isPreferred) variant = "toggle-chip-selected";
      else if (isExcluded) variant = "toggle-chip-excluded";

      return (
        <button
          key={item.id}
          type="button"
          onClick={() => onToggle(id, isExcluded ? "preferred" : isPreferred ? "excluded" : "preferred")}
          className={`toggle-chip ${variant}`}
          aria-pressed={isPreferred || isExcluded}
        >
          <span className="flex items-center justify-between w-full">
            <span>{item.label} {item.code ? `(${item.code})` : ""}</span>
            {isPreferred && <span className="text-green-600 ml-1">✓</span>}
            {isExcluded && <span className="text-red-600 ml-1">✗</span>}
          </span>
        </button>
      );
    });
  };

  return (
    <section className="section page-transition" aria-labelledby="recommendations-heading">
      <header className="page-header">
        <h2 id="recommendations-heading" className="text-2xl font-bold text-surface-900">Get Recommendations</h2>
        <p className="text-sm text-surface-500">Configure your preferences to generate personalized movie and TV recommendations</p>
      </header>

      {/* Error State */}
      {error && (
        <div className="error-state mb-8" role="alert">
          <p className="font-medium">Failed to generate recommendations</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {/* Preferences Form */}
      <form onSubmit={handleSubmit} className="form-section mb-8">
        {/* Favorites Summary */}
        {preferences.favorite_titles.length > 0 && (
          <div className="p-4 bg-brand-50 border border-brand-200 rounded-lg">
            <h3 className="text-sm font-medium text-brand-800 mb-2 flex items-center gap-2">
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
              Favorites ({preferences.favorite_titles.length})
            </h3>
            <div className="flex flex-wrap gap-2">
              {preferences.favorite_titles.slice(0, 5).map((fav) => (
                <span key={`${fav.media_type}-${fav.item_id}`} className="px-2 py-1 bg-brand-100 text-brand-700 text-xs rounded">
                  {fav.media_type}#{fav.item_id}
                </span>
              ))}
              {preferences.favorite_titles.length > 5 && (
                <span className="px-2 py-1 bg-surface-100 text-surface-600 text-xs rounded">
                  +{preferences.favorite_titles.length - 5} more
                </span>
              )}
            </div>
            <p className="text-xs text-brand-600 mt-2">Manage favorites in the <Link to="/favorites" className="link">Favorites</Link> page.</p>
          </div>
        )}

        {/* Genres */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="form-label">Genres</h3>
            <button type="button" onClick={() => setPreferences((p) => ({ ...p, preferred_genres: [], excluded_genres: [] }))} className="btn-ghost text-xs">
              Clear all
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {renderToggleChips(
              ALL_GENRES.map(g => ({ id: g.id, label: g.name })),
              preferences.preferred_genres.map(String),
              preferences.excluded_genres.map(String),
              handleGenreToggle,
              (item) => item.id
            )}
          </div>
        </div>

        {/* Languages */}
        <div>
          <h3 className="form-label mb-3">Languages</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {renderToggleChips(
              COMMON_LANGUAGES.map(l => ({ id: l.code, label: l.name, code: l.code })),
              preferences.preferred_languages,
              preferences.excluded_languages,
              handleLanguageToggle,
              (item) => item.id
            )}
          </div>
        </div>

        {/* Countries */}
        <div>
          <h3 className="form-label mb-3">Production Countries</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {renderToggleChips(
              COMMON_COUNTRIES.map(c => ({ id: c.code, label: c.name, code: c.code })),
              preferences.preferred_countries,
              preferences.excluded_countries,
              handleCountryToggle,
              (item) => item.id
            )}
          </div>
        </div>

        {/* Content Types */}
        <div>
          <h3 className="form-label mb-3">Content Types</h3>
          <div className="flex gap-4">
            {["movie", "tv"].map((type) => (
              <label key={type} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.content_types.includes(type as "movie" | "tv")}
                  onChange={() => handleContentTypeToggle(type as "movie" | "tv")}
                  className="w-4 h-4 text-brand-600 border-surface-300 rounded focus:ring-brand-500"
                />
                <span className="capitalize text-sm text-surface-700">{type === "movie" ? "Movies" : "TV Series"}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Release Era */}
        <div>
          <h3 className="form-label mb-3">Release Era</h3>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label htmlFor="era-start" className="block text-sm text-surface-600 mb-1">Start Year</label>
              <input
                id="era-start"
                type="number"
                min="1900"
                max="2100"
                value={preferences.era?.start_year || ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleEraChange("start_year", e.target.value)}
                className="input-field"
                placeholder="e.g., 2000"
              />
            </div>
            <div className="flex-1">
              <label htmlFor="era-end" className="block text-sm text-surface-600 mb-1">End Year</label>
              <input
                id="era-end"
                type="number"
                min="1900"
                max="2100"
                value={preferences.era?.end_year || ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleEraChange("end_year", e.target.value)}
                className="input-field"
                placeholder="e.g., 2024"
              />
            </div>
          </div>
        </div>

        {/* Minimum Rating */}
        <div>
          <h3 className="form-label mb-3">Minimum TMDB Rating</h3>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            value={preferences.min_vote_average || ""}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleMinVoteChange(e.target.value)}
            className="input-field max-w-xs"
            placeholder="e.g., 7.0"
          />
        </div>

        {/* Discovery Options */}
        <div className="divider">
          <h3 className="form-label mb-4">Discovery Options</h3>
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.prefer_hidden_gems}
                onChange={handleHiddenGemsToggle}
                className="w-4 h-4 text-brand-600 border-surface-300 rounded focus:ring-brand-500"
              />
              <div>
                <p className="text-sm font-medium text-surface-900">Prefer hidden gems</p>
                <p className="text-xs text-surface-500">Prioritize less popular titles you might have missed</p>
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.prefer_similar}
                onChange={handlePreferSimilarToggle}
                className="w-4 h-4 text-brand-600 border-surface-300 rounded focus:ring-brand-500"
              />
              <div>
                <p className="text-sm font-medium text-surface-900">Prefer similar to favorites</p>
                <p className="text-xs text-surface-500">Find titles similar to your favorites vs. new discoveries</p>
              </div>
            </label>
          </div>
        </div>

        {/* Other Options */}
        <div className="divider space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={excludeFavorites}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setExcludeFavorites(e.target.checked)}
              className="w-4 h-4 text-brand-600 border-surface-300 rounded focus:ring-brand-500"
            />
            <span className="text-sm text-surface-700">Exclude favorite titles from recommendations</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeExplanations}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setIncludeExplanations(e.target.checked)}
              className="w-4 h-4 text-brand-600 border-surface-300 rounded focus:ring-brand-500"
            />
            <span className="text-sm text-surface-700">Include explanations for each recommendation</span>
          </label>
          <div>
            <label htmlFor="limit" className="form-label mb-1">Number of Results</label>
            <input
              id="limit"
              type="number"
              min="1"
              max="50"
              value={limit}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setLimit(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
              className="input-field max-w-xs"
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-4 divider">
          <button
            type="submit"
            disabled={loading || !canSubmit}
            className="btn-primary w-full sm:w-auto"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Generating…
              </span>
            ) : (
              "Get Recommendations"
            )}
          </button>
          {!canSubmit && (
            <p className="mt-2 text-sm text-surface-500">Add at least one favorite on the <Link to="/favorites" className="link">Favorites</Link> page to get recommendations.</p>
          )}
        </div>
      </form>

      {/* Results */}
      {response && !loading && (
        <div className="divider">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h3 className="text-lg font-medium text-surface-900">Recommendations</h3>
              <p className="text-sm text-surface-500">
                {response.total_candidates_considered} candidates considered •
                {response.total_excluded} excluded •
                {response.search_time_ms.toFixed(1)}ms
              </p>
            </div>
          </div>

          {response.recommendations.length > 0 ? (
            <div className="results-grid" role="list" aria-label="Recommended movies and TV series">
              {response.recommendations.map((rec: RecommendationItem, index) => (
                <RecommendationCard
                  key={`${rec.media.media_type}-${rec.media.id}`}
                  recommendation={rec}
                  onFeedback={handleFeedback}
                  index={index}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state" role="status">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3>No recommendations found</h3>
              <p className="mt-1">Try adjusting your preferences or adding more favorites</p>
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!response && !loading && !error && (
        <div className="empty-state divider" role="status">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h3>Configure preferences and click "Get Recommendations"</h3>
          <p className="mt-1 text-sm">Start by adding favorites, then customize your preferences above</p>
        </div>
      )}
    </section>
  );
}

interface RecommendationCardProps {
  recommendation: RecommendationItem;
  onFeedback: (mediaType: "movie" | "tv", itemId: number, type: FeedbackType) => void;
  index: number;
}

function RecommendationCard({ recommendation, onFeedback, index }: RecommendationCardProps) {
  const { media, final_score, explanation, graph_path } = recommendation;
  const mediaTypeLabel = media.media_type === "movie" ? "Movie" : "TV Series";
  const releaseYear = media.media_type === "movie" && media.release_date
    ? new Date(media.release_date).getFullYear()
    : media.media_type === "tv" && media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : "Unknown";

  const feedbackTypes: FeedbackType[] = ["like", "dislike", "watched", "more_like_this"];

  return (
    <article
      className="card-interactive card-enter"
      style={{ animationDelay: `${index * 50}ms` }}
      role="listitem"
    >
      <Link to={`/${media.media_type}/${media.id}`} className="block" aria-label={`${media.title} — view details`}>
        {media.poster_url ? (
          <img
            src={media.poster_url}
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
          <h3 className="font-medium text-surface-900 line-clamp-2 mb-1">{media.title}</h3>
          <div className="flex items-center gap-2 text-sm text-surface-500 mb-2">
            <span className="badge badge-gray capitalize">{mediaTypeLabel}</span>
            <span aria-hidden="true">•</span>
            <span>{releaseYear}</span>
          </div>
          {media.vote_average !== null && media.vote_average > 0 && (
            <div className="flex items-center gap-1 text-sm text-brand-600 mb-2">
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
              <span>{media.vote_average.toFixed(1)}</span>
              <span className="text-surface-400">({media.vote_count.toLocaleString()})</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-xs text-surface-500 mb-2">
            <span className="px-2 py-0.5 bg-brand-100 text-brand-700 rounded">Match: {(final_score * 100).toFixed(0)}%</span>
          </div>
        </div>
      </Link>

      {/* Explanation */}
      {explanation.length > 0 && (
        <div className="px-4 pb-4 border-t border-surface-200">
          <p className="text-xs text-surface-500 mb-1">Why this was recommended:</p>
          <div className="flex flex-wrap gap-1">
            {explanation.slice(0, 3).map((reason: { type: string; description: string; weight: number }, idx: number) => (
              <span key={idx} className="px-2 py-0.5 bg-surface-100 text-surface-700 rounded text-xs">
                {reason.description}
              </span>
            ))}
            {explanation.length > 3 && (
              <span className="px-2 py-0.5 bg-surface-100 text-surface-500 rounded text-xs">
                +{explanation.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Graph Path */}
      {graph_path && graph_path.length > 1 && (
        <div className="px-4 pb-4 border-t border-surface-200">
          <p className="text-xs text-surface-500 mb-1">Connection path:</p>
          <div className="flex items-center gap-1 text-xs text-surface-600 flex-wrap">
            {graph_path.map((id: number, idx: number) => (
              <span key={idx} className="flex items-center gap-1">
                #{id}{idx < graph_path.length - 1 && <span className="text-surface-300">→</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Feedback Buttons */}
      <div className="px-4 pb-4 pt-0 border-t border-surface-200">
        <div className="flex flex-wrap gap-1">
          {feedbackTypes.map((type: FeedbackType) => {
            const isActive = hasFeedback(media.media_type, media.id, type);
            return (
              <button
                key={type}
                type="button"
                onClick={() => onFeedback(media.media_type, media.id, type)}
                className={`feedback-btn ${getFeedbackColor(type, isActive)} ${isActive ? "feedback-btn-active" : ""}`}
                title={getFeedbackLabel(type)}
                aria-label={getFeedbackLabel(type)}
                aria-pressed={isActive}
              >
                {getFeedbackIcon(type, isActive)}
                <span className="hidden sm:inline">{getFeedbackLabel(type)}</span>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-surface-400 mt-2 text-center">Feedback is stored locally and does not affect recommendations.</p>
      </div>
    </article>
  );
}