/** Media details component for displaying detailed movie/TV information. */

import { useEffect, useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import {
  getMediaDetails,
  formatRuntime,
  formatEpisodeRuntime,
  formatReleaseDate,
  getDisplayTitle,
  getMediaTypeLabel,
} from "../services/details";
import { addFavorite, removeFavorite, isFavorite } from "../services/favorites";
import { toggleFeedback, hasFeedback, getFeedbackLabel, getFeedbackColor, getFeedbackIcon, type FeedbackType } from "../services/feedback";
import type { MediaDetailsResponse } from "../types/details";

export function MediaDetails() {
  const params = useParams<{ mediaType?: "movie" | "tv"; itemId: string }>();
  const location = useLocation();
  const [details, setDetails] = useState<MediaDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mediaType: "movie" | "tv" | undefined = params.mediaType || (location.pathname.startsWith("/tv") ? "tv" : location.pathname.startsWith("/movie") ? "movie" : undefined);
  const itemId = params.itemId ? parseInt(params.itemId, 10) : NaN;

  const isFav = mediaType && (mediaType === "movie" || mediaType === "tv") && !isNaN(itemId)
    ? isFavorite(mediaType, itemId)
    : false;

  useEffect(() => {
    if (!mediaType || isNaN(itemId) || (mediaType !== "movie" && mediaType !== "tv")) {
      setError("Invalid media type or ID");
      setLoading(false);
      return;
    }

    const validMediaType = mediaType;

    async function fetchDetails() {
      setLoading(true);
      setError(null);
      try {
        const data = await getMediaDetails(validMediaType, itemId);
        setDetails(data);
      } catch (err) {
        const error = err as Error & { status?: number; code?: string };
        let errorMessage = error.message || "Failed to load details";

        if (error.status === 404) {
          errorMessage = "Movie/TV series not found";
        } else if (error.status === 503 && error.code === "TMDB_NOT_CONFIGURED") {
          errorMessage = "Service is not configured. Please contact support.";
        } else if (error.status === 401) {
          errorMessage = "Authentication failed. Please try again later.";
        } else if (error.status === 429) {
          errorMessage = "Too many requests. Please wait a moment and try again.";
        } else if (error.status === 502) {
          errorMessage = "Service temporarily unavailable. Please try again later.";
        } else if (error.status === 504) {
          errorMessage = "Request timed out. Please try again.";
        }

        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    }

    fetchDetails();
  }, [mediaType, itemId]);

  const handleFavoriteToggle = () => {
    if (!mediaType || isNaN(itemId) || !details) return;

    if (isFav) {
      removeFavorite(mediaType, itemId);
    } else {
      addFavorite({ media_type: mediaType, item_id: itemId });
    }
    setDetails({ ...details! });
  };

  const handleFeedback = (type: FeedbackType) => {
    if (!mediaType || isNaN(itemId) || !details) return;
    toggleFeedback(mediaType, itemId, type);
    setDetails({ ...details! });
  };

  if (loading) {
    return (
      <div className="section loading-state" role="status" aria-label="Loading movie details">
        <svg className="loading-spinner" viewBox="0 0 24 24" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="ml-3 text-sm">Loading details…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="section error-state text-center" role="alert">
        <svg className="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="text-lg font-medium">Failed to load details</p>
        <p className="mt-2 text-sm">{error}</p>
        <Link to="/" className="mt-4 inline-block link">
          ← Back to search
        </Link>
      </div>
    );
  }

  if (!details) {
    return null;
  }

  const mediaTypeLabel = getMediaTypeLabel(details.media_type);
  const releaseInfo = details.media_type === "movie"
    ? details.release_date
    : details.first_air_date;
  const fullReleaseDate = formatReleaseDate(releaseInfo);

  const feedbackTypes: FeedbackType[] = ["like", "dislike", "watched", "more_like_this"];

  return (
    <article className="section page-transition" aria-labelledby="media-title">
      {/* Header with backdrop */}
      {details.backdrop_url && (
        <div className="relative -mx-6 -mt-6 mb-6 sm:-mx-8 sm:-mt-8 sm:mb-8 rounded-none">
          <img
            src={details.backdrop_url}
            alt=""
            className="w-full h-48 sm:h-64 object-cover"
            aria-hidden="true"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-surface-900/80 via-surface-900/20 to-transparent" aria-hidden="true" />
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-6 sm:gap-8">
        {/* Poster & Primary Info */}
        <div className="flex-shrink-0 w-full sm:w-64">
          {details.poster_url && (
            <div className="relative mx-auto sm:mx-0" style={{ maxWidth: '240px' }}>
              <img
                src={details.poster_url}
                alt=""
                className="w-full aspect-[2/3] object-cover rounded-lg shadow-xl"
                aria-hidden="true"
              />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* Title Row */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
            <div className="min-w-0">
              <div className="flex items-center gap-3 mb-2 flex-wrap">
                <span className="badge badge-almond">{mediaTypeLabel}</span>
                <button
                  onClick={handleFavoriteToggle}
                  className={`favorite-btn ${isFav ? "favorite-btn-active" : "favorite-btn-inactive"}`}
                  aria-label={isFav ? `Remove "${getDisplayTitle(details)}" from favorites` : `Add "${getDisplayTitle(details)}" to favorites`}
                  aria-pressed={isFav}
                >
                  <svg className="w-5 h-5" fill={isFav ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </button>
              </div>
              <h1 id="media-title" className="text-2xl sm:text-3xl font-bold text-surface-900">{getDisplayTitle(details)}</h1>
              {details.tagline && (
                <p className="mt-2 text-surface-600 italic">"{details.tagline}"</p>
              )}
            </div>
          </div>

          {/* Meta Info */}
          <div className="flex flex-wrap items-center gap-3 text-sm text-surface-600 mb-6 divider-y">
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
              <span>{fullReleaseDate}</span>
            </div>

            {details.runtime && details.media_type === "movie" && (
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{formatRuntime(details.runtime)}</span>
              </div>
            )}

            {details.episode_run_time.length > 0 && details.media_type === "tv" && (
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{formatEpisodeRuntime(details.episode_run_time)} per episode</span>
              </div>
            )}

            {details.number_of_seasons && details.media_type === "tv" && (
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                <span>{details.number_of_seasons} season{details.number_of_seasons !== 1 ? "s" : ""}</span>
              </div>
            )}

            {details.number_of_episodes && details.media_type === "tv" && (
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 5l7-7m0 0l-7 7m7-7H3m14 14l-7 7m0 0l7-7m-7 7h14" /></svg>
                <span>{details.number_of_episodes} episode{details.number_of_episodes !== 1 ? "s" : ""}</span>
              </div>
            )}

            {details.status && (
              <span className="badge badge-gray capitalize">{details.status.toLowerCase().replace("_", " ")}</span>
            )}

            {details.vote_average !== null && details.vote_average > 0 && (
              <div className="flex items-center gap-1 text-brand-600">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
                <span className="font-medium">{details.vote_average.toFixed(1)}</span>
                <span className="text-surface-400">({details.vote_count.toLocaleString()})</span>
              </div>
            )}

            {details.original_language && (
              <span className="badge badge-gray uppercase">{details.original_language}</span>
            )}
          </div>

          {/* Genres */}
          {details.genres.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Genres</h3>
              <div className="flex flex-wrap gap-2">
                {details.genres.map((genre) => (
                  <span key={genre.id} className="badge badge-gray">{genre.name}</span>
                ))}
              </div>
            </div>
          )}

          {/* Overview */}
          {details.overview && (
            <div className="mb-6 divider-y">
              <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-2">Overview</h3>
              <p className="text-surface-700 leading-relaxed">{details.overview}</p>
            </div>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
            {/* Production Companies */}
            {details.production_companies.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Production Companies</h3>
                <div className="flex flex-wrap gap-2">
                  {details.production_companies.slice(0, 10).map((company) => (
                    <div key={company.id} className="flex items-center gap-2 px-3 py-2 bg-surface-50 rounded-lg">
                      {company.logo_url && (
                        <img src={company.logo_url} alt="" className="w-6 h-6 object-contain" aria-hidden="true" />
                      )}
                      <span className="text-sm text-surface-700">{company.name}</span>
                      {company.origin_country && (
                        <span className="text-xs text-surface-500">({company.origin_country})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Production Countries */}
            {details.production_countries.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Production Countries</h3>
                <div className="flex flex-wrap gap-2">
                  {details.production_countries.map((country) => (
                    <span key={country.iso_3166_1} className="badge badge-gray">{country.name}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Spoken Languages */}
            {details.spoken_languages.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Spoken Languages</h3>
                <div className="flex flex-wrap gap-2">
                  {details.spoken_languages.map((lang) => (
                    <span key={lang.iso_639_1} className="badge badge-gray">{lang.english_name}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Keywords */}
            {details.keywords.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Keywords</h3>
                <div className="flex flex-wrap gap-2">
                  {details.keywords.slice(0, 15).map((keyword) => (
                    <span key={keyword.id} className="badge badge-almond">{keyword.name}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Cast */}
          {details.cast.length > 0 && (
            <div className="mb-8 divider-y">
              <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-4">Top Cast</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {details.cast.slice(0, 12).map((actor) => (
                  <div key={actor.id} className="text-center">
                    {actor.profile_url ? (
                      <img
                        src={actor.profile_url}
                        alt={actor.name}
                        className="w-24 h-24 mx-auto rounded-full object-cover mb-2 shadow-sm"
                      />
                    ) : (
                      <div className="w-24 h-24 mx-auto rounded-full bg-surface-200 flex items-center justify-center mb-2" aria-hidden="true">
                        <svg className="w-10 h-10 text-surface-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                    )}
                    <p className="text-sm font-medium text-surface-900 truncate">{actor.name}</p>
                    {actor.character && (
                      <p className="text-xs text-surface-500 truncate">as {actor.character}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Directors */}
          {details.directors.length > 0 && (
            <div className="mb-8 divider-y">
              <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-4">Director{details.directors.length > 1 ? "s" : ""}</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {details.directors.map((director) => (
                  <div key={director.id} className="text-center">
                    {director.profile_url ? (
                      <img
                        src={director.profile_url}
                        alt={director.name}
                        className="w-24 h-24 mx-auto rounded-full object-cover mb-2 shadow-sm"
                      />
                    ) : (
                      <div className="w-24 h-24 mx-auto rounded-full bg-surface-200 flex items-center justify-center mb-2" aria-hidden="true">
                        <svg className="w-10 h-10 text-surface-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                    )}
                    <p className="text-sm font-medium text-surface-900 truncate">{director.name}</p>
                    <p className="text-xs text-surface-500">Director</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Feedback Buttons */}
          <div className="divider-y">
            <h3 className="text-sm font-medium text-surface-500 uppercase tracking-wider mb-3">Your Feedback</h3>
            <div className="flex flex-wrap gap-2">
              {feedbackTypes.map((type) => {
                const isActive = hasFeedback(details.media_type, details.id, type);
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleFeedback(type)}
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
            <p className="text-xs text-surface-400 mt-3 text-center">Feedback is stored locally and does not affect recommendations.</p>
          </div>

          {/* External links */}
          {details.homepage && (
            <div className="mt-6 pt-6 divider-y">
              <a
                href={details.homepage}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg font-medium transition-all duration-200 hover:bg-brand-700 hover:shadow-card-hover focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Official Website
              </a>
            </div>
          )}

          {/* Back Link */}
          <div className="mt-6 pt-6 divider-y">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-surface-600 hover:text-surface-900 font-medium transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to search
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}