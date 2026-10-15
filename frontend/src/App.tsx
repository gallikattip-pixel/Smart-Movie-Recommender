import { useState, useEffect, useCallback, useRef } from "react";
import { searchMedia, getDisplayTitle, getReleaseYear } from "./services/search";
import { getRecommendations } from "./services/recommend";
import { getFavorites, isFavorite, toggleFavorite } from "./services/favorites";
import {
  hasFeedback,
  toggleFeedback,
  getFeedbackColor,
  getFeedbackIcon,
  getFeedbackLabel,
  getFeedbackByType,
  type FeedbackType,
} from "./services/feedback";
import type { SearchResultItem } from "./types/search";
import type { UserPreference, RecommendationItem, ExplanationReason } from "./types/recommend";
import { MediaDetailsModal } from "./components/MediaDetailsModal";
import { PreferencesFilter } from "./components/PreferencesFilter";
import { FavoritesDrawer } from "./components/FavoritesDrawer";

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

export function App() {
  const [nlPrompt, setNlPrompt] = useState("");
  const [titleQuery, setTitleQuery] = useState("");

  const [activeTab, setActiveTab] = useState<"recommendations" | "search">("recommendations");
  const [preferences, setPreferences] = useState<UserPreference>(DEFAULT_PREFERENCES);
  const [filterOpen, setFilterOpen] = useState(false);

  // Results & Loading
  const [searchLoading, setSearchLoading] = useState(false);
  const [recLoading, setRecLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [recError, setRecError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [detectedIntent, setDetectedIntent] = useState<any | null>(null);
  const [recStats, setRecStats] = useState<{ candidates: number; excluded: number; timeMs: number } | null>(null);

  // Overlays / Modals
  const [selectedMedia, setSelectedMedia] = useState<{ mediaType: "movie" | "tv"; itemId: number } | null>(null);
  const [favoritesDrawerOpen, setFavoritesDrawerOpen] = useState(false);
  const [favoritesCount, setFavoritesCount] = useState(0);
  const [, setFeedbackVersion] = useState(0);

  // Cancellation controllers
  const searchAbortRef = useRef<AbortController | null>(null);
  const recAbortRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const recDebounceTimerRef = useRef<number | null>(null);

  // Sync favorites count on mount and after changes
  const refreshFavoritesCount = useCallback(() => {
    const favs = getFavorites();
    setFavoritesCount(favs.length);
  }, []);

  useEffect(() => {
    refreshFavoritesCount();
    // Initial recommendation exploration (backend operates hybrid algorithm quietly)
    runRecommendations("", DEFAULT_PREFERENCES);
  }, [refreshFavoritesCount]);

  // Main recommendation fetch function (sends full description to FastAPI backend)
  const runRecommendations = async (
    descriptionText: string,
    currentPrefs: UserPreference
  ) => {
    if (recAbortRef.current) {
      recAbortRef.current.abort();
    }
    const controller = new AbortController();
    recAbortRef.current = controller;

    setRecLoading(true);
    setRecError(null);

    const storedFavs = getFavorites();
    const likes = getFeedbackByType("like");
    const dislikes = getFeedbackByType("dislike");
    const watched = getFeedbackByType("watched");
    const moreLikeThis = getFeedbackByType("more_like_this");

    try {
      const recPayload: UserPreference = {
        ...currentPrefs,
        query: descriptionText.trim() || undefined,
        favorite_titles: storedFavs,
        feedback_likes: likes,
        feedback_dislikes: dislikes,
        feedback_watched: watched,
        feedback_more_like_this: moreLikeThis,
      };

      const res = await getRecommendations(
        {
          preferences: recPayload,
          limit: 20,
          algorithm: "hybrid",
          exclude_favorites: false,
          include_explanations: true,
        },
        controller.signal
      );

      setRecommendations(res.recommendations);
      setRecStats({
        candidates: res.total_candidates_considered,
        excluded: res.total_excluded,
        timeMs: res.search_time_ms,
      });
      setActiveTab("recommendations");
    } catch (err: any) {
      if (err.name === "AbortError") return;
      const msg = err.message || "Failed to generate recommendations.";
      setRecError(msg);
    } finally {
      setRecLoading(false);
    }
  };

  // Main exact-title search execution function
  const executeTitleSearch = useCallback(
    async (searchText: string) => {
      const trimmed = searchText.trim();
      if (!trimmed) {
        setSearchResults([]);
        return;
      }

      if (searchAbortRef.current) {
        searchAbortRef.current.abort();
      }
      const controller = new AbortController();
      searchAbortRef.current = controller;

      setSearchLoading(true);
      setSearchError(null);

      try {
        const searchRes = await searchMedia({
          query: trimmed,
          type: "multi",
          signal: controller.signal,
        });

        setSearchResults(searchRes.results);
        setDetectedIntent(searchRes.intent || null);
        setActiveTab("search");
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setSearchError(err.message || "Search failed.");
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    },
    []
  );

  // Handle Title input change with debounce
  const handleTitleQueryChange = (val: string) => {
    setTitleQuery(val);
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
    if (val.trim().length >= 2) {
      debounceTimerRef.current = window.setTimeout(() => {
        executeTitleSearch(val);
      }, 350);
    } else if (val.trim().length === 0) {
      setSearchResults([]);
    }
  };

  // Handle Exact Title search submit
  const handleTitleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
    executeTitleSearch(titleQuery);
  };

  const handlePreferencesChange = (updatedPrefs: UserPreference, customQuery?: string) => {
    setPreferences(updatedPrefs);
    const text = customQuery !== undefined ? customQuery : nlPrompt;
    if (recDebounceTimerRef.current) {
      window.clearTimeout(recDebounceTimerRef.current);
    }
    recDebounceTimerRef.current = window.setTimeout(() => {
      runRecommendations(text, updatedPrefs);
    }, 180);
  };

  const handleCardFavorite = (e: React.MouseEvent, mediaType: "movie" | "tv", itemId: number) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite({ media_type: mediaType, item_id: itemId });
    refreshFavoritesCount();
    setFeedbackVersion((v) => v + 1);
  };

  const handleCardFeedback = (
    e: React.MouseEvent,
    mediaType: "movie" | "tv",
    itemId: number,
    type: FeedbackType
  ) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFeedback(mediaType, itemId, type);
    setFeedbackVersion((v) => v + 1);

    if (type === "more_like_this") {
      const refinedPrompt = `More titles like #${itemId}`;
      setNlPrompt(refinedPrompt);
      runRecommendations(refinedPrompt, preferences);
    } else {
      runRecommendations(nlPrompt, preferences);
    }
  };

  const handleMoreLikeThisFromModal = (_mediaType: "movie" | "tv", _itemId: number, title: string) => {
    const refined = `Movies and TV series similar to ${title}`;
    setNlPrompt(refined);
    runRecommendations(refined, preferences);
  };

  const handleRecommendFromFavorites = () => {
    const favs = getFavorites();
    if (favs.length === 0) return;
    setActiveTab("recommendations");
    runRecommendations(nlPrompt, preferences);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#07090e] text-surface-100 selection:bg-almond-400 selection:text-stone-950">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-40 bg-[#0a0d16]/90 backdrop-blur-md border-b border-surface-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-almond-400 text-stone-950 flex items-center justify-center shadow-md shadow-black/30">
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-white tracking-tight leading-none">
                Smart Movie Recommender
              </h1>
            </div>
          </div>

          {/* Right Header Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Favorites Drawer Toggle */}
            <button
              onClick={() => setFavoritesDrawerOpen(true)}
              className="px-3.5 py-1.5 rounded-xl bg-surface-900/90 border border-surface-800 hover:border-almond-400/50 text-surface-200 hover:text-white transition-all inline-flex items-center gap-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-almond-400"
              aria-label="Open saved favorites panel"
            >
              <svg className="w-4 h-4 text-almond-400 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
              <span>Favorites</span>
              <span className="px-1.5 py-0.2 rounded-full bg-almond-400/20 text-almond-200 text-[11px] font-semibold border border-almond-400/30">
                {favoritesCount}
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Single-Page Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {/* Cinematic Hero Section */}
        <div className="text-center max-w-3xl mx-auto mb-8 sm:mb-10">
          <h2 className="text-3xl sm:text-5xl font-black text-white tracking-tight mb-3">
            Find your next <span className="text-almond-300">favorite</span>.
          </h2>
          <p className="text-sm sm:text-base text-surface-400 max-w-xl mx-auto mb-6">
            Search directly for titles or refine recommendations with custom preferences and descriptions below.
          </p>

          {/* Unified Title Search Bar */}
          <div className="animate-fade-in">
            <form onSubmit={handleTitleSubmit} className="relative">
              <div className="rounded-2xl bg-[#0b0f19] border border-surface-700/70 hover:border-surface-600 focus-within:border-almond-400/80 focus-within:ring-1 focus-within:ring-almond-400/30 p-2 sm:p-2.5 transition-all shadow-xl flex items-center gap-2">
                <div className="relative flex-1 flex items-center">
                  <svg className="w-5 h-5 text-almond-400/80 absolute left-3 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    value={titleQuery}
                    onChange={(e) => handleTitleQueryChange(e.target.value)}
                    placeholder="Search movies or TV shows worldwide..."
                    className="w-full pl-10 pr-9 py-2.5 bg-transparent text-white placeholder-surface-500 text-sm sm:text-base focus:outline-none"
                    autoComplete="off"
                    aria-label="Search movie or TV series by title"
                  />
                  {titleQuery && (
                    <button
                      type="button"
                      onClick={() => {
                        setTitleQuery("");
                        setSearchResults([]);
                      }}
                      className="absolute right-2 p-1 text-surface-400 hover:text-white transition-colors"
                      aria-label="Clear title search"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={searchLoading || !titleQuery.trim()}
                  className="btn-primary text-xs sm:text-sm px-5 py-2.5 flex-shrink-0 font-semibold"
                >
                  {searchLoading ? (
                    <span className="flex items-center gap-1.5">
                      <svg className="w-4 h-4 animate-spin text-stone-950" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Searching…</span>
                    </span>
                  ) : (
                    "Search Title"
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Expandable Preferences Filter */}
          <PreferencesFilter
            preferences={preferences}
            onChange={handlePreferencesChange}
            isOpen={filterOpen}
            onToggleOpen={() => setFilterOpen((o) => !o)}
            onClear={() => {
              if (recDebounceTimerRef.current) {
                window.clearTimeout(recDebounceTimerRef.current);
              }
              setNlPrompt("");
              setPreferences(DEFAULT_PREFERENCES);
              runRecommendations("", DEFAULT_PREFERENCES);
            }}
            description={nlPrompt}
            onDescriptionChange={setNlPrompt}
            onSubmitDescription={() => {
              if (recDebounceTimerRef.current) {
                window.clearTimeout(recDebounceTimerRef.current);
              }
              runRecommendations(nlPrompt, preferences);
            }}
            isSubmitting={recLoading}
          />
        </div>

        {/* Intent Breakdown Banner */}
        {detectedIntent && (
          <div className="mb-6 p-4 rounded-xl bg-almond-400/10 border border-almond-400/25 text-almond-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs sm:text-sm animate-fade-in">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded-md bg-almond-400/20 text-almond-200 font-bold text-xs uppercase border border-almond-400/30">
                {detectedIntent.intent_type?.replace("_", " ")}
              </span>
              <span>
                {detectedIntent.intent_type === "natural_language" && (
                  <>Extracted structured preferences while preserving complete text for TF-IDF ranking.</>
                )}
                {detectedIntent.intent_type === "similar_title" && (
                  <>Finding titles similar to <strong>"{detectedIntent.clean_title || detectedIntent.seed_title}"</strong></>
                )}
                {detectedIntent.intent_type === "genre" && (
                  <>Filtering by genre exploration metadata</>
                )}
                {detectedIntent.intent_type === "language_country" && (
                  <>Filtering by regional language: <strong>{detectedIntent.languages?.join(", ") || detectedIntent.countries?.join(", ")}</strong></>
                )}
                {detectedIntent.intent_type === "mood_theme" && (
                  <>Prioritizing moods & themes: <strong>{detectedIntent.moods?.join(", ") || detectedIntent.themes?.join(", ")}</strong></>
                )}
                {detectedIntent.intent_type === "combined" && (
                  <>Multi-attribute search query parsed successfully</>
                )}
                {detectedIntent.intent_type === "exact_title" && (
                  <>Exact TMDB lookup for <strong>"{detectedIntent.clean_title || titleQuery}"</strong></>
                )}
              </span>
            </div>
            {recStats && (
              <span className="text-surface-400 text-xs whitespace-nowrap">
                {recStats.candidates} candidates evaluated in {recStats.timeMs.toFixed(0)}ms
              </span>
            )}
          </div>
        )}

        {/* Tab Switcher: Recommendations vs TMDB Direct Results */}
        <div className="flex items-center justify-between border-b border-surface-800 mb-6">
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setActiveTab("recommendations")}
              className={`pb-3 text-sm font-semibold tracking-wide border-b-2 transition-all flex items-center gap-2 ${
                activeTab === "recommendations"
                  ? "border-almond-400 text-almond-300"
                  : "border-transparent text-surface-400 hover:text-surface-200"
              }`}
            >
              <span>Personalized Recommendations</span>
              <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface-800 text-surface-300">
                {recommendations.length}
              </span>
            </button>

            {searchResults.length > 0 && (
              <button
                type="button"
                onClick={() => setActiveTab("search")}
                className={`pb-3 text-sm font-semibold tracking-wide border-b-2 transition-all flex items-center gap-2 ${
                  activeTab === "search"
                    ? "border-almond-400 text-almond-300"
                    : "border-transparent text-surface-400 hover:text-surface-200"
                }`}
              >
                <span>Direct TMDB Matches</span>
                <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface-800 text-surface-300">
                  {searchResults.length}
                </span>
              </button>
            )}
          </div>
        </div>

        {/* Global Error Banner */}
        {(searchError || recError) && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-start justify-between gap-3 animate-fade-in">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="font-semibold">{searchError ? "Search Error" : "Recommendation Notice"}</p>
                <p className="mt-0.5 text-xs text-rose-300/90">{searchError || recError}</p>
              </div>
            </div>
            {recError && !searchError && (
              <button
                type="button"
                onClick={() => runRecommendations(nlPrompt, preferences)}
                className="px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-xs font-medium text-almond-200 border border-surface-700 transition-colors flex-shrink-0"
              >
                Try Again
              </button>
            )}
          </div>
        )}

        {/* SECTION 1: RECOMMENDATIONS TAB */}
        {activeTab === "recommendations" && (
          <div>
            {recLoading ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-xl bg-[#0b0e18] border border-almond-400/20 text-xs text-almond-200 animate-pulse">
                  <svg className="w-4 h-4 animate-spin text-almond-300 flex-shrink-0" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Searching TMDB & scoring personalized recommendations…</span>
                </div>
                <div className="results-grid">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="card p-3 space-y-3">
                      <div className="w-full h-72 rounded-xl skeleton" />
                      <div className="h-4 w-3/4 rounded skeleton" />
                      <div className="h-3 w-1/2 rounded skeleton" />
                    </div>
                  ))}
                </div>
              </div>
            ) : recommendations.length === 0 ? (
              <div className="empty-state">
                <svg className="w-16 h-16 mx-auto text-surface-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                <h3 className="text-lg font-bold text-surface-200">No recommendations match your criteria</h3>
                <p className="text-sm text-surface-400 mt-1 max-w-sm mx-auto">
                  Try adjusting your description in &ldquo;Explain in Words&rdquo; or relaxing active filters.
                </p>
              </div>
            ) : (
              <div className="results-grid" role="list" aria-label="Personalized recommendations">
                {recommendations.map((rec, index) => {
                  const item = rec.media;
                  const isFav = isFavorite(item.media_type, item.id);
                  const releaseYear = item.media_type === "movie" && item.release_date
                    ? new Date(item.release_date).getFullYear()
                    : item.media_type === "tv" && item.first_air_date
                    ? new Date(item.first_air_date).getFullYear()
                    : "N/A";

                  return (
                    <article
                      key={`${item.media_type}-${item.id}`}
                      className="card-interactive card-enter flex flex-col justify-between"
                      style={{ animationDelay: `${index * 40}ms` }}
                      onClick={() => setSelectedMedia({ mediaType: item.media_type, itemId: item.id })}
                      role="listitem"
                    >
                      <div>
                        {/* Poster with Favorite Heart */}
                        <div className="relative aspect-[2/3] w-full overflow-hidden bg-surface-900">
                          {item.poster_url ? (
                            <img
                              src={item.poster_url}
                              alt={item.title}
                              className="poster-img h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-surface-500 bg-surface-950 p-4 text-center">
                              <svg className="w-10 h-10 mb-2 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                              </svg>
                              <span className="text-xs font-medium text-surface-400">No Image</span>
                            </div>
                          )}

                          {/* Gradient shadow for text readability */}
                          <div className="absolute inset-0 bg-gradient-to-t from-[#0e1320] via-transparent to-transparent opacity-80" />

                          {/* Favorite button */}
                          <button
                            type="button"
                            onClick={(e) => handleCardFavorite(e, item.media_type, item.id)}
                            className={`favorite-btn absolute top-2.5 right-2.5 z-10 ${
                              isFav ? "favorite-btn-active" : "favorite-btn-inactive"
                            }`}
                            title={isFav ? "Remove from favorites" : "Add to favorites"}
                            aria-label={isFav ? `Remove ${item.title} from favorites` : `Add ${item.title} to favorites`}
                            aria-pressed={isFav}
                          >
                            <svg className="w-4 h-4" fill={isFav ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                            </svg>
                          </button>

                          {/* Match Score Badge */}
                          <div className="absolute bottom-2.5 left-2.5 z-10 flex items-center gap-1.5">
                            <span className="px-2 py-0.5 rounded-md bg-almond-400 text-stone-950 font-bold text-[11px] shadow">
                              {(rec.final_score * 100).toFixed(0)}% Match
                            </span>
                          </div>
                        </div>

                        {/* Title and metadata */}
                        <div className="p-3.5 pb-2">
                          <h3 className="font-bold text-surface-100 line-clamp-1 text-sm group-hover:text-almond-300 transition-colors">
                            {item.title}
                          </h3>
                          <div className="flex items-center gap-1.5 text-xs text-surface-400 mt-1">
                            <span className="uppercase text-[10px] font-semibold text-almond-300/80">{item.media_type}</span>
                            <span>•</span>
                            <span>{releaseYear}</span>
                            {item.vote_average ? (
                              <>
                                <span>•</span>
                                <span className="text-almond-300 font-medium">★ {item.vote_average.toFixed(1)}</span>
                              </>
                            ) : null}
                          </div>

                          {/* Evidence / Reason Tags */}
                          {rec.explanation?.length > 0 && (
                            <div className="mt-2.5 flex flex-wrap gap-1">
                              {rec.explanation.slice(0, 2).map((exp: ExplanationReason, i: number) => (
                                <span
                                  key={i}
                                  className="px-1.5 py-0.5 rounded bg-surface-800 text-[10px] text-surface-300 border border-surface-700/60 line-clamp-1"
                                >
                                  {exp.description}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 4 Feedback Buttons Row */}
                      <div className="p-2.5 pt-0 border-t border-surface-800/80 mt-2">
                        <div className="grid grid-cols-4 gap-1">
                          {(["like", "dislike", "watched", "more_like_this"] as FeedbackType[]).map((type) => {
                            const active = hasFeedback(item.media_type, item.id, type);
                            return (
                              <button
                                key={type}
                                type="button"
                                onClick={(e) => handleCardFeedback(e, item.media_type, item.id, type)}
                                className={`p-1.5 rounded-lg flex items-center justify-center transition-all ${
                                  getFeedbackColor(type, active)
                                } ${active ? "feedback-btn-active" : ""}`}
                                title={getFeedbackLabel(type)}
                                aria-label={getFeedbackLabel(type)}
                                aria-pressed={active}
                              >
                                {getFeedbackIcon(type, active)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* SECTION 2: TMDB DIRECT SEARCH RESULTS TAB */}
        {activeTab === "search" && (
          <div>
            {searchLoading ? (
              <div className="results-grid">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="card p-3 space-y-3">
                    <div className="w-full h-72 rounded-xl skeleton" />
                    <div className="h-4 w-3/4 rounded skeleton" />
                    <div className="h-3 w-1/2 rounded skeleton" />
                  </div>
                ))}
              </div>
            ) : searchResults.length === 0 ? (
              <div className="empty-state">
                <svg className="w-16 h-16 mx-auto text-surface-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-lg font-bold text-surface-200">No TMDB matches found</h3>
                <p className="text-sm text-surface-400 mt-1">Try another search title or query.</p>
              </div>
            ) : (
              <div className="results-grid" role="list" aria-label="TMDB search results">
                {searchResults.map((item, index) => {
                  const isFav = isFavorite(item.media_type, item.id);
                  return (
                    <article
                      key={`${item.media_type}-${item.id}`}
                      className="card-interactive card-enter flex flex-col justify-between"
                      style={{ animationDelay: `${index * 40}ms` }}
                      onClick={() => setSelectedMedia({ mediaType: item.media_type, itemId: item.id })}
                      role="listitem"
                    >
                      <div>
                        {/* Poster */}
                        <div className="relative aspect-[2/3] w-full overflow-hidden bg-surface-900">
                          {item.poster_url ? (
                            <img
                              src={item.poster_url}
                              alt={getDisplayTitle(item)}
                              className="poster-img h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-surface-500 bg-surface-950 p-4 text-center">
                              <svg className="w-10 h-10 mb-2 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                              </svg>
                              <span className="text-xs font-medium text-surface-400">No Image</span>
                            </div>
                          )}

                          {/* Favorite button */}
                          <button
                            type="button"
                            onClick={(e) => handleCardFavorite(e, item.media_type, item.id)}
                            className={`favorite-btn absolute top-2.5 right-2.5 z-10 ${
                              isFav ? "favorite-btn-active" : "favorite-btn-inactive"
                            }`}
                            title={isFav ? "Remove from favorites" : "Add to favorites"}
                            aria-label={isFav ? `Remove ${getDisplayTitle(item)} from favorites` : `Add ${getDisplayTitle(item)} to favorites`}
                            aria-pressed={isFav}
                          >
                            <svg className="w-4 h-4" fill={isFav ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                            </svg>
                          </button>
                        </div>

                        {/* Title and details */}
                        <div className="p-3.5">
                          <h3 className="font-bold text-surface-100 line-clamp-1 text-sm group-hover:text-almond-300 transition-colors">
                            {getDisplayTitle(item)}
                          </h3>
                          <div className="flex items-center gap-1.5 text-xs text-surface-400 mt-1">
                            <span className="uppercase text-[10px] font-semibold text-almond-300/80">{item.media_type}</span>
                            <span>•</span>
                            <span>{getReleaseYear(item)}</span>
                            {item.vote_average ? (
                              <>
                                <span>•</span>
                                <span className="text-almond-300 font-medium">★ {item.vote_average.toFixed(1)}</span>
                              </>
                            ) : null}
                          </div>
                          {item.overview && (
                            <p className="text-xs text-surface-400 line-clamp-2 mt-2 leading-relaxed">
                              {item.overview}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* 4 Feedback Buttons Row */}
                      <div className="p-2.5 pt-0 border-t border-surface-800/80 mt-2">
                        <div className="grid grid-cols-4 gap-1">
                          {(["like", "dislike", "watched", "more_like_this"] as FeedbackType[]).map((type) => {
                            const active = hasFeedback(item.media_type, item.id, type);
                            return (
                              <button
                                key={type}
                                type="button"
                                onClick={(e) => handleCardFeedback(e, item.media_type, item.id, type)}
                                className={`p-1.5 rounded-lg flex items-center justify-center transition-all ${
                                  getFeedbackColor(type, active)
                                } ${active ? "feedback-btn-active" : ""}`}
                                title={getFeedbackLabel(type)}
                                aria-label={getFeedbackLabel(type)}
                                aria-pressed={active}
                              >
                                {getFeedbackIcon(type, active)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-800/80 bg-[#080a11] py-6 text-center text-xs text-surface-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>
            Smart Movie Recommender — Powered exclusively by <strong>TMDB</strong>. All favorites and feedback stored locally.
          </p>
        </div>
      </footer>

      {/* In-Page Media Details Modal */}
      {selectedMedia && (
        <MediaDetailsModal
          mediaType={selectedMedia.mediaType}
          itemId={selectedMedia.itemId}
          isOpen={true}
          onClose={() => setSelectedMedia(null)}
          onMoreLikeThis={handleMoreLikeThisFromModal}
          onFavoriteChange={refreshFavoritesCount}
        />
      )}

      {/* In-Page Favorites Drawer */}
      <FavoritesDrawer
        isOpen={favoritesDrawerOpen}
        onClose={() => setFavoritesDrawerOpen(false)}
        onSelectMedia={(mediaType, itemId) => setSelectedMedia({ mediaType, itemId })}
        onRecommendFromFavorites={handleRecommendFromFavorites}
      />
    </div>
  );
}

export default App;