/** Recommendation API service for frontend. */

import type {
  RecommendRequest,
  RecommendResponse,
  RecommendError,
  AlgorithmType,
} from "../types/recommend";

export type { RecommendRequest, RecommendResponse, RecommendError, AlgorithmType };

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, "")}/api`
  : "/api";

export async function getRecommendations(
  request: RecommendRequest,
  signal?: AbortSignal
): Promise<RecommendResponse> {
  const response = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const errorData: RecommendError = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
      code: "HTTP_ERROR",
    }));

    const error = new Error(errorData.detail) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code || response.headers.get("X-Error-Code") || undefined;
    throw error;
  }

  return response.json();
}

export async function getRecommendationsFromFavorites(
  favorites: Array<{ media_type: "movie" | "tv"; item_id: number }>,
  limit: number = 20,
  algorithm: AlgorithmType = "hybrid",
  signal?: AbortSignal
): Promise<RecommendResponse> {
  const query = new URLSearchParams({ limit: String(limit), algorithm }).toString();
  const response = await fetch(`${API_BASE}/recommend/from-favorites?${query}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(favorites),
    signal,
  });

  if (!response.ok) {
    const errorData: RecommendError = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
      code: "HTTP_ERROR",
    }));

    const error = new Error(errorData.detail) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code || response.headers.get("X-Error-Code") || undefined;
    throw error;
  }

  return response.json();
}

export function getAlgorithmLabel(algorithm: AlgorithmType): string {
  switch (algorithm) {
    case "bfs":
      return "Breadth-First Search (Local exploration)";
    case "dfs":
      return "Depth-First Search (Deep discovery)";
    case "ucs":
      return "Uniform-Cost Search (Strongest relationships)";
    case "greedy":
      return "Greedy Best-First (Preference matching)";
    case "astar":
      return "A* Search (Optimal paths)";
    case "hybrid":
      return "Hybrid (Recommended - combines BFS + A*)";
  }
}

export function getAlgorithmDescription(algorithm: AlgorithmType): string {
  switch (algorithm) {
    case "bfs":
      return "Explores nearby connections first. Best for finding closely related titles.";
    case "dfs":
      return "Explores deep relationship chains. Best for discovering hidden gems through long connections.";
    case "ucs":
      return "Finds paths with strongest cumulative relationships. Prioritizes connection strength over distance.";
    case "greedy":
      return "Prioritizes titles that best match your preferences. Fast but may miss optimal paths.";
    case "astar":
      return "Combines path cost with preference heuristic. Optimal when heuristic is well-calibrated.";
    case "hybrid":
      return "Combines BFS local exploration with A* preference-guided search. Best overall for recommendations.";
  }
}