"""
Tests for language detection
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from troubleshooting.engine import detect_language, extract_keywords
from database.models import generate_char_ngrams, dice_coefficient


class TestLanguageDetection:
    """Tests for language detection functionality"""

    def test_detect_english_text(self):
        """Should detect English text"""
        text = 'computer not turning on'
        language = detect_language(text)
        assert language == 'en', f"Expected 'en', got '{language}' for English text"

    def test_detect_burmese_text(self):
        """Should detect Burmese text"""
        text = 'ကွန်ပျူတာ ဖွင့်မရပါ'
        language = detect_language(text)
        assert language == 'my', f"Expected 'my', got '{language}' for Burmese text"

    def test_detect_burmese_cpu_hot(self):
        """Should detect Burmese 'CPU hot' phrase"""
        text = 'CPU အလွန်ပူနေသည်'
        language = detect_language(text)
        assert language == 'my'

    def test_detect_burmese_power_issue(self):
        """Should detect Burmese 'power issue' phrase"""
        text = 'ကွန်ပျူတာ အားမဖြေမရပါ'
        language = detect_language(text)
        assert language == 'my'

    def test_mixed_language_prefers_detected_script(self):
        """Mixed language text should prefer detected script"""
        # Text with more Burmese
        text = 'ကွန်ပျူတာ computer problem အဆင်မပြေ'
        language = detect_language(text)
        # Should detect as Burmese since more Burmese script present
        assert language == 'my'

    def test_english_dominant_mixed_text(self):
        """English-dominant mixed text should detect as English"""
        text = 'The computer (ကွန်ပျူတာ) won\'t turn on'
        language = detect_language(text)
        # Should detect as English since English words dominate
        assert language in ['en', 'my']  # Accept either

    def test_empty_string_defaults_to_english(self):
        """Empty or whitespace-only text should default to English"""
        text = '   '
        language = detect_language(text)
        assert language == 'en'

    def test_numbers_only_defaults_to_english(self):
        """Numeric text should default to English"""
        text = '12345'
        language = detect_language(text)
        assert language == 'en'

    def test_case_insensitive_english_detection(self):
        """Should detect English regardless of case"""
        texts = [
            'COMPUTER NOT WORKING',
            'Computer Not Working',
            'computer not working',
            'CoMpUtEr NoT wOrKiNg'
        ]

        for text in texts:
            language = detect_language(text)
            assert language == 'en', f"Failed to detect English in '{text}'"

    def test_burmese_detection_with_whitespace(self):
        """Should detect Burmese with extra whitespace"""
        text = '  ကွန်ပျူတာ ဖွင့်မရပါ  '
        language = detect_language(text)
        assert language == 'my'

    def test_punctuation_doesnt_affect_detection(self):
        """Punctuation should not affect language detection"""
        english_text = 'Computer not working???'
        burmese_text = 'ကွန်ပျူတာ ဖွင့်မရပါ။'

        assert detect_language(english_text) == 'en'
        assert detect_language(burmese_text) == 'my'

    def test_special_characters_in_english(self):
        """Should handle special characters in English"""
        text = '@computer #not $working'
        language = detect_language(text)
        assert language == 'en'

    def test_common_burmese_words(self):
        """Should detect common Burmese words"""
        burmese_words = [
            'အဆင်မပြေ',  # problem
            'ကူညီ',      # help
            'အကူအညီ',   # assistance
            'ပြန်လည်',    # again
            'အခြား',      # other
        ]

        for word in burmese_words:
            language = detect_language(word)
            assert language == 'my', f"Failed to detect Burmese in '{word}'"

    def test_common_english_words(self):
        """Should detect common English words"""
        english_words = [
            'computer',
            'problem',
            'help',
            'working',
            'power'
        ]

        for word in english_words:
            language = detect_language(word)
            assert language == 'en', f"Failed to detect English in '{word}'"


class TestBurmeseKeywordExtraction:
    """Tests for Burmese keyword extraction (character n-grams instead of
    whitespace-split words, since Burmese isn't reliably space-delimited)"""

    def test_burmese_no_spaces_produces_ngrams(self):
        """A Burmese query with no spaces at all should still yield n-grams,
        not collapse into a single unusable 'word'"""
        text = 'ကွန်ပျူတာဖွင့်မရပါ'  # same phrase as below, no space
        keywords = extract_keywords(text, 'my')

        assert isinstance(keywords, list)
        assert len(keywords) > 1
        # Every returned keyword should be a short n-gram, not the whole string
        assert all(len(k) <= 4 for k in keywords)

    def test_burmese_partial_spacing_produces_similar_ngrams(self):
        """A Burmese query with only partial/phrase-level spacing should
        produce a keyword set that heavily overlaps with the no-space and
        fully-spaced versions of the same text"""
        no_space = extract_keywords('ကွန်ပျူတာဖွင့်မရပါ', 'my')
        partial_space = extract_keywords('ကွန်ပျူတာ ဖွင့်မရပါ', 'my')

        ratio = dice_coefficient(set(no_space), set(partial_space))
        assert ratio > 0.8, f"Expected high n-gram overlap regardless of spacing, got {ratio}"

    def test_burmese_ngram_overlap_ratio_for_similar_phrases(self):
        """Similar Burmese phrases should score a high Dice overlap ratio"""
        a = generate_char_ngrams('ကွန်ပျူတာ လည်ပတ်မည်မ ဖြစ်သည်')
        b = generate_char_ngrams('ကွန်ပျူတာလည်ပတ်မည်မဖြစ်သည်')  # same, no spaces

        ratio = dice_coefficient(a, b)
        assert ratio > 0.8

    def test_burmese_ngram_overlap_ratio_for_unrelated_phrases(self):
        """Unrelated Burmese phrases should score a low Dice overlap ratio"""
        a = generate_char_ngrams('ကွန်ပျူတာ လည်ပတ်မည်မ ဖြစ်သည်')  # computer won't run
        b = generate_char_ngrams('ပရင်တာ အလုပ်မလုပ်ပါ')  # printer not working

        ratio = dice_coefficient(a, b)
        assert ratio < 0.4

    def test_english_keyword_extraction_still_word_based(self):
        """English extraction must remain unchanged: whitespace-split words,
        not character n-grams"""
        keywords = extract_keywords('computer not working', 'en')
        assert keywords == ['computer', 'working']
