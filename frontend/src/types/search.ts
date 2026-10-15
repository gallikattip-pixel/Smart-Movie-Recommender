/** Search types for frontend API integration. */

export type SearchType = "multi" | "movie" | "tv";

export interface SearchResultItem {
  id: number;
  title: string;
  media_type: "movie" | "tv";
  release_date: string | null;
  first_air_date: string | null;
  overview: string | null;
  poster_path: string | null;
  poster_url: string | null;
  vote_average: number | null;
  vote_count: number;
  popularity: number;
  original_language: string;
  genre_ids: number[];
}

export interface SearchResponse {
  results: SearchResultItem[];
  page: number;
  total_pages: number;
  total_results: number;
  query: string;
  search_type: string;
  intent?: {
    intent_type: string;
    seed_title?: string;
    genres?: number[];
    moods?: string[];
    languages?: string[];
    countries?: string[];
    era?: { start_year?: number; end_year?: number };
    content_type?: string;
    cleaned_query?: string;
    confidence: number;
  } | null;
}

export interface SearchError {
  detail: string;
  code?: string;
}

export interface SearchState {
  query: string;
  type: SearchType;
  page: number;
  loading: boolean;
  error: string | null;
  results: SearchResultItem[];
  total_pages: number;
  total_results: number;
  hasSearched: boolean;
}