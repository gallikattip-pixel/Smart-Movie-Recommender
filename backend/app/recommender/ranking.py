"""Ranking and similarity for recommendations.

Implements TF-IDF + cosine similarity for content-based ranking,
plus weighted preference scoring.
"""

from typing import List, Dict, Set, Optional, Tuple
from collections import Counter
import math
import re

from app.schemas import (
    MediaDetailsResponse,
    UserPreference,
    RecommendationItem,
    ExplanationReason,
)
from app.recommender.graph import MetadataGraph, GraphNode


# Stop words for TF-IDF
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "were", "been", "be",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "what", "which",
    "who", "whom", "whose", "where", "when", "why", "how", "all", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "now"
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into words."""
    if not text:
        return []
    # Lowercase and split on non-alphanumeric
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())
    return [w for w in words if w not in STOP_WORDS]


def build_corpus(documents: List[str]) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Build TF-IDF corpus from documents.
    
    Returns:
        vocab: word -> index mapping
        idf: word -> IDF score
    """
    if not documents:
        return {}, {}

    # Count document frequency
    doc_freq = Counter()
    total_docs = len(documents)

    for doc in documents:
        tokens = set(tokenize(doc))
        for token in tokens:
            doc_freq[token] += 1

    # Compute IDF
    idf = {}
    for token, df in doc_freq.items():
        idf[token] = math.log(total_docs / df)

    # Build vocabulary
    vocab = {token: i for i, token in enumerate(doc_freq.keys())}

    return vocab, idf


def compute_tfidf_vector(text: str, vocab: Dict[str, int], idf: Dict[str, float]) -> Dict[int, float]:
    """Compute TF-IDF vector for a document."""
    tokens = tokenize(text)
    if not tokens:
        return {}

    tf = Counter(tokens)
    max_tf = max(tf.values()) if tf else 1

    vector = {}
    for token, count in tf.items():
        if token in vocab and token in idf:
            tf_normalized = count / max_tf
            vector[vocab[token]] = tf_normalized * idf[token]

    return vector


