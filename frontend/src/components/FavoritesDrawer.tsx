import React, { useEffect, useState } from "react";
import { getFavorites, removeFavorite, clearFavorites } from "../services/favorites";
import { resolveFavorites } from "../services/details";
import type { MediaDetailsResponse } from "../types/details";

interface FavoritesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectMedia: (mediaType: "movie" | "tv", itemId: number) => void;
  onRecommendFromFavorites: () => void;
}

export function FavoritesDrawer({
  isOpen,
  onClose,
  onSelectMedia,
  onRecommendFromFavorites,
}: FavoritesDrawerProps) {
  const [favoriteItems, setFavoriteItems] = useState<MediaDetailsResponse[]>([]);
  const [loading, setLoading] = useState(false);

  const loadFavorites = async () => {
    const rawFavs = getFavorites();
    if (rawFavs.length === 0) {
      setFavoriteItems([]);
      return;
    }

    setLoading(true);
    try {
      const res = await resolveFavorites({ titles: rawFavs });
      setFavoriteItems(res.resolved);
    } catch {
      // If resolving fails, keep minimal state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadFavorites();
    }
  }, [isOpen]);

  const handleRemove = (e: React.MouseEvent, mediaType: "movie" | "tv", itemId: number) => {
    e.stopPropagation();
    removeFavorite(mediaType, itemId);
    setFavoriteItems((prev) => prev.filter((item) => !(item.media_type === mediaType && item.id === itemId)));
  };

  const handleClearAll = () => {
    clearFavorites();
    setFavoriteItems([]);
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm flex justify-end animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="favorites-drawer-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[#0c101a] border-l border-surface-800 h-full flex flex-col shadow-2xl p-6 text-surface-100 animate-slide-left"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-surface-800">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-almond-400 fill-current" viewBox="0 0 24 24">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
            </svg>
            <h2 id="favorites-drawer-title" className="text-xl font-bold text-white">
              Your Favorites ({favoriteItems.length})
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800 transition-colors"
            aria-label="Close favorites panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center">
              <div className="w-8 h-8 border-3 border-almond-400/20 border-t-almond-400 rounded-full animate-spin mb-3" />
              <p className="text-xs text-surface-400">Loading your favorites…</p>
            </div>
          ) : favoriteItems.length === 0 ? (
            <div className="py-16 text-center text-surface-400">
              <svg className="w-12 h-12 mx-auto text-surface-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <h3 className="text-base font-semibold text-surface-200">No favorites yet</h3>
              <p className="text-xs text-surface-500 mt-1 max-w-xs mx-auto">
                Click the heart icon on any movie or TV series card to save it to your taste profile.
              </p>
            </div>
          ) : (
            favoriteItems.map((item) => (
              <div
                key={`${item.media_type}-${item.id}`}
                onClick={() => {
                  onSelectMedia(item.media_type, item.id);
                  onClose();
                }}
                className="flex items-center gap-3 p-2.5 rounded-xl bg-surface-900/60 border border-surface-800/80 hover:border-almond-400/40 hover:bg-surface-800/60 cursor-pointer transition-all group"
              >
                <div className="w-12 h-16 flex-shrink-0 bg-surface-800 rounded-lg overflow-hidden border border-surface-700/50">
                  {item.poster_url ? (
                    <img src={item.poster_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-surface-500 text-xs">
                      TMDB
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-surface-100 group-hover:text-almond-300 transition-colors truncate">
                    {item.title}
                  </h4>
                  <div className="flex items-center gap-2 text-xs text-surface-400 mt-1">
                    <span className="capitalize">{item.media_type}</span>
                    <span>•</span>
                    <span>
                      {item.release_date
                        ? new Date(item.release_date).getFullYear()
                        : item.first_air_date
                        ? new Date(item.first_air_date).getFullYear()
                        : "N/A"}
                    </span>
                    {item.vote_average ? (
                      <>
                        <span>•</span>
                        <span className="text-almond-300 font-medium">★ {item.vote_average.toFixed(1)}</span>
                      </>
                    ) : null}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => handleRemove(e, item.media_type, item.id)}
                  className="p-2 text-surface-500 hover:text-rose-400 hover:bg-surface-800 rounded-lg transition-colors"
                  title="Remove from favorites"
                  aria-label={`Remove ${item.title} from favorites`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer Actions */}
        {favoriteItems.length > 0 && (
          <div className="pt-4 border-t border-surface-800 space-y-2">
            <button
              type="button"
              onClick={() => {
                onRecommendFromFavorites();
                onClose();
              }}
              className="btn-primary w-full"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Recommend Based On Favorites</span>
            </button>
            <button
              type="button"
              onClick={handleClearAll}
              className="w-full text-center py-1.5 text-xs text-surface-500 hover:text-rose-400 transition-colors"
            >
              Clear all favorites
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
