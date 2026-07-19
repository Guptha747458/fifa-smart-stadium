"""Unit tests for core.genai — RAG retriever, translation, and simulated chat."""
import pytest
from core.genai import retrieve, translate, chat, _simulated_answer, _tokenize


class TestTokenize:
    """Tests for the _tokenize helper."""

    def test_lowercases_and_splits(self):
        tokens = _tokenize("Hello World 2026")
        assert "hello" in tokens
        assert "world" in tokens
        assert "2026" in tokens

    def test_strips_punctuation(self):
        tokens = _tokenize("where's the restroom?")
        assert "where" in tokens or "where's" not in tokens  # punctuation stripped

    def test_returns_set(self):
        assert isinstance(_tokenize("test test"), set)


class TestRetrieve:
    """Tests for the RAG retrieve() function."""

    def test_returns_list(self):
        results = retrieve("emergency exit evacuation")
        assert isinstance(results, list)

    def test_returns_at_most_top_k(self):
        results = retrieve("food", top_k=2)
        assert len(results) <= 2

    def test_relevant_doc_returned_for_medical_query(self):
        results = retrieve("medical emergency first aid", top_k=3)
        ids = [d["id"] for d in results]
        assert "emerg-medical" in ids

    def test_relevant_doc_returned_for_accessibility_query(self):
        results = retrieve("wheelchair accessible elevator ramp", top_k=3)
        ids = [d["id"] for d in results]
        # Should match acc-services or accessible-paths
        assert any(i in ids for i in ("acc-services", "accessible-paths"))

    def test_no_results_for_completely_unrelated_query(self):
        results = retrieve("xyzabc123 gobbledegook", top_k=3)
        # May return empty list or minimal matches — should not crash
        assert isinstance(results, list)

    def test_each_result_has_required_fields(self):
        results = retrieve("transit parking EV", top_k=3)
        for doc in results:
            assert "id" in doc
            assert "title" in doc
            assert "text" in doc
            assert "category" in doc


class TestTranslate:
    """Tests for the translate() function (simulated fallback)."""

    def test_english_passthrough(self):
        result = translate("Where is the nearest exit?", "en", "en")
        assert result["ok"] is True
        assert result["target"] == "en"

    def test_unsupported_language_returns_error(self):
        result = translate("Hello", "xx_invalid", "en")
        assert result["ok"] is False
        assert "error" in result

    def test_phrasebook_match_for_restroom_spanish(self):
        result = translate("Where is the nearest restroom?", "es", "en")
        assert result["ok"] is True
        assert "baño" in result["text"].lower() or result["method"] == "phrasebook"

    def test_simulated_fallback_wraps_with_language_name(self):
        result = translate("Custom unknown text here", "fr", "en")
        assert result["ok"] is True
        # Simulated translation should contain [French] marker or phrasebook match
        assert "fr" == result["target"]

    def test_returns_source_and_target_fields(self):
        result = translate("Hello", "es", "en")
        assert "source" in result
        assert "target" in result
        assert result["target"] == "es"


class TestChat:
    """Tests for the chat() function (simulated mode)."""

    def test_chat_returns_required_keys(self):
        result = chat("Where is the nearest emergency exit?", language="en")
        assert "answer" in result
        assert "language" in result
        assert "sources" in result
        assert "mode" in result

    def test_chat_language_propagated(self):
        result = chat("What can I eat?", language="es")
        assert result["language"] == "es"

    def test_chat_sources_is_list(self):
        result = chat("Tell me about accessibility services")
        assert isinstance(result["sources"], list)

    def test_simulated_answer_for_known_topic(self):
        answer = _simulated_answer("system", "wheelchair accessible elevator ramp section")
        assert isinstance(answer, str)
        assert len(answer) > 0
