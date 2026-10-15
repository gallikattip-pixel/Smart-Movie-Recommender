/** Search API service for frontend. */

import type { SearchType, SearchResponse, SearchResultItem, SearchError } from "../types/search";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, "")}/api`
  : "/api";

interface SearchParams {
  query: string;
  type?: SearchType;
  page?: number;
  include_adult?: boolean;
  language?: string;
  signal?: AbortSignal;
}

function buildSearchUrl(params: SearchParams): string {
  const searchParams = new URLSearchParams();
  searchParams.set("query", params.query);
  if (params.type) searchParams.set("type", params.type);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.include_adult !== undefined) searchParams.set("include_adult", String(params.include_adult));
  if (params.language) searchParams.set("language", params.language);
  return `${API_BASE}/search?${searchParams.toString()}`;
}

export async function searchMedia(params: SearchParams): Promise<SearchResponse> {
  const url = buildSearchUrl(params);
  const response = await fetch(url, { signal: params.signal });

  if (!response.ok) {
    const errorData: SearchError = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
      code: "HTTP_ERROR",
    }));

    // Include status code in error for better handling
    const error = new Error(errorData.detail) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code || response.headers.get("X-Error-Code") || undefined;
    throw error;
  }

  return response.json();
}

export function formatReleaseDate(dateStr: string | null): string {
  if (!dateStr) return "Unknown";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "Unknown";
    return date.getFullYear().toString();
  } catch {
    return "Unknown";
  }
}

export function getDisplayTitle(item: SearchResultItem): string {
  return item.title;
}

export function getReleaseYear(item: SearchResultItem): string {
  if (item.media_type === "movie" && item.release_date) {
    return formatReleaseDate(item.release_date);
  }
  if (item.media_type === "tv" && item.first_air_date) {
    return formatReleaseDate(item.first_air_date);
  }
  return "Unknown";
}