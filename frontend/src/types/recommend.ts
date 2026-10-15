/** Recommendation types for frontend API integration. */

import type { MediaDetailsResponse } from "./details";

export type AlgorithmType = "bfs" | "dfs" | "ucs" | "greedy" | "astar" | "hybrid";

export interface EraRange {
  start_year?: number;
  end_year?: number;
}

export interface UserPreference {
  favorite_titles: FavoriteTitleRequest[];
  query?: string;
  preferred_genres: number[];
  excluded_genres: number[];
  preferred_languages: string[];
  excluded_languages: string[];
  preferred_countries: string[];
  excluded_countries: string[];
  content_types: ("movie" | "tv")[];
  era: EraRange | null;
  min_vote_average: number | null;
  preferred_themes: string[];
  excluded_themes: string[];
  preferred_moods: string[];
  excluded_moods: string[];
  preferred_pacing: string[];
  preferred_endings: string[];
  prefer_hidden_gems: boolean;
  prefer_similar: boolean;
  feedback_likes?: FavoriteTitleRequest[];
  feedback_dislikes?: FavoriteTitleRequest[];
  feedback_watched?: FavoriteTitleRequest[];
  feedback_more_like_this?: FavoriteTitleRequest[];
}

export interface FavoriteTitleRequest {
  media_type: "movie" | "tv";
  item_id: number;
}

export interface RecommendRequest {
  preferences: UserPreference;
  limit: number;
  algorithm: AlgorithmType;
  exclude_favorites: boolean;
  include_explanations: boolean;
}

export interface ExplanationReason {
  type: "genre" | "keyword" | "cast" | "director" | "language" | "country" | "era" | "rating" | "theme" | "mood" | "content_type" | "hidden_gem" | "similar_to_favorite";
  description: string;
  weight: number;
}

export interface RecommendationItem {
  media: MediaDetailsResponse;
  similarity_score: number;
  preference_score: number;
  final_score: number;
  explanation: ExplanationReason[];
  graph_path: number[] | null;
}

export interface RecommendResponse {
  recommendations: RecommendationItem[];
  algorithm_used: string;
  total_candidates_considered: number;
  total_excluded: number;
  search_time_ms: number;
}

export interface RecommendError {
  detail: string;
  code?: string;
}

// TMDB Genre constants (stable IDs from TMDB)
export const MOVIE_GENRES: { id: number; name: string }[] = [
  { id: 28, name: "Action" },
  { id: 12, name: "Adventure" },
  { id: 16, name: "Animation" },
  { id: 35, name: "Comedy" },
  { id: 80, name: "Crime" },
  { id: 99, name: "Documentary" },
  { id: 18, name: "Drama" },
  { id: 10751, name: "Family" },
  { id: 14, name: "Fantasy" },
  { id: 36, name: "History" },
  { id: 27, name: "Horror" },
  { id: 10402, name: "Music" },
  { id: 9648, name: "Mystery" },
  { id: 10749, name: "Romance" },
  { id: 878, name: "Science Fiction" },
  { id: 10770, name: "TV Movie" },
  { id: 53, name: "Thriller" },
  { id: 10752, name: "War" },
  { id: 37, name: "Western" },
];

export const TV_GENRES: { id: number; name: string }[] = [
  { id: 10759, name: "Action & Adventure" },
  { id: 16, name: "Animation" },
  { id: 35, name: "Comedy" },
  { id: 80, name: "Crime" },
  { id: 99, name: "Documentary" },
  { id: 18, name: "Drama" },
  { id: 10751, name: "Family" },
  { id: 10762, name: "Kids" },
  { id: 9648, name: "Mystery" },
  { id: 10763, name: "News" },
  { id: 10764, name: "Reality" },
  { id: 10765, name: "Sci-Fi & Fantasy" },
  { id: 10766, name: "Soap" },
  { id: 10767, name: "Talk" },
  { id: 10768, name: "War & Politics" },
  { id: 37, name: "Western" },
];

export const ALL_GENRES = [...MOVIE_GENRES, ...TV_GENRES.filter(tv => !MOVIE_GENRES.some(m => m.id === tv.id))];

// Common languages (ISO 639-1)
export const COMMON_LANGUAGES = [
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "de", name: "German" },
  { code: "it", name: "Italian" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "zh", name: "Chinese" },
  { code: "hi", name: "Hindi" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
  { code: "ar", name: "Arabic" },
];

// Common countries (ISO 3166-1)
export const COMMON_COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "IN", name: "India" },
  { code: "KR", name: "South Korea" },
  { code: "JP", name: "Japan" },
  { code: "CN", name: "China" },
  { code: "FR", name: "France" },
  { code: "DE", name: "Germany" },
  { code: "IT", name: "Italy" },
  { code: "ES", name: "Spain" },
  { code: "BR", name: "Brazil" },
  { code: "MX", name: "Mexico" },
];