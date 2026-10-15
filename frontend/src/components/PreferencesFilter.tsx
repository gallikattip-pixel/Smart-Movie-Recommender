import type { UserPreference } from "../types/recommend";

interface PreferencesFilterProps {
  preferences: UserPreference;
  onChange: (updated: UserPreference) => void;
  isOpen: boolean;
  onToggleOpen: () => void;
  onClear: () => void;
  description: string;
  onDescriptionChange: (val: string) => void;
  onSubmitDescription: () => void;
  isSubmitting?: boolean;
}

const POPULAR_GENRES = [
  { id: 28, name: "Action" },
  { id: 878, name: "Sci-Fi" },
  { id: 53, name: "Thriller" },
  { id: 18, name: "Drama" },
  { id: 35, name: "Comedy" },
  { id: 80, name: "Crime" },
  { id: 9648, name: "Mystery" },
  { id: 27, name: "Horror" },
  { id: 10749, name: "Romance" },
  { id: 16, name: "Animation" },
  { id: 14, name: "Fantasy" },
  { id: 12, name: "Adventure" },
];

const MOOD_TAGS = [
  "Mind-bending",
  "Plot twists",
  "Dark & Gritty",
  "Feel-good",
  "Fast-paced",
  "Thought-provoking",
  "Heartwarming",
  "Psychological",
];

const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "hi", name: "Hindi" },
  { code: "kn", name: "Kannada" },
  { code: "ta", name: "Tamil" },
  { code: "te", name: "Telugu" },
  { code: "ml", name: "Malayalam" },
  { code: "ko", name: "Korean" },
  { code: "ja", name: "Japanese" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
];

const ERAS = [
  { label: "2020s", start: 2020, end: 2030 },
  { label: "2010s", start: 2010, end: 2019 },
  { label: "2000s", start: 2000, end: 2009 },
  { label: "90s", start: 1990, end: 1999 },
  { label: "Classics", start: 1950, end: 1989 },
];

