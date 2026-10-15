"""Query intent parser for movie & TV recommendation.

Distinguishes between exact title searches, similar-title requests,
genre requests, mood/theme requests, language/country requests, combined queries,
and comprehensive natural-language preference descriptions.
Deterministic, rule-based, and fully testable without external LLM dependencies.
"""

import re
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from app.schemas import EraRange


# TMDB Genre ID mappings
GENRE_MAP: Dict[str, int] = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "anime": 16,
    "animated": 16,
    "cartoon": 16,
    "comedy": 35,
    "comedies": 35,
    "funny": 35,
    "crime": 80,
    "gangster": 80,
    "mob": 80,
    "documentary": 99,
    "documentaries": 99,
    "doc": 99,
    "drama": 18,
    "dramas": 18,
    "dramatic": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "historical": 36,
    "period": 36,
    "horror": 27,
    "scary": 27,
    "spooky": 27,
    "music": 10402,
    "musical": 10402,
    "musicals": 10402,
    "mystery": 9648,
    "mysteries": 9648,
    "detective": 9648,
    "whodunit": 9648,
    "romance": 10749,
    "romantic": 10749,
    "romcom": 10749,
    "love": 10749,
    "science fiction": 878,
    "sci-fi": 878,
    "scifi": 878,
    "thriller": 53,
    "thrillers": 53,
    "suspense": 53,
    "war": 10752,
    "western": 37,
    "westerns": 37,
}

# Regional language / country mapping
LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "kannada": {"lang": "kn", "country": "IN"},
    "hindi": {"lang": "hi", "country": "IN"},
    "bollywood": {"lang": "hi", "country": "IN"},
    "tamil": {"lang": "ta", "country": "IN"},
    "kollywood": {"lang": "ta", "country": "IN"},
    "telugu": {"lang": "te", "country": "IN"},
    "tollywood": {"lang": "te", "country": "IN"},
    "malayalam": {"lang": "ml", "country": "IN"},
    "mollywood": {"lang": "ml", "country": "IN"},
    "bengali": {"lang": "bn", "country": "IN"},
    "marathi": {"lang": "mr", "country": "IN"},
    "punjabi": {"lang": "pa", "country": "IN"},
    "indian": {"country": "IN"},
    "korean": {"lang": "ko", "country": "KR"},
    "k-drama": {"lang": "ko", "country": "KR", "type": "tv"},
    "kdrama": {"lang": "ko", "country": "KR", "type": "tv"},
    "japanese": {"lang": "ja", "country": "JP"},
    "french": {"lang": "fr", "country": "FR"},
    "spanish": {"lang": "es", "country": "ES"},
    "german": {"lang": "de", "country": "DE"},
    "italian": {"lang": "it", "country": "IT"},
    "chinese": {"lang": "zh", "country": "CN"},
    "mandarin": {"lang": "zh", "country": "CN"},
    "cantonese": {"lang": "zh", "country": "HK"},
    "british": {"lang": "en", "country": "GB"},
    "english": {"lang": "en"},
}

# Theme / mood keywords
THEME_KEYWORDS: Dict[str, List[str]] = {
    "mind-bending": ["mind-bending", "mind bending", "mind blowing", "mind-blowing", "mindfuck", "psychological", "thought-provoking"],
    "plot twist": ["plot twist", "plot twists", "twist ending", "twist endings", "unexpected ending", "unexpected endings", "shocking ending", "surprise ending"],
    "time travel": ["time travel", "time loop", "multiverse", "parallel universe"],
    "heist": ["heist", "robbery", "caper", "bank heist"],
    "superhero": ["superhero", "superheroes", "comic book", "marvel", "dc"],
    "space": ["space", "interstellar", "outer space", "astronaut", "astronauts", "alien", "aliens"],
    "cyberpunk": ["cyberpunk", "futuristic", "ai", "artificial intelligence", "dystopian", "dystopia"],
    "zombie": ["zombie", "zombies", "undead", "apocalypse", "post-apocalyptic"],
    "serial killer": ["serial killer", "serial killers", "psychopath", "true crime"],
    "investigation": ["investigation", "murder mystery", "detective", "police procedural"],
    "revenge": ["revenge", "vengeance", "retribution"],
    "sports": ["sports", "boxing", "football", "basketball", "cricket", "racing"],
    "coming-of-age": ["coming of age", "coming-of-age", "teen", "high school", "youth"],
}

