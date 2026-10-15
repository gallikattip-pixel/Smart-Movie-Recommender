"""Recommendation engine package."""

from app.recommender.profile import (
    validate_preferences,
    extract_genres_from_favorites,
    extract_keywords_from_favorites,
    extract_languages_from_favorites,
    extract_countries_from_favorites,
    extract_directors_from_favorites,
    extract_cast_from_favorites,
    extract_eras_from_favorites,
    build_profile_from_favorites,
    merge_preferences,
    genre_id_to_name,
    apply_hard_exclusions,
)

from app.recommender.graph import (
    MetadataGraph,
    GraphNode,
    GraphEdge,
    build_graph_from_favorites_and_candidates,
)

from app.recommender.search_algorithms import (
    SearchConfig,
    SearchResult,
    bfs,
    dfs,
    ucs,
    greedy_best_first,
    astar,
    hybrid_search,
)

from app.recommender.ranking import (
    tokenize,
    build_corpus,
    compute_tfidf_vector,
    cosine_similarity,
    build_content_corpus,
    compute_content_similarity,
    build_preference_query_vector,
    compute_preference_score,
    combine_scores,
    rank_candidates,
)

from app.recommender.candidates import (
    discover_candidates_from_favorites,
    discover_candidates_by_genre,
    discover_candidates_by_keyword,
    discover_candidates_by_cast_director,
    discover_candidates_by_language_country,
    get_all_candidates,
    filter_candidates_by_preferences,
)

from app.recommender.explain import (
    ExplanationBuilder,
    generate_explanation_text,
    generate_explanation_detailed,
)

__all__ = [
    # Profile
    "validate_preferences",
    "extract_genres_from_favorites",
    "extract_keywords_from_favorites",
    "extract_languages_from_favorites",
    "extract_countries_from_favorites",
    "extract_directors_from_favorites",
    "extract_cast_from_favorites",
    "extract_eras_from_favorites",
    "build_profile_from_favorites",
    "merge_preferences",
    "genre_id_to_name",
    "apply_hard_exclusions",
    # Graph
    "MetadataGraph",
    "GraphNode",
    "GraphEdge",
    "build_graph_from_favorites_and_candidates",
    # Search Algorithms
    "SearchConfig",
    "SearchResult",
    "bfs",
    "dfs",
    "ucs",
    "greedy_best_first",
    "astar",
    "hybrid_search",
    # Ranking
    "tokenize",
    "build_corpus",
    "compute_tfidf_vector",
    "cosine_similarity",
    "build_content_corpus",
    "compute_content_similarity",
    "build_preference_query_vector",
    "compute_preference_score",
    "combine_scores",
    "rank_candidates",
    # Candidates
    "discover_candidates_from_favorites",
    "discover_candidates_by_genre",
    "discover_candidates_by_keyword",
    "discover_candidates_by_cast_director",
    "discover_candidates_by_language_country",
    "get_all_candidates",
    "filter_candidates_by_preferences",
    # Explain
    "ExplanationBuilder",
    "generate_explanation_text",
    "generate_explanation_detailed",
]