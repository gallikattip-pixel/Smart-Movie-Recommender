/** Favorites storage service using localStorage. */

import type { FavoriteTitleRequest } from "../types/details";

const STORAGE_KEY = "smart-movie-recommender-favorites";

export function getFavorites(): FavoriteTitleRequest[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    // Validate each favorite has required fields
    return parsed.filter(
      (f): f is FavoriteTitleRequest =>
        f &&
        typeof f === "object" &&
        (f.media_type === "movie" || f.media_type === "tv") &&
        typeof f.item_id === "number" &&
        f.item_id > 0
    );
  } catch {
    return [];
  }
}

export function saveFavorites(favorites: FavoriteTitleRequest[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
  } catch {
    // Ignore storage errors (e.g., quota exceeded, private browsing)
  }
}

export function addFavorite(favorite: FavoriteTitleRequest): FavoriteTitleRequest[] {
  const favorites = getFavorites();
  // Check if already exists
  const exists = favorites.some(
    (f) => f.media_type === favorite.media_type && f.item_id === favorite.item_id
  );
  if (!exists) {
    favorites.push(favorite);
    saveFavorites(favorites);
  }
  return favorites;
}

export function removeFavorite(mediaType: "movie" | "tv", itemId: number): FavoriteTitleRequest[] {
  const favorites = getFavorites().filter(
    (f) => !(f.media_type === mediaType && f.item_id === itemId)
  );
  saveFavorites(favorites);
  return favorites;
}

export function toggleFavorite(favorite: FavoriteTitleRequest): FavoriteTitleRequest[] {
  const favorites = getFavorites();
  const index = favorites.findIndex(
    (f) => f.media_type === favorite.media_type && f.item_id === favorite.item_id
  );
  if (index >= 0) {
    favorites.splice(index, 1);
  } else {
    favorites.push(favorite);
  }
  saveFavorites(favorites);
  return favorites;
}

export function isFavorite(mediaType: "movie" | "tv", itemId: number): boolean {
  const favorites = getFavorites();
  return favorites.some((f) => f.media_type === mediaType && f.item_id === itemId);
}

export function clearFavorites(): void {
  localStorage.removeItem(STORAGE_KEY);
}