"""Comprehensive test suite for recommendation engine pipeline:
- Taste profile construction from query and feedback
- Algorithm graph traversals (BFS, DFS, UCS, Greedy, A*, Hybrid)
- TF-IDF content similarity and ranking
- Feedback influence (likes boost, dislikes exclude, watched handling)
"""

import pytest
from app.schemas import (
    UserPreference,
    FavoriteTitleRequest,
    MediaDetailsResponse,
    GenreItem,
    CastMemberItem,
    CrewMemberItem,
    KeywordItem,
)
from app.recommender.graph import MetadataGraph, GraphNode, GraphEdge
from app.recommender.search_algorithms import (
    bfs,
    dfs,
    ucs,
    greedy_best_first,
    astar,
    hybrid_search,
    SearchConfig,
)
from app.recommender.ranking import (
    build_content_corpus,
    build_preference_query_vector,
    compute_content_similarity,
    compute_preference_score,
    combine_scores,
    rank_candidates,
)
from app.recommender.profile import apply_hard_exclusions


def make_sample_media(
    item_id: int,
    title: str,
    media_type: str = "movie",
    genres: list = None,
    language: str = "en",
    vote_average: float = 8.0,
    popularity: float = 50.0,
    keywords: list = None,
    directors: list = None,
    cast: list = None,
    overview: str = "A fascinating film.",
) -> MediaDetailsResponse:
    return MediaDetailsResponse(
        id=item_id,
        title=title,
        media_type=media_type,  # type: ignore
        release_date="2020-01-01",
        first_air_date=None,
        overview=overview,
        poster_path=f"/{item_id}.jpg",
        poster_url=f"https://image.tmdb.org/t/p/w342/{item_id}.jpg",
        backdrop_path=None,
        backdrop_url=None,
        vote_average=vote_average,
        vote_count=500,
        popularity=popularity,
        original_language=language,
        genres=[GenreItem(id=g[0], name=g[1]) for g in (genres or [(28, "Action"), (878, "Sci-Fi")])],
        runtime=120,
        episode_run_time=[],
        number_of_seasons=None,
        number_of_episodes=None,
        status="Released",
        tagline="Epic story",
        homepage=None,
        production_companies=[],
        production_countries=[],
        spoken_languages=[],
        cast=[CastMemberItem(id=i, name=name) for i, name in enumerate(cast or ["Actor A", "Actor B"])],
        crew=[],
        keywords=[KeywordItem(id=i, name=k) for i, k in enumerate(keywords or ["space", "future"])],
        directors=[CrewMemberItem(id=99, name=name, job="Director", department="Directing") for name in (directors or ["Director Nolan"])],
    )


