/** Media details types for frontend API integration. */

export interface GenreItem {
  id: number;
  name: string;
}

export interface ProductionCompanyItem {
  id: number;
  name: string;
  logo_path: string | null;
  logo_url: string | null;
  origin_country: string | null;
}

export interface ProductionCountryItem {
  iso_3166_1: string;
  name: string;
}

export interface SpokenLanguageItem {
  english_name: string;
  iso_639_1: string;
  name: string;
}

export interface CastMemberItem {
  id: number;
  name: string;
  character: string | null;
  profile_path: string | null;
  profile_url: string | null;
  order: number;
  known_for_department: string;
}

export interface CrewMemberItem {
  id: number;
  name: string;
  job: string;
  department: string;
  profile_path: string | null;
  profile_url: string | null;
}

export interface KeywordItem {
  id: number;
  name: string;
}

export interface MediaDetailsResponse {
  id: number;
  title: string;
  media_type: "movie" | "tv";
  release_date: string | null;
  first_air_date: string | null;
  overview: string | null;
  poster_path: string | null;
  poster_url: string | null;
  backdrop_path: string | null;
  backdrop_url: string | null;
  vote_average: number | null;
  vote_count: number;
  popularity: number;
  original_language: string;
  genres: GenreItem[];
  runtime: number | null;
  episode_run_time: number[];
  number_of_seasons: number | null;
  number_of_episodes: number | null;
  status: string | null;
  tagline: string | null;
  homepage: string | null;
  production_companies: ProductionCompanyItem[];
  production_countries: ProductionCountryItem[];
  spoken_languages: SpokenLanguageItem[];
  cast: CastMemberItem[];
  crew: CrewMemberItem[];
  keywords: KeywordItem[];
  directors: CrewMemberItem[];
}

export interface FavoriteTitleRequest {
  media_type: "movie" | "tv";
  item_id: number;
}

export interface FavoritesResolveRequest {
  titles: FavoriteTitleRequest[];
}

export interface FavoritesResolveResponse {
  resolved: MediaDetailsResponse[];
  failed: Array<{
    media_type: string;
    item_id: number;
    error: string;
    code: string;
    status_code: number;
  }>;
}

export interface FavoritesState {
  favorites: FavoriteTitleRequest[];
}