import { useEffect, useState, useCallback } from "react";
import type { MediaDetailsResponse } from "../types/details";
import { getMediaDetails, formatRuntime, formatReleaseYear } from "../services/details";
import { isFavorite, toggleFavorite } from "../services/favorites";
import {
  hasFeedback,
  toggleFeedback,
  getFeedbackColor,
  getFeedbackIcon,
  getFeedbackLabel,
  type FeedbackType,
} from "../services/feedback";

interface MediaDetailsModalProps {
  mediaType: "movie" | "tv";
  itemId: number;
  isOpen: boolean;
  onClose: () => void;
  onMoreLikeThis?: (mediaType: "movie" | "tv", itemId: number, title: string) => void;
  onFavoriteChange?: () => void;
}

export function MediaDetailsModal({
  mediaType,
  itemId,
  isOpen,
  onClose,
  onMoreLikeThis,
  onFavoriteChange,
}: MediaDetailsModalProps) {
  const [details, setDetails] = useState<MediaDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFav, setIsFav] = useState(false);
  const [, setFeedbackTrigger] = useState(0);

  // Fetch media details when modal opens with a valid itemId
  useEffect(() => {
    if (!isOpen || !itemId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);
    setIsFav(isFavorite(mediaType, itemId));

    getMediaDetails(mediaType, itemId)
      .then((data) => {
        if (isMounted) {
          setDetails(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || "Failed to load title details.");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, mediaType, itemId]);

  // Handle ESC key press
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleToggleFavorite = useCallback(() => {
    toggleFavorite({ media_type: mediaType, item_id: itemId });
    const newFavStatus = isFavorite(mediaType, itemId);
    setIsFav(newFavStatus);
    if (onFavoriteChange) onFavoriteChange();
  }, [mediaType, itemId, onFavoriteChange]);

  const handleFeedbackClick = useCallback(
    (type: FeedbackType) => {
      toggleFeedback(mediaType, itemId, type);
      setFeedbackTrigger((prev) => prev + 1);
      if (type === "more_like_this" && onMoreLikeThis && details) {
        onMoreLikeThis(mediaType, itemId, details.title);
      }
    },
    [mediaType, itemId, onMoreLikeThis, details]
  );

  if (!isOpen) return null;

  const feedbackTypes: FeedbackType[] = ["like", "dislike", "watched", "more_like_this"];

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-media-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl bg-[#0e1320] border border-surface-700/70 rounded-2xl shadow-2xl overflow-hidden text-surface-100 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 p-2 rounded-full bg-black/60 hover:bg-black/80 text-surface-300 hover:text-white transition-all focus:outline-none focus:ring-2 focus:ring-almond-400"
          aria-label="Close details dialog"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center min-h-[380px]">
            <div className="w-10 h-10 border-4 border-almond-400/20 border-t-almond-400 rounded-full animate-spin mb-4" />
            <p className="text-surface-400 text-sm">Loading details from TMDB…</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center min-h-[300px] flex flex-col items-center justify-center">
            <div className="p-3 bg-rose-500/10 rounded-full text-rose-400 mb-3">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-surface-200 mb-1">Unable to Load Title</h3>
            <p className="text-surface-400 text-sm max-w-md mb-6">{error}</p>
            <button onClick={onClose} className="btn-secondary">
              Close
            </button>
          </div>
        ) : details ? (
          <>
            {/* Backdrop Banner */}
            {details.backdrop_url && (
              <div className="relative h-48 sm:h-64 w-full overflow-hidden">
                <img
                  src={details.backdrop_url}
                  alt=""
                  className="w-full h-full object-cover object-center filter brightness-[0.65]"
                  aria-hidden="true"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0e1320] via-transparent to-transparent" />
              </div>
            )}

            {/* Content Container */}
            <div className={`p-6 sm:p-8 ${details.backdrop_url ? "-mt-20 relative z-10" : ""}`}>
              <div className="flex flex-col sm:flex-row gap-6">
                {/* Poster */}
                <div className="flex-shrink-0 w-36 sm:w-48 mx-auto sm:mx-0 shadow-2xl rounded-xl overflow-hidden border border-surface-700/60 bg-surface-900">
                  {details.poster_url ? (
                    <img
                      src={details.poster_url}
                      alt={details.title}
                      className="w-full h-auto object-cover"
                    />
                  ) : (
                    <div className="w-full h-64 bg-surface-900 flex flex-col items-center justify-center text-surface-500">
                      <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                      </svg>
                      <span className="text-xs">No Poster</span>
                    </div>
                  )}
                </div>

                {/* Main Details */}
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 id="modal-media-title" className="text-2xl sm:text-3xl font-extrabold text-white leading-tight">
                        {details.title}
                      </h2>
                      {details.tagline && (
                        <p className="text-sm italic text-almond-300/90 mt-1">{details.tagline}</p>
                      )}
                    </div>

                    {/* Favorite Button */}
                    <button
                      onClick={handleToggleFavorite}
                      className={`p-2.5 rounded-full transition-all ${
                        isFav
                          ? "bg-almond-400 text-stone-950 shadow-md shadow-black/30"
                          : "bg-surface-800 text-surface-300 hover:text-almond-300 hover:bg-surface-700 border border-surface-700"
                      }`}
                      title={isFav ? "Remove from favorites" : "Add to favorites"}
                      aria-label={isFav ? "Remove from favorites" : "Add to favorites"}
                      aria-pressed={isFav}
                    >
                      <svg
                        className="w-5 h-5"
                        fill={isFav ? "currentColor" : "none"}
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                        />
                      </svg>
                    </button>
                  </div>

                  {/* Metadata Row */}
                  <div className="flex flex-wrap items-center gap-2 mt-3 text-xs sm:text-sm text-surface-300">
                    <span className="badge badge-almond uppercase tracking-wider">{details.media_type}</span>
                    <span className="text-surface-600">•</span>
                    <span>{formatReleaseYear(details.release_date || details.first_air_date)}</span>
                    {details.runtime ? (
                      <>
                        <span className="text-surface-600">•</span>
                        <span>{formatRuntime(details.runtime)}</span>
                      </>
                    ) : details.number_of_seasons ? (
                      <>
                        <span className="text-surface-600">•</span>
                        <span>
                          {details.number_of_seasons} Season{details.number_of_seasons > 1 ? "s" : ""}
                        </span>
                      </>
                    ) : null}
                    {details.vote_average !== null && details.vote_average > 0 && (
                      <>
                        <span className="text-surface-600">•</span>
                        <div className="inline-flex items-center gap-1 font-semibold text-almond-300">
                          <svg className="w-4 h-4 fill-current text-almond-400" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                          </svg>
                          <span>{details.vote_average.toFixed(1)}</span>
                          <span className="text-surface-400 text-xs">({details.vote_count.toLocaleString()})</span>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Genres */}
                  {details.genres && details.genres.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {details.genres.map((g) => (
                        <span key={g.id} className="badge badge-gray text-xs">
                          {g.name}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Overview */}
                  <div className="mt-4">
                    <h4 className="text-xs uppercase font-bold tracking-wider text-surface-400 mb-1">Overview</h4>
                    <p className="text-sm text-surface-200 leading-relaxed max-h-48 overflow-y-auto pr-2">
                      {details.overview || "No overview available for this title."}
                    </p>
                  </div>

                  {/* Cast & Directors */}
                  {(details.directors?.length > 0 || details.cast?.length > 0) && (
                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs border-t border-surface-800/80 pt-3">
                      {details.directors?.length > 0 && (
                        <div>
                          <span className="text-surface-400 uppercase font-bold block mb-1">Director</span>
                          <span className="text-surface-200">
                            {details.directors.map((d) => d.name).join(", ")}
                          </span>
                        </div>
                      )}
                      {details.cast?.length > 0 && (
                        <div>
                          <span className="text-surface-400 uppercase font-bold block mb-1">Top Cast</span>
                          <span className="text-surface-200 line-clamp-2">
                            {details.cast.slice(0, 5).map((c) => c.name).join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Feedback Controls Section */}
              <div className="mt-6 pt-5 border-t border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="w-full sm:w-auto">
                  <span className="text-xs uppercase font-bold tracking-wider text-surface-400 block mb-2 sm:mb-1">
                    Your Feedback
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {feedbackTypes.map((type) => {
                      const isActive = hasFeedback(mediaType, itemId, type);
                      return (
                        <button
                          key={type}
                          type="button"
                          onClick={() => handleFeedbackClick(type)}
                          className={`feedback-btn ${getFeedbackColor(type, isActive)} ${
                            isActive ? "feedback-btn-active" : ""
                          }`}
                          title={getFeedbackLabel(type)}
                          aria-label={getFeedbackLabel(type)}
                          aria-pressed={isActive}
                        >
                          {getFeedbackIcon(type, isActive)}
                          <span>{getFeedbackLabel(type)}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* More Like This Quick Action */}
                {onMoreLikeThis && (
                  <button
                    type="button"
                    onClick={() => {
                      onMoreLikeThis(mediaType, itemId, details.title);
                      onClose();
                    }}
                    className="btn-primary w-full sm:w-auto text-sm"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>Recommend Similar Titles</span>
                  </button>
                )}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