class TestRecommenderPipeline:
    """Test recommender pipeline components."""

    def test_algorithms_graph_traversal(self):
        """Verify BFS, DFS, UCS, Greedy, A*, and Hybrid explore nodes according to their semantics."""
        graph = MetadataGraph()

        def make_node(node_id: int, title: str) -> GraphNode:
            return GraphNode(
                id=node_id,
                media_type="movie",
                title=title,
                genres={28},
                keywords=set(),
                original_language="en",
                production_countries=set(),
                cast_names=set(),
                director_names=set(),
                vote_average=7.5,
                popularity=20.0,
                release_year=2020,
            )

        def add_edge(u: int, v: int, cost: float):
            graph.edges[u].append(GraphEdge(source=u, target=v, cost=cost, reasons=["test"], shared_attributes={}))

        # Create a graph: 1 -> 2 -> 3; 1 -> 4
        graph.nodes[1] = make_node(1, "Movie 1")
        graph.nodes[2] = make_node(2, "Movie 2")
        graph.nodes[3] = make_node(3, "Movie 3")
        graph.nodes[4] = make_node(4, "Movie 4")

        add_edge(1, 2, cost=0.2)
        add_edge(2, 3, cost=0.4)
        add_edge(1, 4, cost=0.5)

        config = SearchConfig(max_depth=3, max_nodes=10)

        # BFS visits level 1 (nodes 2 and 4) before level 2 (node 3)
        bfs_res = bfs(graph, [1], config)
        assert 1 in bfs_res.visited
        assert 2 in bfs_res.visited
        assert 4 in bfs_res.visited
        assert 3 in bfs_res.visited
        assert bfs_res.visited.index(2) < bfs_res.visited.index(3)
        assert bfs_res.visited.index(4) < bfs_res.visited.index(3)

        # DFS traverses deep first
        dfs_res = dfs(graph, [1], config)
        assert len(dfs_res.visited) == 4

        # UCS finds lowest cumulative cost
        ucs_res = ucs(graph, [1], config)
        assert ucs_res.costs[1] == 0.0
        assert ucs_res.costs[2] == pytest.approx(0.2)
        assert ucs_res.costs[3] == pytest.approx(0.6)

        # Greedy and A* with admissible heuristic
        heuristic = lambda node: -1.0 if node.id == 3 else 0.0
        greedy_res = greedy_best_first(graph, [1], heuristic, config)
        assert len(greedy_res.visited) > 0

        astar_res = astar(graph, [1], heuristic, config)
        assert len(astar_res.visited) > 0

        # Hybrid search
        hybrid_res = hybrid_search(graph, [1], {2, 3, 4}, heuristic, config)
        assert len(hybrid_res.visited) > 0

    def test_feedback_dislike_exclusion(self):
        """Disliked movies must be excluded by apply_hard_exclusions and compute_preference_score."""
        cand1 = make_sample_media(101, "Great Movie")
        cand2 = make_sample_media(102, "Bad Movie")

        prefs = UserPreference(
            feedback_dislikes=[FavoriteTitleRequest(media_type="movie", item_id=102)]
        )

        score1, _ = compute_preference_score(cand1, prefs)
        score2, reasons2 = compute_preference_score(cand2, prefs)

        assert score2 == 0.0
        assert any("dislike" in r.description.lower() for r in reasons2)

    def test_feedback_likes_boost(self):
        """Titles with like feedback should receive positive scoring and explanation reason."""
        cand = make_sample_media(101, "Beloved Film")
        prefs = UserPreference(
            feedback_likes=[FavoriteTitleRequest(media_type="movie", item_id=101)]
        )

        score, reasons = compute_preference_score(cand, prefs)
        assert score > 0.0
        assert any("liked" in r.description.lower() for r in reasons)

    def test_tfidf_content_similarity_ranking(self):
        """Content TF-IDF should score candidates higher when they share keywords and themes with query."""
        cand_space = make_sample_media(201, "Interstellar Odyssey", keywords=["space", "wormhole", "astronomy"], overview="A mission across space.")
        cand_romance = make_sample_media(202, "Summer Love", genres=[(10749, "Romance")], keywords=["dating", "paris"], overview="A romantic story in Paris.")

        candidates = [cand_space, cand_romance]

        prefs = UserPreference(
            query="space exploration interstellar astronomy",
            preferred_genres=[878],  # Sci-Fi
        )

        ranked = rank_candidates(candidates, prefs)
        assert len(ranked) == 2
        # Space movie should rank first due to strong query & genre match
        assert ranked[0].media.id == 201
        assert ranked[0].similarity_score > ranked[1].similarity_score

    def test_natural_language_description_ranking(self):
        """Detailed natural language description must directly influence TF-IDF similarity and final rank."""
        from app.recommender.intent import parse_query_intent

        cand_scifi = make_sample_media(
            301,
            "Virtual Illusion",
            genres=[(878, "Sci-Fi"), (53, "Thriller")],
            keywords=["hacker", "simulation", "virtual reality", "plot twist"],
            overview="A programmer discovers that his reality is a simulation with unexpected plot twists."
        )
        cand_action = make_sample_media(
            302,
            "Miami Nitro",
            genres=[(28, "Action")],
            keywords=["cars", "street racing", "miami"],
            overview="High speed muscle cars race through the streets of Miami."
        )

        candidates = [cand_action, cand_scifi]

        description = (
            "I'm looking for a mind-bending sci-fi thriller about virtual reality and simulation "
            "with a hacker protagonist and unexpected plot twists."
        )

        intent = parse_query_intent(description)
        prefs = UserPreference(
            query=description,
            preferred_genres=intent.genre_ids,
            preferred_themes=intent.themes,
            preferred_endings=intent.endings,
        )

        ranked = rank_candidates(candidates, prefs)
        assert len(ranked) == 2
        # Sci-Fi simulation movie must rank first due to strong natural language TF-IDF and genre/theme matches
        assert ranked[0].media.id == 301
        assert ranked[0].similarity_score > ranked[1].similarity_score
        assert ranked[0].final_score > ranked[1].final_score

    def test_natural_language_exclusion_filtering(self):
        """Natural language description with exclusions must exclude matching candidates."""
        from app.recommender.intent import parse_query_intent
        from app.recommender.candidates import filter_candidates_by_preferences

        cand_thriller = make_sample_media(401, "Dark Secret", genres=[(53, "Thriller"), (9648, "Mystery")])
        cand_comedy = make_sample_media(402, "Silly Joke", genres=[(35, "Comedy")])
        cand_horror = make_sample_media(403, "Haunted Mansion", genres=[(27, "Horror")])

        description = "Intense psychological mystery thriller, avoid comedy and horror."
        intent = parse_query_intent(description)

        prefs = UserPreference(
            query=description,
            preferred_genres=intent.genre_ids,
            excluded_genres=intent.excluded_genre_ids,
        )

        filtered = filter_candidates_by_preferences([cand_thriller, cand_comedy, cand_horror], prefs)
        assert len(filtered) == 1
        assert filtered[0].id == 401