export function PreferencesFilter({
  preferences,
  onChange,
  isOpen,
  onToggleOpen,
  onClear,
  description,
  onDescriptionChange,
  onSubmitDescription,
  isSubmitting = false,
}: PreferencesFilterProps) {
  // Compute count of active filters
  const activeCount =
    (preferences.preferred_genres?.length || 0) +
    (preferences.preferred_languages?.length || 0) +
    (preferences.preferred_moods?.length || 0) +
    (preferences.content_types?.length === 1 ? 1 : 0) +
    (preferences.era ? 1 : 0) +
    (preferences.min_vote_average ? 1 : 0) +
    (preferences.prefer_hidden_gems ? 1 : 0) +
    (description?.trim() ? 1 : 0);

  const toggleGenre = (genreId: number) => {
    const current = preferences.preferred_genres || [];
    const updated = current.includes(genreId)
      ? current.filter((id) => id !== genreId)
      : [...current, genreId];
    onChange({ ...preferences, preferred_genres: updated });
  };

  const toggleMood = (mood: string) => {
    const current = preferences.preferred_moods || [];
    const updated = current.includes(mood)
      ? current.filter((m) => m !== mood)
      : [...current, mood];
    onChange({ ...preferences, preferred_moods: updated });
  };

  const toggleLanguage = (code: string) => {
    const current = preferences.preferred_languages || [];
    const updated = current.includes(code)
      ? current.filter((c) => c !== code)
      : [...current, code];
    onChange({ ...preferences, preferred_languages: updated });
  };

  const setContentType = (type: "all" | "movie" | "tv") => {
    if (type === "all") {
      onChange({ ...preferences, content_types: ["movie", "tv"] });
    } else {
      onChange({ ...preferences, content_types: [type] });
    }
  };

  const toggleEra = (eraObj: { label: string; start: number; end: number }) => {
    if (
      preferences.era &&
      preferences.era.start_year === eraObj.start &&
      preferences.era.end_year === eraObj.end
    ) {
      onChange({ ...preferences, era: null });
    } else {
      onChange({
        ...preferences,
        era: { start_year: eraObj.start, end_year: eraObj.end },
      });
    }
  };

  const setMinRating = (rating: number | null) => {
    onChange({ ...preferences, min_vote_average: rating });
  };

  const toggleHiddenGems = () => {
    onChange({
      ...preferences,
      prefer_hidden_gems: !preferences.prefer_hidden_gems,
    });
  };

  return (
    <div className="w-full mt-3">
      {/* Toggle button */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onToggleOpen}
          className="inline-flex items-center gap-2 text-xs sm:text-sm font-medium text-surface-400 hover:text-almond-300 transition-colors py-1.5 focus:outline-none"
          aria-expanded={isOpen}
        >
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <span>{isOpen ? "Hide Filters & Preferences" : "Refine Preferences & Filters"}</span>
          {activeCount > 0 && (
            <span className="px-2 py-0.5 text-[11px] rounded-full bg-almond-400/20 text-almond-200 border border-almond-400/30">
              {activeCount} active
            </span>
          )}
        </button>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-surface-500 hover:text-rose-400 transition-colors"
          >
            Reset all
          </button>
        )}
      </div>

      {/* Expandable Filter Body */}
      {isOpen && (
        <div className="mt-3 p-4 sm:p-5 rounded-2xl bg-[#0c101b] border border-surface-800/90 shadow-xl space-y-4 animate-fade-in text-xs sm:text-sm">
          {/* Content Type Row */}
          <div>
            <span className="form-label">Type</span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setContentType("all")}
                className={`toggle-chip ${
                  preferences.content_types.length === 2 ? "toggle-chip-selected" : "toggle-chip-default"
                }`}
              >
                All Formats
              </button>
              <button
                type="button"
                onClick={() => setContentType("movie")}
                className={`toggle-chip ${
                  preferences.content_types.length === 1 && preferences.content_types.includes("movie")
                    ? "toggle-chip-selected"
                    : "toggle-chip-default"
                }`}
              >
                Movies Only
              </button>
              <button
                type="button"
                onClick={() => setContentType("tv")}
                className={`toggle-chip ${
                  preferences.content_types.length === 1 && preferences.content_types.includes("tv")
                    ? "toggle-chip-selected"
                    : "toggle-chip-default"
                }`}
              >
                TV Series Only
              </button>
            </div>
          </div>

          {/* Genres */}
          <div>
            <span className="form-label">Favorite Genres</span>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {POPULAR_GENRES.map((g) => {
                const isSelected = (preferences.preferred_genres || []).includes(g.id);
                return (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => toggleGenre(g.id)}
                    className={`toggle-chip ${isSelected ? "toggle-chip-selected" : "toggle-chip-default"}`}
                    aria-pressed={isSelected}
                  >
                    <span>{g.name}</span>
                    {isSelected && <span className="ml-1 text-almond-300">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Moods / Themes */}
          <div>
            <span className="form-label">Mood & Vibe</span>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {MOOD_TAGS.map((m) => {
                const isSelected = (preferences.preferred_moods || []).includes(m);
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => toggleMood(m)}
                    className={`toggle-chip ${isSelected ? "toggle-chip-selected" : "toggle-chip-default"}`}
                    aria-pressed={isSelected}
                  >
                    <span>{m}</span>
                    {isSelected && <span className="ml-1 text-almond-300">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Languages */}
          <div>
            <span className="form-label">Language & Region</span>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {LANGUAGES.map((l) => {
                const isSelected = (preferences.preferred_languages || []).includes(l.code);
                return (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => toggleLanguage(l.code)}
                    className={`toggle-chip ${isSelected ? "toggle-chip-selected" : "toggle-chip-default"}`}
                    aria-pressed={isSelected}
                  >
                    <span>{l.name}</span>
                    {isSelected && <span className="ml-1 text-almond-300">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Era & Rating & Hidden Gems */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-surface-800">
            {/* Era */}
            <div>
              <span className="form-label">Era</span>
              <div className="flex flex-wrap gap-1.5">
                {ERAS.map((era) => {
                  const isSelected =
                    preferences.era?.start_year === era.start &&
                    preferences.era?.end_year === era.end;
                  return (
                    <button
                      key={era.label}
                      type="button"
                      onClick={() => toggleEra(era)}
                      className={`toggle-chip ${isSelected ? "toggle-chip-selected" : "toggle-chip-default"}`}
                      aria-pressed={isSelected}
                    >
                      {era.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Minimum Rating */}
            <div>
              <span className="form-label">Min Rating (TMDB)</span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { label: "Any", val: null },
                  { label: "6.0+", val: 6.0 },
                  { label: "7.0+", val: 7.0 },
                  { label: "8.0+", val: 8.0 },
                ].map((r) => {
                  const isSelected = preferences.min_vote_average === r.val;
                  return (
                    <button
                      key={r.label}
                      type="button"
                      onClick={() => setMinRating(r.val)}
                      className={`toggle-chip ${isSelected ? "toggle-chip-selected" : "toggle-chip-default"}`}
                    >
                      {r.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Hidden Gems Toggle */}
            <div>
              <span className="form-label">Discovery Mode</span>
              <button
                type="button"
                onClick={toggleHiddenGems}
                className={`toggle-chip w-full flex items-center justify-between ${
                  preferences.prefer_hidden_gems ? "toggle-chip-selected" : "toggle-chip-default"
                }`}
                aria-pressed={preferences.prefer_hidden_gems}
              >
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-almond-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                  <span>Hidden Gems</span>
                </span>
                <span>{preferences.prefer_hidden_gems ? "ON" : "OFF"}</span>
              </button>
            </div>
          </div>

          {/* Explain in Words */}
          <div className="pt-3 border-t border-surface-800 space-y-2">
            <div className="flex items-center justify-between">
              <label
                htmlFor="nl-description-input"
                className="text-xs font-semibold text-almond-300 uppercase tracking-wider flex items-center gap-1.5"
              >
                <span>Explain in Words</span>
                <span className="text-[11px] font-normal text-surface-400 lowercase tracking-normal">(optional)</span>
              </label>
              {description && (
                <button
                  type="button"
                  onClick={() => onDescriptionChange("")}
                  className="text-xs text-surface-400 hover:text-almond-200 transition-colors"
                >
                  Clear text
                </button>
              )}
            </div>

            <textarea
              id="nl-description-input"
              rows={2}
              value={description}
              onChange={(e) => onDescriptionChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmitDescription();
                }
              }}
              placeholder="Describe what you want in your own words..."
              className="w-full bg-[#080c14] border border-surface-700/70 hover:border-surface-600 focus:border-almond-400/80 focus:ring-1 focus:ring-almond-400/30 rounded-xl text-white placeholder-surface-500 text-xs sm:text-sm p-3 transition-all resize-y leading-relaxed focus:outline-none"
            />

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={onSubmitDescription}
                disabled={isSubmitting}
                className="btn-primary text-xs px-4 py-2 font-medium"
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5 animate-spin text-stone-950" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Finding…</span>
                  </span>
                ) : (
                  "Find Recommendations"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