def cosine_similarity(vec1: Dict[int, float], vec2: Dict[int, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    if not vec1 or not vec2:
        return 0.0

    # Dot product
    dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in vec1 if k in vec2)

    # Magnitudes
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def build_content_corpus(candidates: List[MediaDetailsResponse]) -> Tuple[Dict[str, int], Dict[str, float], Dict[int, Dict[int, float]]]:
    """
    Build TF-IDF corpus from candidate media content.
    
    Returns:
        vocab, idf, vectors (media_id -> vector)
    """
    documents = []
    media_ids = []

    for media in candidates:
        # Combine overview, tagline, keywords, genres, cast, and directors for content
        parts = []
        if media.overview:
            parts.append(media.overview)
        if media.tagline:
            parts.append(media.tagline)
        parts.extend([k.name for k in media.keywords])
        parts.extend([g.name for g in media.genres])
        parts.extend([c.name for c in media.cast[:5]])
        if hasattr(media, "directors") and media.directors:
            parts.extend([d.name for d in media.directors[:2]])

        doc = " ".join(parts)
        documents.append(doc)
        media_ids.append(media.id)

    vocab, idf = build_corpus(documents)

    vectors = {}
    for i, doc in enumerate(documents):
        vectors[media_ids[i]] = compute_tfidf_vector(doc, vocab, idf)

    return vocab, idf, vectors


def compute_content_similarity(
    query_vector: Dict[int, float],
    candidate_vectors: Dict[int, Dict[int, float]],
) -> Dict[int, float]:
    """Compute cosine similarity between query and all candidates."""
    return {
        media_id: cosine_similarity(query_vector, vec)
        for media_id, vec in candidate_vectors.items()
    }


def build_preference_query_vector(
    prefs: UserPreference,
    vocab: Optional[Dict[str, int]] = None,
    idf: Optional[Dict[str, float]] = None,
) -> Dict[int, float]:
    """
    Build a synthetic query vector from user preferences.
    
    This creates a "virtual document" representing what the user likes.
    """
    parts = []

    # Include explicit search or recommendation query if present
    if hasattr(prefs, "query") and prefs.query:
        parts.append(prefs.query)

    # Add preferred genres
    genre_names = {
        28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
        80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
        14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
        9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
        10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
    }
    for g_id in prefs.preferred_genres:
        name = genre_names.get(g_id)
        if name:
            parts.append(name)

    # Add preferred languages
    parts.extend(prefs.preferred_languages)

    # Add preferred countries
    parts.extend(prefs.preferred_countries)

    # Add themes and moods
    parts.extend(prefs.preferred_themes)
    parts.extend(prefs.preferred_moods)

    # Add pacing and endings
    parts.extend(prefs.preferred_pacing)
    parts.extend(prefs.preferred_endings)

    query_text = " ".join(parts)

    if vocab is not None and idf is not None:
        return compute_tfidf_vector(query_text, vocab, idf)

    # Fallback to pseudo-vocabulary if vocab/idf not supplied
    tokens = tokenize(query_text)
    tf = Counter(tokens)
    max_tf = max(tf.values()) if tf else 1

    vector = {}
    for token, count in tf.items():
        idx = hash(token) % 10000
        vector[idx] = (count / max_tf) * 1.0

    return vector


def compute_preference_score(media: MediaDetailsResponse, prefs: UserPreference) -> Tuple[float, List[ExplanationReason]]:
    """
    Compute weighted preference match score for a candidate.
    
    Returns:
        (score 0-1, explanation reasons)
    """
    score = 0.0
    reasons: List[ExplanationReason] = []
    max_score = 0.0

    # Genre match (weight: 0.30)
    if prefs.preferred_genres:
        max_score += 0.30
        candidate_genres = {g.id for g in media.genres}
        matches = set(prefs.preferred_genres) & candidate_genres
        if matches:
            genre_score = len(matches) / max(len(prefs.preferred_genres), len(candidate_genres))
            score += 0.30 * genre_score
            reasons.append(ExplanationReason(
                type="genre",
                description=f"Matches {len(matches)} preferred genre(s): {', '.join(g.name for g in media.genres if g.id in matches)}",
                weight=0.30 * genre_score
            ))

    # Excluded genre penalty
    if prefs.excluded_genres:
        candidate_genres = {g.id for g in media.genres}
        if set(prefs.excluded_genres) & candidate_genres:
            return 0.0, [ExplanationReason(
                type="genre",
                description="Contains excluded genre",
                weight=0.0
            )]

    # Language match (weight: 0.15)
    if prefs.preferred_languages:
        max_score += 0.15
        if media.original_language in prefs.preferred_languages:
            score += 0.15
            reasons.append(ExplanationReason(
                type="language",
                description=f"In preferred language: {media.original_language}",
                weight=0.15
            ))

    # Country match (weight: 0.10)
    if prefs.preferred_countries:
        max_score += 0.10
        candidate_countries = {c.iso_3166_1 for c in media.production_countries if c.iso_3166_1}
        matches = set(prefs.preferred_countries) & candidate_countries
        if matches:
            country_score = len(matches) / len(prefs.preferred_countries)
            score += 0.10 * country_score
            reasons.append(ExplanationReason(
                type="country",
                description=f"From preferred country: {', '.join(matches)}",
                weight=0.10 * country_score
            ))

    # Content type (weight: 0.05)
    max_score += 0.05
    if media.media_type in prefs.content_types:
        score += 0.05
        reasons.append(ExplanationReason(
            type="content_type",
            description=f"{media.media_type.capitalize()} matches your preference",
            weight=0.05
        ))

    # Era match (weight: 0.10)
    if prefs.era:
        max_score += 0.10
        year = None
        if media.media_type == "movie" and media.release_date:
            try:
                year = int(media.release_date[:4])
            except (ValueError, IndexError):
                pass
        elif media.media_type == "tv" and media.first_air_date:
            try:
                year = int(media.first_air_date[:4])
            except (ValueError, IndexError):
                pass

        if year:
            in_era = True
            if prefs.era.start_year and year < prefs.era.start_year:
                in_era = False
            if prefs.era.end_year and year > prefs.era.end_year:
                in_era = False

            if in_era:
                score += 0.10
                reasons.append(ExplanationReason(
                    type="era",
                    description=f"Released in preferred era ({prefs.era.start_year or '?'} - {prefs.era.end_year or 'present'})",
                    weight=0.10
                ))

    # Rating match (weight: 0.10)
    if prefs.min_vote_average is not None:
        max_score += 0.10
        if media.vote_average is not None and media.vote_average >= prefs.min_vote_average:
            # Bonus for higher rating
            rating_bonus = min((media.vote_average - prefs.min_vote_average) / (10.0 - prefs.min_vote_average), 1.0)
            score += 0.10 * rating_bonus
            reasons.append(ExplanationReason(
                type="rating",
                description=f"Rating {media.vote_average:.1f} meets minimum {prefs.min_vote_average}",
                weight=0.10 * rating_bonus
            ))
        else:
            return 0.0, [ExplanationReason(
                type="rating",
                description=f"Rating below minimum {prefs.min_vote_average}",
                weight=0.0
            )]

    # Theme/mood match (weight: 0.10) - from keywords
    if prefs.preferred_themes or prefs.preferred_moods:
        max_score += 0.10
        candidate_keywords = {k.name.lower() for k in media.keywords}
        theme_matches = set(t.lower() for t in prefs.preferred_themes) & candidate_keywords
        mood_matches = set(m.lower() for m in prefs.preferred_moods) & candidate_keywords
        total_matches = len(theme_matches) + len(mood_matches)
        if total_matches > 0:
            score += 0.10 * min(total_matches / 3.0, 1.0)
            if theme_matches:
                reasons.append(ExplanationReason(
                    type="theme",
                    description=f"Matches themes: {', '.join(theme_matches)}",
                    weight=0.05
                ))
            if mood_matches:
                reasons.append(ExplanationReason(
                    type="mood",
                    description=f"Matches moods: {', '.join(mood_matches)}",
                    weight=0.05
                ))

    # Excluded theme penalty
    if prefs.excluded_themes:
        candidate_keywords = {k.name.lower() for k in media.keywords}
        if set(t.lower() for t in prefs.excluded_themes) & candidate_keywords:
            return 0.0, [ExplanationReason(
                type="theme",
                description="Contains excluded theme",
                weight=0.0
            )]

    # Pacing match (weight: 0.05)
    if hasattr(prefs, "preferred_pacing") and prefs.preferred_pacing:
        max_score += 0.05
        candidate_text = ((media.overview or "") + " " + " ".join(k.name for k in media.keywords)).lower()
        pacing_matches = [
            p for p in prefs.preferred_pacing
            if p.lower() in candidate_text or any(w in candidate_text for w in p.lower().split("-"))
        ]
        if pacing_matches:
            score += 0.05
            reasons.append(ExplanationReason(
                type="theme",
                description=f"Matches pacing preference: {', '.join(pacing_matches)}",
                weight=0.05
            ))

    # Ending match (weight: 0.05)
    if hasattr(prefs, "preferred_endings") and prefs.preferred_endings:
        max_score += 0.05
        candidate_text = ((media.overview or "") + " " + " ".join(k.name for k in media.keywords)).lower()
        ending_matches = [
            e for e in prefs.preferred_endings
            if e.lower() in candidate_text or any(w in candidate_text for w in e.lower().split())
        ]
        if ending_matches:
            score += 0.05
            reasons.append(ExplanationReason(
                type="theme",
                description=f"Matches ending preference: {', '.join(ending_matches)}",
                weight=0.05
            ))

    # Hidden gems bonus (weight: 0.05)
    if prefs.prefer_hidden_gems:
        max_score += 0.05
        # Lower popularity = more hidden
        if media.popularity < 50:
            score += 0.05
            reasons.append(ExplanationReason(
                type="hidden_gem",
                description="Lesser-known title (hidden gem)",
                weight=0.05
            ))

    # Similar to favorites (weight: 0.15)
    if prefs.favorite_titles:
        max_score += 0.15
        # This is a placeholder - actual similarity computed via graph/TF-IDF
        # Here we just give a base score if favorites exist
        score += 0.15 * 0.5  # Partial credit
        reasons.append(ExplanationReason(
            type="similar_to_favorite",
            description="Similar to your favorite titles",
            weight=0.075
        ))

    # Dislike feedback: completely exclude titles the user explicitly disliked
    if hasattr(prefs, "feedback_dislikes") and prefs.feedback_dislikes:
        disliked_ids = {d.item_id for d in prefs.feedback_dislikes if d.media_type == media.media_type}
        if media.id in disliked_ids:
            return 0.0, [ExplanationReason(
                type="theme",
                description="Excluded based on your dislike feedback",
                weight=0.0
            )]

    # Like feedback: bonus for liked titles or titles matching liked characteristics
    if hasattr(prefs, "feedback_likes") and prefs.feedback_likes:
        liked_ids = {l.item_id for l in prefs.feedback_likes if l.media_type == media.media_type}
        if media.id in liked_ids:
            score += 0.20
            reasons.append(ExplanationReason(
                type="similar_to_favorite",
                description="Matches a title you liked",
                weight=0.20
            ))

    # Normalize
    if max_score > 0:
        score = score / max_score

    return min(score, 1.0), reasons


def combine_scores(
    content_sim: float,
    preference_score: float,
    graph_path_score: float = 0.0,
    weights: Tuple[float, float, float] = (0.4, 0.5, 0.1),
) -> float:
    """Combine multiple scores into final ranking score."""
    w_content, w_pref, w_graph = weights
    total = w_content + w_pref + w_graph
    return (
        content_sim * w_content +
        preference_score * w_pref +
        graph_path_score * w_graph
    ) / total


def rank_candidates(
    candidates: List[MediaDetailsResponse],
    prefs: UserPreference,
    graph: Optional[MetadataGraph] = None,
    favorite_ids: Optional[Set[int]] = None,
) -> List[RecommendationItem]:
    """
    Rank candidates using combined content similarity and preference scoring.
    
    Returns sorted list of RecommendationItem with scores and explanations.
    """
    if not candidates:
        return []

    # Build TF-IDF corpus for content similarity
    vocab, idf, candidate_vectors = build_content_corpus(candidates)

    # Build query vector from preferences using candidate vocabulary and IDF
    query_vector = build_preference_query_vector(prefs, vocab, idf)

    # Compute content similarity
    content_sims = compute_content_similarity(query_vector, candidate_vectors)

    # Compute preference scores and explanations
    results: List[RecommendationItem] = []

    for media in candidates:
        # Skip if already in favorites (will be filtered upstream)
        if favorite_ids and media.id in favorite_ids:
            continue

        # Content similarity
        content_sim = content_sims.get(media.id, 0.0)

        # Preference score
        pref_score, reasons = compute_preference_score(media, prefs)

        # Graph path score (if graph available)
        graph_score = 0.0
        graph_path = None
        if graph and favorite_ids:
            # Check if there's a path from any favorite
            min_path_cost = float('inf')
            best_path = None
            for fav_id in favorite_ids:
                if graph.has_node(fav_id) and graph.has_node(media.id):
                    # Could do path finding here, but for now use edge cost
                    neighbors = graph.get_neighbors(fav_id)
                    for edge in neighbors:
                        if edge.target == media.id:
                            if edge.cost < min_path_cost:
                                min_path_cost = edge.cost
                                best_path = [fav_id, media.id]
            if best_path:
                # Convert cost to similarity (lower cost = higher similarity)
                graph_score = max(0.0, 1.0 - min_path_cost / 10.0)
                graph_path = best_path

        # Combine scores
        final_score = combine_scores(content_sim, pref_score, graph_score)

        results.append(RecommendationItem(
            media=media,
            similarity_score=round(content_sim, 4),
            preference_score=round(pref_score, 4),
            final_score=round(final_score, 4),
            explanation=reasons,
            graph_path=graph_path,
        ))

    # Sort by final score descending
    results.sort(key=lambda r: r.final_score, reverse=True)

    return results