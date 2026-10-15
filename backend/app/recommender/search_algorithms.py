"""Graph search algorithms for recommendation discovery.

Each algorithm has a documented purpose:
- BFS: Discover titles within bounded relationship steps (explore locally)
- DFS: Explore deeper relationship chains (discover niche connections)
- UCS: Find minimum-cost paths (strongest cumulative relationships)
- Greedy Best-First: Prioritize by relevance heuristic (preference matching)
- A*: Combine path cost + admissible heuristic (optimal when heuristic is valid)

All algorithms include cycle prevention, depth/cost limits, and deterministic tie-breaking.
"""

from typing import List, Dict, Set, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from heapq import heappush, heappop
from collections import deque
import math

from app.recommender.graph import MetadataGraph, GraphNode, GraphEdge


@dataclass
class SearchResult:
    """Result of a graph search."""
    visited: List[int]  # Node IDs in order visited
    paths: Dict[int, List[int]]  # node_id -> path from start
    costs: Dict[int, float]  # node_id -> cost from start
    stopped_reason: str


@dataclass
class SearchConfig:
    """Configuration for graph search."""
    max_depth: int = 3  # Maximum hops from start
    max_nodes: int = 100  # Maximum nodes to visit
    max_cost: float = 10.0  # Maximum path cost
    target_nodes: Optional[Set[int]] = None  # Specific targets to find


def deterministic_tiebreaker(node_id: int) -> int:
    """Deterministic tiebreaker for queue ordering."""
    return node_id


