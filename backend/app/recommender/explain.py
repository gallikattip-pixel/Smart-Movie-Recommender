"""Recommendation explanation generation."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.schemas import (
    MediaDetailsResponse,
    RecommendationItem,
    ExplanationReason,
    UserPreference,
)


@dataclass
class ExplanationBuilder:
    """Build human-readable explanations for recommendations."""
    
    media: MediaDetailsResponse
    prefs: UserPreference
    recommendation: RecommendationItem

    def build_explanation(self) -> str:
        """Generate a human-readable explanation string."""
        if not self.recommendation.explanation:
            return "Recommended based on general popularity."

        parts = []
        for reason in self.recommendation.explanation:
            parts.append(self._format_reason(reason))

        if not parts:
            return "Recommended based on your preferences."

        return " ".join(parts)

    def _format_reason(self, reason: ExplanationReason) -> str:
        """Format a single explanation reason."""
        templates = {
            "genre": "Matches your interest in {description}.",
            "keyword": "Shares themes with your favorites: {description}.",
            "cast": "Features actors you like: {description}.",
            "director": "From a director you enjoy: {description}.",
            "language": "In your preferred language ({description}).",
            "country": "From a country you prefer: {description}.",
            "era": "Released in your preferred era ({description}).",
            "rating": "Well-rated ({description}).",
            "theme": "Matches your preferred theme: {description}.",
            "mood": "Fits your preferred mood: {description}.",
            "content_type": "A {description.lower()} as you prefer.",
            "hidden_gem": "A hidden gem you might not have discovered.",
            "similar_to_favorite": "Similar to your favorite titles.",
        }

        template = templates.get(reason.type, "{description}.")
        return template.format(description=reason.description)

    def build_detailed_explanation(self) -> Dict[str, Any]:
        """Build structured explanation for API response."""
        return {
            "summary": self.build_explanation(),
            "reasons": [
                {
                    "type": r.type,
                    "description": r.description,
                    "weight": r.weight,
                }
                for r in self.recommendation.explanation
            ],
            "scores": {
                "content_similarity": self.recommendation.similarity_score,
                "preference_match": self.recommendation.preference_score,
                "graph_path": self.recommendation.graph_path is not None,
            },
            "graph_path": self.recommendation.graph_path,
        }


def generate_explanation_text(media: MediaDetailsResponse, prefs: UserPreference, rec: RecommendationItem) -> str:
    """Convenience function to generate explanation text."""
    builder = ExplanationBuilder(media=media, prefs=prefs, recommendation=rec)
    return builder.build_explanation()


def generate_explanation_detailed(media: MediaDetailsResponse, prefs: UserPreference, rec: RecommendationItem) -> Dict[str, Any]:
    """Convenience function to generate detailed explanation."""
    builder = ExplanationBuilder(media=media, prefs=prefs, recommendation=rec)
    return builder.build_detailed_explanation()