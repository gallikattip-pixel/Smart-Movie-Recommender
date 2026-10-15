/** Media details and favorites API services for frontend. */

import type { MediaDetailsResponse, FavoritesResolveRequest, FavoritesResolveResponse } from "../types/details";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, "")}/api`
  : "/api";

export async function getMediaDetails(mediaType: "movie" | "tv", itemId: number): Promise<MediaDetailsResponse> {
  const response = await fetch(`${API_BASE}/search/${mediaType}/${itemId}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
      code: "HTTP_ERROR",
    }));

    const error = new Error(errorData.detail) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code || response.headers.get("X-Error-Code") || undefined;
    throw error;
  }

  return response.json();
}

export async function resolveFavorites(request: FavoritesResolveRequest): Promise<FavoritesResolveResponse> {
  const response = await fetch(`${API_BASE}/favorites/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
      code: "HTTP_ERROR",
    }));

    const error = new Error(errorData.detail) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code || response.headers.get("X-Error-Code") || undefined;
    throw error;
  }

  return response.json();
}

export function formatRuntime(minutes: number | null): string {
  if (!minutes) return "Unknown";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  }
  return `${mins}m`;
}

export function formatEpisodeRuntime(runtimes: number[]): string {
  if (!runtimes.length) return "Unknown";
  const avg = Math.round(runtimes.reduce((a, b) => a + b, 0) / runtimes.length);
  return `${avg}m`;
}

export function formatReleaseDate(dateStr: string | null): string {
  if (!dateStr) return "Unknown";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "Unknown";
    return date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  } catch {
    return "Unknown";
  }
}

export function formatReleaseYear(dateStr: string | null): string {
  if (!dateStr) return "Unknown";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "Unknown";
    return date.getFullYear().toString();
  } catch {
    return "Unknown";
  }
}

export function getDisplayTitle(item: MediaDetailsResponse): string {
  return item.title;
}

export function getMediaTypeLabel(mediaType: "movie" | "tv"): string {
  return mediaType === "movie" ? "Movie" : "TV Series";
}