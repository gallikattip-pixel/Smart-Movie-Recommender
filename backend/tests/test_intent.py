"""Tests for deterministic query intent parsing."""

import pytest
from app.recommender.intent import parse_query_intent, QueryIntent


class TestQueryIntentParsing:
    """Test suite verifying deterministic search intent extraction."""

    def test_exact_title_searches(self):
        """Direct movie/TV titles should be classified as exact_title and NOT recommendation."""
        titles = ["Baahubali", "Inception", "The Dark Knight", "Breaking Bad", "Interstellar", "Avatar", "Dune"]
        for title in titles:
            intent = parse_query_intent(title)
            assert intent.intent_type == "exact_title", f"Failed for {title}"
            assert intent.is_recommendation is False, f"Expected is_recommendation=False for {title}"
            assert intent.clean_title == title

    def test_similar_title_requests(self):
        """Similar title patterns should extract the seed title and classify as similar_title."""
        cases = [
            ("Movies like Inception", "Inception", "movie"),
            ("films similar to Interstellar", "Interstellar", "movie"),
            ("shows like Breaking Bad", "Breaking Bad", "tv"),
            ("series similar to Dark", "Dark", "tv"),
            ("more like Stranger Things", "Stranger Things", "multi"),
            ("something like Oppenheimer", "Oppenheimer", "multi"),
        ]
        for query, expected_seed, expected_type in cases:
            intent = parse_query_intent(query)
            assert intent.intent_type == "similar_title", f"Failed for {query}"
            assert intent.is_recommendation is True
            assert intent.clean_title.lower() == expected_seed.lower()
            if expected_type != "multi":
                assert intent.media_type == expected_type

    def test_genre_requests(self):
        """Genre requests should extract genre IDs and classify as genre recommendation."""
        cases = [
            ("psychological thrillers", [53]),
            ("action movies", [28]),
            ("horror films", [27]),
            ("sci-fi movies", [878]),
            ("comedy series", [35]),
        ]
        for query, expected_genre_ids in cases:
            intent = parse_query_intent(query)
            assert intent.intent_type in ("genre", "combined", "mood_theme"), f"Failed for {query}"
            assert intent.is_recommendation is True
            for gid in expected_genre_ids:
                assert gid in intent.genre_ids, f"Expected genre {gid} in {intent.genre_ids} for {query}"

    def test_mood_theme_requests(self):
        """Mood and theme requests should extract corresponding themes and moods."""
        query = "mind-bending movies with plot twists"
        intent = parse_query_intent(query)
        assert intent.intent_type in ("mood_theme", "combined")
        assert intent.is_recommendation is True
        assert "mind-bending" in intent.themes
        assert "plot twist" in intent.themes
        assert intent.media_type == "movie"

        heartwarming_query = "heartwarming feel-good movies"
        intent_hw = parse_query_intent(heartwarming_query)
        assert intent_hw.is_recommendation is True
        assert "heartwarming" in intent_hw.moods

    def test_language_and_country_requests(self):
        """Regional language and country requests should extract ISO codes."""
        kannada_query = "Kannada crime dramas"
        intent_kn = parse_query_intent(kannada_query)
        assert intent_kn.is_recommendation is True
        assert "kn" in intent_kn.languages
        assert "IN" in intent_kn.countries
        assert 80 in intent_kn.genre_ids  # Crime
        assert 18 in intent_kn.genre_ids  # Drama

        korean_query = "Korean thriller series"
        intent_kr = parse_query_intent(korean_query)
        assert intent_kr.is_recommendation is True
        assert "ko" in intent_kr.languages
        assert "KR" in intent_kr.countries
        assert 53 in intent_kr.genre_ids  # Thriller
        assert intent_kr.media_type == "tv"

    def test_combined_requests(self):
        """Complex multi-attribute requests should extract all dimensions."""
        query = "Recent Indian mystery thrillers with unexpected endings"
        intent = parse_query_intent(query)
        assert intent.intent_type == "combined"
        assert intent.is_recommendation is True
        assert "IN" in intent.countries
        assert 9648 in intent.genre_ids  # Mystery
        assert 53 in intent.genre_ids    # Thriller
        assert "plot twist" in intent.themes
        assert intent.era is not None
        assert intent.era.start_year == 2020

    def test_empty_and_whitespace(self):
        """Empty query should gracefully return exact_title with is_recommendation=False."""
        intent = parse_query_intent("   ")
        assert intent.is_recommendation is False
        assert intent.intent_type == "exact_title"

    def test_natural_language_description(self):
        """Full natural language prompts should extract structured genres, pacing, endings, and seed titles."""
        prompt = (
            "I'm looking for a fast-paced psychological thriller with unexpected plot twists "
            "and a shocking ending. Similar to Inception or Shutter Island. Avoid comedy and horror."
        )
        intent = parse_query_intent(prompt)
        assert intent.intent_type == "natural_language"
        assert intent.is_recommendation is True
        assert 53 in intent.genre_ids  # Thriller
        assert "psychological" in intent.themes or "mind-bending" in intent.themes
        assert "fast-paced" in intent.pacing
        assert "twist ending" in intent.endings
        assert any("inception" in s.lower() for s in intent.seed_titles)
        assert any("shutter island" in s.lower() for s in intent.seed_titles)
        # Exclusions
        assert 35 in intent.excluded_genre_ids  # Comedy
        assert 27 in intent.excluded_genre_ids  # Horror
        # Comedy and Horror must NOT be in positive genre_ids!
        assert 35 not in intent.genre_ids
        assert 27 not in intent.genre_ids

    def test_natural_language_era_and_language(self):
        """Natural language description with era constraints and languages."""
        prompt = "I want a 90s animated movie in Japanese, feel-good and heartwarming with aliens."
        intent = parse_query_intent(prompt)
        assert intent.is_recommendation is True
        assert "ja" in intent.languages
        assert 16 in intent.genre_ids  # Animation
        assert intent.era is not None
        assert intent.era.start_year == 1990 and intent.era.end_year == 1999
        assert "heartwarming" in intent.moods

    def test_unsupported_or_gibberish_query(self):
        """Gibberish or unknown queries should fallback safely to exact title search."""
        intent = parse_query_intent("asdfghjk qwertyuiop")
        assert intent.intent_type == "exact_title"
        assert intent.is_recommendation is False
        assert intent.clean_title == "asdfghjk qwertyuiop"
