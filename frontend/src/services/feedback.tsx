/** Feedback storage service using localStorage. */

import React from "react";

export type FeedbackType = "like" | "dislike" | "watched" | "more_like_this";

export interface FeedbackItem {
  media_type: "movie" | "tv";
  item_id: number;
  type: FeedbackType;
  timestamp: number; // Unix timestamp in ms
}

const STORAGE_KEY = "smart-movie-recommender-feedback";

export function getFeedback(): FeedbackItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (f): f is FeedbackItem =>
        f &&
        typeof f === "object" &&
        (f.media_type === "movie" || f.media_type === "tv") &&
        typeof f.item_id === "number" &&
        f.item_id > 0 &&
        ["like", "dislike", "watched", "more_like_this"].includes(f.type) &&
        typeof f.timestamp === "number"
    );
  } catch {
    return [];
  }
}

export function saveFeedback(feedback: FeedbackItem[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(feedback));
  } catch {
    // Ignore storage errors (e.g., quota exceeded, private browsing)
  }
}

export function addFeedback(item: FeedbackItem): FeedbackItem[] {
  const feedback = getFeedback();
  // Remove existing feedback of same type or mutually exclusive like/dislike for this item
  const filtered = feedback.filter(
    (f) =>
      !(
        f.media_type === item.media_type &&
        f.item_id === item.item_id &&
        (f.type === item.type ||
          (item.type === "like" && f.type === "dislike") ||
          (item.type === "dislike" && f.type === "like"))
      )
  );
  filtered.push(item);
  saveFeedback(filtered);
  return filtered;
}

export function removeFeedback(mediaType: "movie" | "tv", itemId: number, type: FeedbackType): FeedbackItem[] {
  const feedback = getFeedback().filter(
    (f) => !(f.media_type === mediaType && f.item_id === itemId && f.type === type)
  );
  saveFeedback(feedback);
  return feedback;
}

export function toggleFeedback(
  mediaType: "movie" | "tv",
  itemId: number,
  type: FeedbackType
): { added: boolean; feedback: FeedbackItem[] } {
  const feedback = getFeedback();
  const index = feedback.findIndex(
    (f) => f.media_type === mediaType && f.item_id === itemId && f.type === type
  );
  if (index >= 0) {
    feedback.splice(index, 1);
    saveFeedback(feedback);
    return { added: false, feedback };
  } else {
    // Remove mutual exclusive feedback (like vs dislike)
    let updated = feedback;
    if (type === "like") {
      updated = updated.filter((f) => !(f.media_type === mediaType && f.item_id === itemId && f.type === "dislike"));
    } else if (type === "dislike") {
      updated = updated.filter((f) => !(f.media_type === mediaType && f.item_id === itemId && f.type === "like"));
    }
    const newItem: FeedbackItem = { media_type: mediaType, item_id: itemId, type, timestamp: Date.now() };
    updated.push(newItem);
    saveFeedback(updated);
    return { added: true, feedback: updated };
  }
}

export function getFeedbackForItem(mediaType: "movie" | "tv", itemId: number): FeedbackType[] {
  const feedback = getFeedback();
  return feedback
    .filter((f) => f.media_type === mediaType && f.item_id === itemId)
    .map((f) => f.type);
}

export function hasFeedback(mediaType: "movie" | "tv", itemId: number, type: FeedbackType): boolean {
  const feedback = getFeedback();
  return feedback.some((f) => f.media_type === mediaType && f.item_id === itemId && f.type === type);
}

export function clearFeedback(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getFeedbackByType(type: FeedbackType): { media_type: "movie" | "tv"; item_id: number }[] {
  return getFeedback()
    .filter((f) => f.type === type)
    .map((f) => ({ media_type: f.media_type, item_id: f.item_id }));
}

export function getFeedbackCounts(): Record<FeedbackType, number> {
  const feedback = getFeedback();
  const counts: Record<FeedbackType, number> = {
    like: 0,
    dislike: 0,
    watched: 0,
    more_like_this: 0,
  };
  feedback.forEach((f) => {
    counts[f.type]++;
  });
  return counts;
}

export function getFeedbackLabel(type: FeedbackType): string {
  switch (type) {
    case "like":
      return "Like";
    case "dislike":
      return "Dislike";
    case "watched":
      return "Watched";
    case "more_like_this":
      return "More Like This";
  }
}

export function getFeedbackIcon(type: FeedbackType, isActive = false): React.ReactNode {
  switch (type) {
    case "like":
      return (
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill={isActive ? "currentColor" : "none"}
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
          />
        </svg>
      );
    case "dislike":
      return (
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill={isActive ? "currentColor" : "none"}
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17"
          />
        </svg>
      );
    case "watched":
      return (
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    case "more_like_this":
      return (
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill={isActive ? "currentColor" : "none"}
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            stroke={isActive ? "#D8C3A5" : "currentColor"}
            d="M12 9v6m-3-3h6"
          />
        </svg>
      );
  }
}

export function getFeedbackColor(type: FeedbackType, isActive = false): string {
  if (isActive) {
    switch (type) {
      case "like":
        return "text-white bg-green-600 hover:bg-green-700 ring-1 ring-green-600 shadow-sm";
      case "dislike":
        return "text-white bg-red-600 hover:bg-red-700 ring-1 ring-red-600 shadow-sm";
      case "watched":
        return "text-white bg-blue-600 hover:bg-blue-700 ring-1 ring-blue-600 shadow-sm";
      case "more_like_this":
        return "text-stone-950 bg-almond-400 hover:bg-almond-300 ring-1 ring-almond-400 shadow-sm";
    }
  }
  switch (type) {
    case "like":
      return "text-green-700 bg-green-50 hover:bg-green-100 border border-green-200/60";
    case "dislike":
      return "text-red-700 bg-red-50 hover:bg-red-100 border border-red-200/60";
    case "watched":
      return "text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/60";
    case "more_like_this":
      return "text-almond-200 bg-almond-400/15 hover:bg-almond-400/25 border border-almond-400/30";
  }
}