MOOD_KEYWORDS: Dict[str, List[str]] = {
    "dark and gritty": ["dark and gritty", "dark", "gritty", "bleak", "neo-noir", "noir", "somber"],
    "heartwarming": ["heartwarming", "feel-good", "feel good", "uplifting", "comforting", "wholesome", "sweet"],
    "high adrenaline": ["high adrenaline", "adrenaline", "action-packed", "fast-paced", "intense", "edge of your seat", "thrilling"],
    "emotional": ["emotional", "tearjerker", "touching", "moving", "sad"],
    "cozy": ["cozy", "relaxing", "lighthearted", "chill"],
    "creepy": ["creepy", "unsettling", "eerie", "haunting"],
}

PACING_KEYWORDS: Dict[str, List[str]] = {
    "fast-paced": ["fast-paced", "fast paced", "high adrenaline", "non-stop", "action-packed", "quick", "rapid", "breathless"],
    "slow-paced": ["slow-burn", "slow burn", "slow-paced", "slow paced", "deliberate", "atmospheric", "methodical"],
}

ENDING_KEYWORDS: Dict[str, List[str]] = {
    "twist ending": ["plot twist", "plot twists", "twist ending", "twist endings", "unexpected ending", "unexpected endings", "shocking ending", "surprise ending"],
    "happy ending": ["happy ending", "feel-good ending", "uplifting ending", "satisfying ending"],
    "tragic ending": ["tragic ending", "sad ending", "dark ending", "depressing ending", "bleak ending"],
    "open ending": ["open ending", "ambiguous ending", "unresolved ending"],
}

CHARACTER_KEYWORDS: List[str] = [
    "detective", "anti-hero", "astronaut", "psychopath", "serial killer",
    "scientist", "cop", "police officer", "hitman", "spy", "secret agent",
    "robot", "cyborg", "alien", "gangster", "superhero"
]

# Patterns for similar title queries
SIMILAR_PATTERNS = [
    re.compile(r"^(?:movies?|films?|shows?|series|tv\s+shows?)\s+(?:like|similar\s+to|resembling)\s+(.+)$", re.IGNORECASE),
    re.compile(r"^(?:something|anything|more)\s+like\s+(.+)$", re.IGNORECASE),
    re.compile(r"^similar\s+to\s+(.+)$", re.IGNORECASE),
    re.compile(r"^like\s+(.+)$", re.IGNORECASE),
    re.compile(r"^(.+)\s+(?:recommendations|suggestions|lookalikes|alternatives)$", re.IGNORECASE),
    re.compile(r"^if\s+i\s+liked\s+(.+?)(?:,\s*what\s+should\s+i\s+watch|\?|$)", re.IGNORECASE),
]

# Recommendation intent trigger words
RECOMMENDATION_TRIGGERS = [
    "best", "top", "recommend", "recommendation", "recommendations", "suggest",
    "suggestions", "what to watch", "watch next", "hidden gems", "underrated",
    "must watch", "good", "great", "popular", "trending", "recent", "looking for",
    "want to watch", "find me", "show me", "give me", "something with",
]


class QueryIntent(BaseModel):
    """Parsed search intent."""

    raw_query: str
    intent_type: Literal["exact_title", "similar_title", "genre", "mood_theme", "language_country", "combined", "natural_language"]
    is_recommendation: bool
    clean_title: Optional[str] = None
    seed_titles: List[str] = Field(default_factory=list)
    media_type: Literal["multi", "movie", "tv"] = "multi"
    genre_ids: List[int] = Field(default_factory=list)
    genre_names: List[str] = Field(default_factory=list)
    excluded_genre_ids: List[int] = Field(default_factory=list)
    excluded_genre_names: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    excluded_themes: List[str] = Field(default_factory=list)
    moods: List[str] = Field(default_factory=list)
    pacing: List[str] = Field(default_factory=list)
    endings: List[str] = Field(default_factory=list)
    characters: List[str] = Field(default_factory=list)
    era: Optional[EraRange] = None
    min_rating: Optional[float] = None
    prefer_hidden_gems: bool = False
    explanation_summary: str = ""