def bfs(
    graph: MetadataGraph,
    start_nodes: List[int],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    Breadth-First Search: Discover titles within bounded relationship steps.
    
    Purpose: Find all nodes within N hops from favorites, level by level.
    Use case: Local exploration - find closely related titles first.
    
    Args:
        graph: Metadata graph to search
        start_nodes: Favorite node IDs to start from
        config: Search configuration (depth, node limits)
        
    Returns:
        SearchResult with visited nodes in BFS order
    """
    config = config or SearchConfig()
    visited: List[int] = []
    paths: Dict[int, List[int]] = {}
    costs: Dict[int, float] = {}
    visited_set: Set[int] = set()
    
    queue = deque()
    
    # Initialize with start nodes
    for start in start_nodes:
        if graph.has_node(start):
            queue.append((start, 0, [start]))  # (node_id, depth, path)
            if start not in visited_set:
                visited_set.add(start)
                visited.append(start)
                paths[start] = [start]
                costs[start] = 0.0

    while queue and len(visited) < (config.max_nodes or 100):
        node_id, depth, path = queue.popleft()

        if depth >= config.max_depth:
            continue

        node = graph.get_node(node_id)
        if not node:
            continue

        # Get neighbors, sort by node_id for deterministic order
        neighbors = sorted(graph.get_neighbors(node_id), key=lambda e: e.target)

        for edge in neighbors:
            if edge.target in visited_set:
                continue

            visited_set.add(edge.target)
            visited.append(edge.target)
            new_path = path + [edge.target]
            paths[edge.target] = new_path
            costs[edge.target] = costs.get(node_id, 0.0) + edge.cost

            if config.target_nodes and edge.target in config.target_nodes:
                return SearchResult(visited, paths, costs, "target_found")

            queue.append((edge.target, depth + 1, new_path))

    return SearchResult(visited, paths, costs, "completed" if not queue else "node_limit")


def dfs(
    graph: MetadataGraph,
    start_nodes: List[int],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    Depth-First Search: Explore deeper relationship chains.
    
    Purpose: Find niche/long-tail connections by going deep before wide.
    Use case: Discover hidden gems through longer relationship chains.
    
    Args:
        graph: Metadata graph to search
        start_nodes: Favorite node IDs to start from
        config: Search configuration (depth, node limits)
        
    Returns:
        SearchResult with visited nodes in DFS order
    """
    config = config or SearchConfig()
    visited: List[int] = []
    paths: Dict[int, List[int]] = {}
    costs: Dict[int, float] = {}
    visited_set: Set[int] = set()

    def dfs_recursive(node_id: int, depth: int, path: List[int], path_cost: float) -> bool:
        """Recursive DFS with limits."""
        if depth > config.max_depth or len(visited) >= (config.max_nodes or 100):
            return False

        if node_id in visited_set:
            return False

        visited_set.add(node_id)
        visited.append(node_id)
        paths[node_id] = path
        costs[node_id] = path_cost

        if config.target_nodes and node_id in config.target_nodes:
            return True

        node = graph.get_node(node_id)
        if not node:
            return False

        # Sort neighbors by cost (strongest relationship first) for deterministic order
        neighbors = sorted(graph.get_neighbors(node_id), key=lambda e: (e.cost, e.target))

        for edge in neighbors:
            if dfs_recursive(edge.target, depth + 1, path + [edge.target], path_cost + edge.cost):
                return True

        return False

    for start in start_nodes:
        if graph.has_node(start) and start not in visited_set:
            if dfs_recursive(start, 0, [start], 0.0):
                return SearchResult(visited, paths, costs, "target_found")

    return SearchResult(visited, paths, costs, "completed")


def ucs(
    graph: MetadataGraph,
    start_nodes: List[int],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    Uniform-Cost Search: Find minimum-cost paths.
    
    Purpose: Find titles with strongest cumulative relationship to favorites.
    Use case: When relationship strength matters more than hop count.
    
    Args:
        graph: Metadata graph to search
        start_nodes: Favorite node IDs to start from
        config: Search configuration (cost limits)
        
    Returns:
        SearchResult with nodes ordered by minimum path cost
    """
    config = config or SearchConfig()
    visited: List[int] = []
    paths: Dict[int, List[int]] = {}
    costs: Dict[int, float] = {}
    visited_set: Set[int] = set()

    # Priority queue: (cost, tiebreaker, node_id, path)
    pq: List[Tuple[float, int, int, List[int]]] = []

    for start in start_nodes:
        if graph.has_node(start):
            heappush(pq, (0.0, deterministic_tiebreaker(start), start, [start]))

    while pq and len(visited) < (config.max_nodes or 100):
        cost, _, node_id, path = heappop(pq)

        if cost > (config.max_cost or 10.0):
            break

        if node_id in visited_set:
            continue

        visited_set.add(node_id)
        visited.append(node_id)
        paths[node_id] = path
        costs[node_id] = cost

        if config.target_nodes and node_id in config.target_nodes:
            return SearchResult(visited, paths, costs, "target_found")

        node = graph.get_node(node_id)
        if not node:
            continue

        # Expand neighbors
        for edge in sorted(graph.get_neighbors(node_id), key=lambda e: (e.cost, e.target)):
            if edge.target not in visited_set:
                new_cost = cost + edge.cost
                if new_cost <= (config.max_cost or 10.0):
                    heappush(pq, (new_cost, deterministic_tiebreaker(edge.target), edge.target, path + [edge.target]))

    return SearchResult(visited, paths, costs, "completed" if not pq else "cost_limit")


def greedy_best_first(
    graph: MetadataGraph,
    start_nodes: List[int],
    heuristic: Callable[[GraphNode], float],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    Greedy Best-First Search: Explore using relevance heuristic.
    
    Purpose: Prioritize nodes that best match user preferences.
    Use case: Fast discovery of highly relevant titles.
    
    Args:
        graph: Metadata graph to search
        start_nodes: Favorite node IDs to start from
        heuristic: Function h(node) -> relevance score (higher = better)
        config: Search configuration
        
    Returns:
        SearchResult with nodes ordered by heuristic
    """
    config = config or SearchConfig()
    visited: List[int] = []
    paths: Dict[int, List[int]] = {}
    costs: Dict[int, float] = {}
    visited_set: Set[int] = set()

    # Priority queue: (-heuristic, tiebreaker, node_id, path, path_cost)
    pq: List[Tuple[float, int, int, List[int], float]] = []

    for start in start_nodes:
        if graph.has_node(start):
            node = graph.get_node(start)
            h = heuristic(node) if node else 0.0
            heappush(pq, (-h, deterministic_tiebreaker(start), start, [start], 0.0))

    while pq and len(visited) < (config.max_nodes or 100):
        neg_h, _, node_id, path, path_cost = heappop(pq)

        if node_id in visited_set:
            continue

        visited_set.add(node_id)
        visited.append(node_id)
        paths[node_id] = path
        costs[node_id] = path_cost

        if config.target_nodes and node_id in config.target_nodes:
            return SearchResult(visited, paths, costs, "target_found")

        node = graph.get_node(node_id)
        if not node:
            continue

        # Expand neighbors
        for edge in sorted(graph.get_neighbors(node_id), key=lambda e: (e.cost, e.target)):
            if edge.target not in visited_set:
                neighbor = graph.get_node(edge.target)
                h = heuristic(neighbor) if neighbor else 0.0
                new_path = path + [edge.target]
                new_cost = path_cost + edge.cost
                heappush(pq, (-h, deterministic_tiebreaker(edge.target), edge.target, new_path, new_cost))

    return SearchResult(visited, paths, costs, "completed" if not pq else "node_limit")


def astar(
    graph: MetadataGraph,
    start_nodes: List[int],
    heuristic: Callable[[GraphNode], float],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    A* Search: Combine path cost with admissible heuristic.
    
    Purpose: Find optimal paths when heuristic is admissible (never overestimates).
    Heuristic must be admissible: h(node) <= actual cost to target.
    
    For recommendations, we use a preference-relevance heuristic that
    estimates how well a node matches user preferences.
    
    Args:
        graph: Metadata graph to search
        start_nodes: Favorite node IDs to start from
        heuristic: Admissible heuristic h(node) -> estimated cost to "ideal" match
        config: Search configuration
        
    Returns:
        SearchResult with optimal paths
        
    Note: Heuristic must be admissible for optimality guarantee.
    In practice, our heuristic estimates preference match (0-10 scale)
    and we negate it for min-heap behavior.
    """
    config = config or SearchConfig()
    visited: List[int] = []
    paths: Dict[int, List[int]] = {}
    costs: Dict[int, float] = {}
    visited_set: Set[int] = set()

    # Priority queue: (f_score, g_score, tiebreaker, node_id, path)
    # f = g + h where g = path cost, h = heuristic
    pq: List[Tuple[float, float, int, int, List[int]]] = []

    for start in start_nodes:
        if graph.has_node(start):
            node = graph.get_node(start)
            h = heuristic(node) if node else 0.0
            g = 0.0
            f = g + h
            heappush(pq, (f, g, deterministic_tiebreaker(start), start, [start]))

    while pq and len(visited) < (config.max_nodes or 100):
        f, g, _, node_id, path = heappop(pq)

        if g > (config.max_cost or 10.0):
            continue

        if node_id in visited_set:
            continue

        visited_set.add(node_id)
        visited.append(node_id)
        paths[node_id] = path
        costs[node_id] = g

        if config.target_nodes and node_id in config.target_nodes:
            return SearchResult(visited, paths, costs, "target_found")

        node = graph.get_node(node_id)
        if not node:
            continue

        for edge in sorted(graph.get_neighbors(node_id), key=lambda e: (e.cost, e.target)):
            if edge.target not in visited_set:
                neighbor = graph.get_node(edge.target)
                h = heuristic(neighbor) if neighbor else 0.0
                new_g = g + edge.cost
                new_f = new_g + h
                if new_g <= (config.max_cost or 10.0):
                    heappush(pq, (new_f, new_g, deterministic_tiebreaker(edge.target), edge.target, path + [edge.target]))

    return SearchResult(visited, paths, costs, "completed" if not pq else "cost_limit")


def hybrid_search(
    graph: MetadataGraph,
    start_nodes: List[int],
    candidate_nodes: Set[int],
    heuristic: Callable[[GraphNode], float],
    config: Optional[SearchConfig] = None,
) -> SearchResult:
    """
    Hybrid search combining multiple strategies for recommendations.
    
    Strategy:
    1. BFS to find local neighborhood (depth 2)
    2. A* from favorites toward candidate nodes using preference heuristic
    3. Combine and deduplicate results
    
    This is the recommended default for recommendations.
    """
    config = config or SearchConfig()
    config = SearchConfig(
        max_depth=2,
        max_nodes=config.max_nodes,
        max_cost=config.max_cost,
        target_nodes=candidate_nodes,
    )

    # Phase 1: BFS for local exploration
    bfs_result = bfs(graph, start_nodes, config)

    # Phase 2: A* toward candidates
    config.max_depth = 3
    astar_result = astar(graph, start_nodes, heuristic, config)

    # Merge results, prioritizing candidate nodes
    all_visited = []
    seen = set()

    # Add candidate nodes first (from A*)
    for node_id in astar_result.visited:
        if node_id in candidate_nodes and node_id not in seen:
            seen.add(node_id)
            all_visited.append(node_id)

    # Add BFS results
    for node_id in bfs_result.visited:
        if node_id not in seen:
            seen.add(node_id)
            all_visited.append(node_id)

    # Merge paths and costs (prefer lower cost)
    merged_paths = {**bfs_result.paths, **astar_result.paths}
    merged_costs = {}
    for k, v in bfs_result.costs.items():
        merged_costs[k] = v
    for k, v in astar_result.costs.items():
        if k not in merged_costs or v < merged_costs[k]:
            merged_costs[k] = v

    return SearchResult(
        visited=all_visited,
        paths=merged_paths,
        costs=merged_costs,
        stopped_reason="hybrid_completed"
    )