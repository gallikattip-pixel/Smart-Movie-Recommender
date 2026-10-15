"""Metadata relationship graph for movie/TV recommendations."""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import math

from app.tmdb.models import TMDBMovieDetails, TMDBTVSeriesDetails
from app.schemas import MediaDetailsResponse


@dataclass
class GraphNode:
    """Node in the metadata relationship graph."""
    id: int
    media_type: str  # "movie" or "tv"
    title: str
    genres: Set[int]
    keywords: Set[str]
    original_language: str
    production_countries: Set[str]
    cast_names: Set[str]
    director_names: Set[str]
    vote_average: float
    popularity: float
    release_year: Optional[int]
    # Cached metadata for edge computation
    metadata: Any = field(default=None, repr=False)


@dataclass
class GraphEdge:
    """Edge in the metadata relationship graph."""
    source: int
    target: int
    cost: float  # Lower = stronger relationship
    reasons: List[str]  # Why this edge exists
    shared_attributes: Dict[str, Any]  # Details about shared attributes


class MetadataGraph:
    """
    In-memory metadata relationship graph.
    
    Nodes: Movies and TV series
    Edges: Weighted by shared metadata attributes
    
    Edge cost rules (lower = stronger relationship):
    - Shared genres: -2.0 per genre (max -8.0)
    - Shared keywords: -1.5 per keyword (max -6.0)
    - Same original language: -1.0
    - Shared production country: -1.0 per country (max -3.0)
    - Shared cast: -0.5 per actor (max -2.0)
    - Shared director: -1.5 per director (max -3.0)
    - Same release era (decade): -0.5
    - Similar vote average (within 0.5): -0.3
    - Popularity difference penalty: +0.1 per 10 popularity difference
    
    Minimum edge cost: 0.1 (prevents zero/negative cycles)
    Maximum edges per node: 50 (limits graph density)
    """

    # Edge cost weights
    GENRE_WEIGHT = -2.0
    KEYWORD_WEIGHT = -1.5
    LANGUAGE_WEIGHT = -1.0
    COUNTRY_WEIGHT = -1.0
    CAST_WEIGHT = -0.5
    DIRECTOR_WEIGHT = -1.5
    ERA_WEIGHT = -0.5
    RATING_WEIGHT = -0.3
    POPULARITY_PENALTY = 0.1  # per 10 popularity difference

    MIN_EDGE_COST = 0.1
    MAX_EDGES_PER_NODE = 50
    MAX_GRAPH_NODES = 500

    def __init__(self):
        self.nodes: Dict[int, GraphNode] = {}
        self.edges: Dict[int, List[GraphEdge]] = defaultdict(list)
        self._node_counter = 0

    def add_node(self, media: MediaDetailsResponse) -> int:
        """Add a media item as a node. Returns node ID."""
        if media.id in self.nodes:
            return media.id

        if len(self.nodes) >= self.MAX_GRAPH_NODES:
            return media.id  # Don't add more nodes

        release_year = None
        if media.media_type == "movie" and media.release_date:
            try:
                release_year = int(media.release_date[:4])
            except (ValueError, IndexError):
                pass
        elif media.media_type == "tv" and media.first_air_date:
            try:
                release_year = int(media.first_air_date[:4])
            except (ValueError, IndexError):
                pass

        node = GraphNode(
            id=media.id,
            media_type=media.media_type,
            title=media.title,
            genres={g.id for g in media.genres},
            keywords={k.name.lower() for k in media.keywords},
            original_language=media.original_language,
            production_countries={c.iso_3166_1 for c in media.production_countries if c.iso_3166_1},
            cast_names={c.name for c in media.cast[:10]},  # Top 10 cast
            director_names={d.name for d in media.directors},
            vote_average=media.vote_average or 0.0,
            popularity=media.popularity or 0.0,
            release_year=release_year,
            metadata=media,
        )

        self.nodes[media.id] = node
        return media.id

    def build_edges(self) -> None:
        """Build edges between all pairs of nodes based on shared metadata."""
        node_ids = list(self.nodes.keys())
        n = len(node_ids)

        for i in range(n):
            for j in range(i + 1, n):
                node_a = self.nodes[node_ids[i]]
                node_b = self.nodes[node_ids[j]]

                cost, reasons, shared = self._compute_edge_cost(node_a, node_b)

                if cost < float('inf') and cost > 0:
                    # Add bidirectional edges
                    self.edges[node_a.id].append(GraphEdge(
                        source=node_a.id, target=node_b.id, cost=cost,
                        reasons=reasons, shared_attributes=shared
                    ))
                    self.edges[node_b.id].append(GraphEdge(
                        source=node_b.id, target=node_a.id, cost=cost,
                        reasons=reasons, shared_attributes=shared
                    ))

        # Prune edges per node to limit graph density
        self._prune_edges()

    def _compute_edge_cost(
        self, node_a: GraphNode, node_b: GraphNode
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """Compute edge cost between two nodes. Lower cost = stronger relationship."""
        cost = 0.0
        reasons = []
        shared = {}

        # Shared genres
        shared_genres = node_a.genres & node_b.genres
        if shared_genres:
            genre_cost = max(self.GENRE_WEIGHT * len(shared_genres), -8.0)
            cost += genre_cost
            reasons.append(f"{len(shared_genres)} shared genre(s)")
            shared["genres"] = list(shared_genres)

        # Shared keywords
        shared_keywords = node_a.keywords & node_b.keywords
        if shared_keywords:
            kw_cost = max(self.KEYWORD_WEIGHT * len(shared_keywords), -6.0)
            cost += kw_cost
            reasons.append(f"{len(shared_keywords)} shared keyword(s)")
            shared["keywords"] = list(shared_keywords)[:10]

        # Same original language
        if node_a.original_language and node_a.original_language == node_b.original_language:
            cost += self.LANGUAGE_WEIGHT
            reasons.append(f"Same language ({node_a.original_language})")
            shared["language"] = node_a.original_language

        # Shared production countries
        shared_countries = node_a.production_countries & node_b.production_countries
        if shared_countries:
            country_cost = max(self.COUNTRY_WEIGHT * len(shared_countries), -3.0)
            cost += country_cost
            reasons.append(f"{len(shared_countries)} shared production country(ies)")
            shared["countries"] = list(shared_countries)

        # Shared cast
        shared_cast = node_a.cast_names & node_b.cast_names
        if shared_cast:
            cast_cost = max(self.CAST_WEIGHT * len(shared_cast), -2.0)
            cost += cast_cost
            reasons.append(f"{len(shared_cast)} shared cast member(s)")
            shared["cast"] = list(shared_cast)[:5]

        # Shared directors
        shared_directors = node_a.director_names & node_b.director_names
        if shared_directors:
            dir_cost = max(self.DIRECTOR_WEIGHT * len(shared_directors), -3.0)
            cost += dir_cost
            reasons.append(f"{len(shared_directors)} shared director(s)")
            shared["directors"] = list(shared_directors)

        # Same release era (decade)
        if node_a.release_year and node_b.release_year:
            decade_a = (node_a.release_year // 10) * 10
            decade_b = (node_b.release_year // 10) * 10
            if decade_a == decade_b:
                cost += self.ERA_WEIGHT
                reasons.append(f"Same era ({decade_a}s)")
                shared["era"] = decade_a

        # Similar vote average (within 0.5)
        if node_a.vote_average > 0 and node_b.vote_average > 0:
            rating_diff = abs(node_a.vote_average - node_b.vote_average)
            if rating_diff <= 0.5:
                cost += self.RATING_WEIGHT
                reasons.append("Similar ratings")
                shared["rating_similarity"] = round(1.0 - rating_diff, 2)

        # Popularity difference penalty
        pop_diff = abs(node_a.popularity - node_b.popularity)
        if pop_diff > 10:
            penalty = (pop_diff / 10) * self.POPULARITY_PENALTY
            cost += penalty

        # If no shared attributes, no edge
        if not reasons:
            return float('inf'), [], {}

        # Apply minimum cost floor
        cost = max(cost, self.MIN_EDGE_COST)

        return cost, reasons, shared

    def _prune_edges(self) -> None:
        """Limit edges per node to keep graph sparse."""
        for node_id, edges in self.edges.items():
            if len(edges) > self.MAX_EDGES_PER_NODE:
                # Keep lowest cost edges (strongest relationships)
                edges.sort(key=lambda e: e.cost)
                self.edges[node_id] = edges[:self.MAX_EDGES_PER_NODE]

    def get_neighbors(self, node_id: int) -> List[GraphEdge]:
        """Get outgoing edges for a node."""
        return self.edges.get(node_id, [])

    def get_node(self, node_id: int) -> Optional[GraphNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def has_node(self, node_id: int) -> bool:
        """Check if node exists."""
        return node_id in self.nodes


def build_graph_from_favorites_and_candidates(
    favorites: List[MediaDetailsResponse],
    candidates: List[MediaDetailsResponse],
) -> MetadataGraph:
    """
    Build a metadata graph from favorites and candidate titles.
    
    Favorites are added first as seed nodes, then candidates.
    """
    graph = MetadataGraph()

    # Add favorites first (seed nodes)
    for fav in favorites:
        graph.add_node(fav)

    # Add candidates
    for candidate in candidates:
        if len(graph.nodes) >= graph.MAX_GRAPH_NODES:
            break
        graph.add_node(candidate)

    # Build edges
    graph.build_edges()

    return graph