def parse_query_intent(query: str) -> QueryIntent:
    """
    Parse a user query or natural language description deterministically into a QueryIntent structure.

    Distinguishes exact title searches from recommendation-oriented queries and natural-language prompts.
    """
    q = query.strip()
    if not q:
        return QueryIntent(
            raw_query="",
            intent_type="exact_title",
            is_recommendation=False,
            explanation_summary="Empty search query",
        )

    q_lower = q.lower()

    # 1. Check for single similar title request pattern
    for pattern in SIMILAR_PATTERNS:
        match = pattern.match(q)
        if match:
            seed_title = match.group(1).strip().strip("\"'.,?!")
            if seed_title:
                media_type: Literal["multi", "movie", "tv"] = "multi"
                if re.search(r"\b(movie|movies|film|films)\b", q_lower):
                    media_type = "movie"
                elif re.search(r"\b(show|shows|series|tv)\b", q_lower):
                    media_type = "tv"

                return QueryIntent(
                    raw_query=q,
                    intent_type="similar_title",
                    is_recommendation=True,
                    clean_title=seed_title,
                    seed_titles=[seed_title],
                    media_type=media_type,
                    explanation_summary=f"Titles similar to '{seed_title}'",
                )

    # 2. Extract Exclusions (Negative Preferences)
    excluded_genre_ids: List[int] = []
    excluded_genre_names: List[str] = []
    excluded_themes: List[str] = []

    # Find exclusion segments like "no horror", "avoid comedies", "without romance", "avoid comedy and horror"
    exclusion_matches = re.finditer(
        r"\b(?:no|not|without|exclude|excluding|avoid|don't want|dont want|skip)\s+([a-zA-Z0-9\s\-]+?)(?:[.,;!?]|\bbut\b|\bwith\b|\bfor\b|$)",
        q_lower
    )
    exclusion_text = ""
    for m in exclusion_matches:
        seg = m.group(1).strip()
        exclusion_text += " " + seg
        for g_name, g_id in GENRE_MAP.items():
            if re.search(r"\b" + re.escape(g_name) + r"\b", seg):
                if g_id not in excluded_genre_ids:
                    excluded_genre_ids.append(g_id)
                    excluded_genre_names.append(g_name.title())
        for t_name, variants in THEME_KEYWORDS.items():
            for v in variants:
                if re.search(r"\b" + re.escape(v) + r"\b", seg):
                    if t_name not in excluded_themes:
                        excluded_themes.append(t_name)

    # 3. Extract media type
    media_type: Literal["multi", "movie", "tv"] = "multi"
    if re.search(r"\b(movies|movie|films|film|cinema)\b", q_lower):
        media_type = "movie"
    elif re.search(r"\b(shows|show|series|tv series|tv show|tv)\b", q_lower):
        media_type = "tv"

    # 4. Extract seed titles from natural language descriptions
    # e.g., "similar to Inception or Blade Runner", "like Interstellar"
    extracted_seed_titles: List[str] = []
    for m in re.finditer(
        r"\b(?:similar to|like|reminiscent of|in the style of)\s+([^.,;!?\n]+?)(?:[.,;!?\n]|\bwith\b|\bno\b|\bavoid\b|\bwithout\b|$)",
        q,
        re.IGNORECASE
    ):
        raw_segment = m.group(1).strip()
        chunks = re.split(r"\b(?:or|and)\b|,", raw_segment)
        for chunk in chunks:
            cand = chunk.strip().strip("\"'")
            cand = re.sub(r"\b(movies?|films?|shows?|series)\b.*$", "", cand, flags=re.IGNORECASE).strip()
            if cand and len(cand) >= 2 and cand.lower() not in ["movies", "films", "tv", "shows", "series", "something", "anything"]:
                if cand not in extracted_seed_titles:
                    extracted_seed_titles.append(cand)

    # 5. Extract languages and countries
    extracted_languages: List[str] = []
    extracted_countries: List[str] = []
    has_language_or_country = False

    for term, meta in LANGUAGE_MAP.items():
        if re.search(r"\b" + re.escape(term) + r"\b", q_lower):
            has_language_or_country = True
            if "lang" in meta and meta["lang"] not in extracted_languages:
                extracted_languages.append(meta["lang"])
            if "country" in meta and meta["country"] not in extracted_countries:
                extracted_countries.append(meta["country"])
            if "type" in meta:
                media_type = meta["type"]  # type: ignore

    # 6. Extract positive genres (excluding those mentioned in exclusion_text)
    extracted_genre_ids: List[int] = []
    extracted_genre_names: List[str] = []
    for g_name, g_id in GENRE_MAP.items():
        if re.search(r"\b" + re.escape(g_name) + r"\b", q_lower):
            # Only add as positive if NOT part of an exclusion segment
            if g_id not in excluded_genre_ids:
                if g_id not in extracted_genre_ids:
                    extracted_genre_ids.append(g_id)
                    extracted_genre_names.append(g_name.title())

    # 7. Extract themes (positive)
    extracted_themes: List[str] = []
    for theme_name, variants in THEME_KEYWORDS.items():
        if theme_name in excluded_themes:
            continue
        for variant in variants:
            if re.search(r"\b" + re.escape(variant) + r"\b", q_lower):
                if theme_name not in extracted_themes:
                    extracted_themes.append(theme_name)
                break

    # 8. Extract moods
    extracted_moods: List[str] = []
    for mood_name, variants in MOOD_KEYWORDS.items():
        for variant in variants:
            if re.search(r"\b" + re.escape(variant) + r"\b", q_lower):
                if mood_name not in extracted_moods:
                    extracted_moods.append(mood_name)
                break

    # 9. Extract pacing
    extracted_pacing: List[str] = []
    for pacing_name, variants in PACING_KEYWORDS.items():
        for variant in variants:
            if re.search(r"\b" + re.escape(variant) + r"\b", q_lower):
                if pacing_name not in extracted_pacing:
                    extracted_pacing.append(pacing_name)
                break

    # 10. Extract endings
    extracted_endings: List[str] = []
    for ending_name, variants in ENDING_KEYWORDS.items():
        for variant in variants:
            if re.search(r"\b" + re.escape(variant) + r"\b", q_lower):
                if ending_name not in extracted_endings:
                    extracted_endings.append(ending_name)
                break

    # 11. Extract characters
    extracted_characters: List[str] = []
    for char in CHARACTER_KEYWORDS:
        if re.search(r"\b" + re.escape(char) + r"\b", q_lower):
            if char not in extracted_characters:
                extracted_characters.append(char)

    # 12. Extract era / time
    era: Optional[EraRange] = None
    # Explicit years: "after 2010", "released after 2015", "from 2020 onwards"
    year_after_match = re.search(r"\b(?:after|from|since)\s+(\d{4})\b", q_lower)
    year_before_match = re.search(r"\b(?:before|prior\s+to|until)\s+(\d{4})\b", q_lower)
    year_between_match = re.search(r"\b(?:between|from)\s+(\d{4})\s+(?:and|to)\s+(\d{4})\b", q_lower)

    if year_between_match:
        era = EraRange(start_year=int(year_between_match.group(1)), end_year=int(year_between_match.group(2)))
    elif year_after_match:
        era = EraRange(start_year=int(year_after_match.group(1)))
    elif year_before_match:
        era = EraRange(end_year=int(year_before_match.group(1)))
    elif re.search(r"\b(recent|new|latest|contemporary|current)\b", q_lower):
        era = EraRange(start_year=2020)
    elif re.search(r"\b(90s|1990s)\b", q_lower):
        era = EraRange(start_year=1990, end_year=1999)
    elif re.search(r"\b(80s|1980s)\b", q_lower):
        era = EraRange(start_year=1980, end_year=1989)
    elif re.search(r"\b(2000s|00s)\b", q_lower):
        era = EraRange(start_year=2000, end_year=2009)
    elif re.search(r"\b(2010s|10s)\b", q_lower):
        era = EraRange(start_year=2010, end_year=2019)
    elif re.search(r"\b(classic|classics|golden age|vintage|old)\b", q_lower):
        era = EraRange(end_year=1985)

    # 13. Extract hidden gems / popularity / ratings
    prefer_hidden_gems = bool(re.search(r"\b(hidden gems?|underrated|lesser known|indie|overlooked)\b", q_lower))
    min_rating: Optional[float] = None
    rating_match = re.search(r"\b(rated|rating|imdb)\s*(?:above|over|>|>=)?\s*([0-9](?:\.[0-9])?)\b", q_lower)
    if rating_match:
        try:
            val = float(rating_match.group(2))
            if 0.0 <= val <= 10.0:
                min_rating = val
        except ValueError:
            pass

    # 14. Recommendation triggers check
    has_rec_trigger = any(re.search(r"\b" + re.escape(trig) + r"\b", q_lower) for trig in RECOMMENDATION_TRIGGERS)

    # Check if query has natural language conversational sentence structure or multiline prompt
    word_count = len(q.split())
    has_conversational_marker = bool(
        re.search(r"\b(i'm|im|i am|i want|i'd like|id like|looking for|recommend me|what should i watch|can you|suggest me|give me|something with|avoid|no horror|without)\b", q_lower)
        or "\n" in q
        or len(re.findall(r"[.?!;]", q)) >= 1
        or (word_count >= 8 and (excluded_genre_ids or extracted_pacing or extracted_endings or extracted_seed_titles))
    )

    # 15. Count discovery dimensions matched
    dimensions_count = (
        (1 if has_language_or_country else 0)
        + (1 if extracted_genre_ids else 0)
        + (1 if extracted_themes else 0)
        + (1 if extracted_moods else 0)
        + (1 if extracted_pacing else 0)
        + (1 if extracted_endings else 0)
        + (1 if extracted_characters else 0)
        + (1 if excluded_genre_ids or excluded_themes else 0)
        + (1 if extracted_seed_titles else 0)
        + (1 if era else 0)
        + (1 if prefer_hidden_gems else 0)
    )

    # Natural Language Detailed Prompt Handling
    if has_conversational_marker and dimensions_count >= 1:
        summary_parts = []
        if extracted_languages:
            summary_parts.append(f"lang: {'/'.join(extracted_languages).upper()}")
        if extracted_genre_names:
            summary_parts.append(f"genres: {', '.join(extracted_genre_names)}")
        if excluded_genre_names:
            summary_parts.append(f"exclude: {', '.join(excluded_genre_names)}")
        if extracted_themes:
            summary_parts.append(f"themes: {', '.join(extracted_themes)}")
        if extracted_moods:
            summary_parts.append(f"mood: {', '.join(extracted_moods)}")
        if extracted_pacing:
            summary_parts.append(f"pacing: {', '.join(extracted_pacing)}")
        if extracted_endings:
            summary_parts.append(f"ending: {', '.join(extracted_endings)}")
        if extracted_seed_titles:
            summary_parts.append(f"similar to: {', '.join(extracted_seed_titles)}")
        if era:
            summary_parts.append(f"era: {era.start_year or 'any'}-{era.end_year or 'present'}")

        return QueryIntent(
            raw_query=q,
            intent_type="natural_language",
            is_recommendation=True,
            media_type=media_type,
            clean_title=extracted_seed_titles[0] if extracted_seed_titles else None,
            seed_titles=extracted_seed_titles,
            genre_ids=extracted_genre_ids,
            genre_names=extracted_genre_names,
            excluded_genre_ids=excluded_genre_ids,
            excluded_genre_names=excluded_genre_names,
            languages=extracted_languages,
            countries=extracted_countries,
            themes=extracted_themes,
            excluded_themes=excluded_themes,
            moods=extracted_moods,
            pacing=extracted_pacing,
            endings=extracted_endings,
            characters=extracted_characters,
            era=era,
            min_rating=min_rating,
            prefer_hidden_gems=prefer_hidden_gems,
            explanation_summary="Natural language description: " + "; ".join(summary_parts) if summary_parts else "Detailed recommendation description",
        )

    # 16. Combined multi-attribute queries (e.g., "Recent Indian mystery thrillers with unexpected endings")
    if dimensions_count >= 2:
        summary_parts = []
        if extracted_languages:
            summary_parts.append("/".join(extracted_languages).upper())
        if extracted_genre_names:
            summary_parts.append(", ".join(extracted_genre_names))
        if extracted_themes:
            summary_parts.append(f"themes: {', '.join(extracted_themes)}")
        if extracted_moods:
            summary_parts.append(f"mood: {', '.join(extracted_moods)}")
        if era:
            summary_parts.append(f"era: {era.start_year or ''}-{era.end_year or ''}")

        return QueryIntent(
            raw_query=q,
            intent_type="combined",
            is_recommendation=True,
            media_type=media_type,
            clean_title=extracted_seed_titles[0] if extracted_seed_titles else None,
            seed_titles=extracted_seed_titles,
            genre_ids=extracted_genre_ids,
            genre_names=extracted_genre_names,
            excluded_genre_ids=excluded_genre_ids,
            excluded_genre_names=excluded_genre_names,
            languages=extracted_languages,
            countries=extracted_countries,
            themes=extracted_themes,
            excluded_themes=excluded_themes,
            moods=extracted_moods,
            pacing=extracted_pacing,
            endings=extracted_endings,
            characters=extracted_characters,
            era=era,
            min_rating=min_rating,
            prefer_hidden_gems=prefer_hidden_gems,
            explanation_summary="Combined discovery: " + "; ".join(summary_parts),
        )

    # 17. Regional queries
    if has_language_or_country and (has_rec_trigger or media_type != "multi" or extracted_genre_ids):
        return QueryIntent(
            raw_query=q,
            intent_type="language_country",
            is_recommendation=True,
            media_type=media_type,
            clean_title=extracted_seed_titles[0] if extracted_seed_titles else None,
            seed_titles=extracted_seed_titles,
            genre_ids=extracted_genre_ids,
            genre_names=extracted_genre_names,
            excluded_genre_ids=excluded_genre_ids,
            excluded_genre_names=excluded_genre_names,
            languages=extracted_languages,
            countries=extracted_countries,
            themes=extracted_themes,
            excluded_themes=excluded_themes,
            moods=extracted_moods,
            pacing=extracted_pacing,
            endings=extracted_endings,
            characters=extracted_characters,
            era=era,
            min_rating=min_rating,
            prefer_hidden_gems=prefer_hidden_gems,
            explanation_summary=f"Regional search ({'/'.join(extracted_languages or extracted_countries)})",
        )

    # 18. Mood & Theme queries
    if (extracted_themes or extracted_moods) and (has_rec_trigger or media_type != "multi" or extracted_genre_ids):
        return QueryIntent(
            raw_query=q,
            intent_type="mood_theme",
            is_recommendation=True,
            media_type=media_type,
            clean_title=extracted_seed_titles[0] if extracted_seed_titles else None,
            seed_titles=extracted_seed_titles,
            genre_ids=extracted_genre_ids,
            genre_names=extracted_genre_names,
            excluded_genre_ids=excluded_genre_ids,
            excluded_genre_names=excluded_genre_names,
            languages=extracted_languages,
            countries=extracted_countries,
            themes=extracted_themes,
            excluded_themes=excluded_themes,
            moods=extracted_moods,
            pacing=extracted_pacing,
            endings=extracted_endings,
            characters=extracted_characters,
            era=era,
            min_rating=min_rating,
            prefer_hidden_gems=prefer_hidden_gems,
            explanation_summary=f"Mood & theme: {', '.join(extracted_themes + extracted_moods)}",
        )

    # 19. Plural genre requests like "psychological thrillers", "action movies", "comedies"
    if extracted_genre_ids and (
        has_rec_trigger
        or media_type != "multi"
        or any(w in q_lower for w in ["movies", "films", "shows", "series", "thrillers", "comedies", "dramas"])
    ):
        return QueryIntent(
            raw_query=q,
            intent_type="genre",
            is_recommendation=True,
            media_type=media_type,
            clean_title=extracted_seed_titles[0] if extracted_seed_titles else None,
            seed_titles=extracted_seed_titles,
            genre_ids=extracted_genre_ids,
            genre_names=extracted_genre_names,
            excluded_genre_ids=excluded_genre_ids,
            excluded_genre_names=excluded_genre_names,
            languages=extracted_languages,
            countries=extracted_countries,
            themes=extracted_themes,
            excluded_themes=excluded_themes,
            moods=extracted_moods,
            pacing=extracted_pacing,
            endings=extracted_endings,
            characters=extracted_characters,
            era=era,
            min_rating=min_rating,
            prefer_hidden_gems=prefer_hidden_gems,
            explanation_summary=f"Genre exploration: {', '.join(extracted_genre_names)}",
        )

    # 20. Otherwise: It's an exact title search! e.g. "Baahubali", "Inception", "The Dark Knight", "Breaking Bad"
    return QueryIntent(
        raw_query=q,
        intent_type="exact_title",
        is_recommendation=False,
        clean_title=q,
        media_type=media_type,
        explanation_summary=f"Direct search for '{q}'",
    )
