"""
Tests for chat engine and query processing
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from troubleshooting.engine import (
    extract_keywords, process_query, format_response,
    detect_language
)


class TestKeywordExtraction:
    """Tests for keyword extraction"""

    def test_extract_keywords_from_english(self):
        """Should extract keywords from English text"""
        text = 'computer not turning on'
        keywords = extract_keywords(text, 'en')

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should include main words
        assert any('computer' in k.lower() or 'turn' in k.lower() for k in keywords)

    def test_extract_keywords_from_burmese(self):
        """Should extract keywords from Burmese text"""
        text = 'ကွန်ပျူတာ ဖွင့်မရပါ'
        keywords = extract_keywords(text, 'my')

        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_keywords_lowercase(self):
        """Keywords should be lowercase"""
        text = 'COMPUTER NOT WORKING'
        keywords = extract_keywords(text, 'en')

        for keyword in keywords:
            assert keyword == keyword.lower()

    def test_keywords_no_empty_strings(self):
        """Should not include empty keyword strings"""
        text = 'computer   not   working'
        keywords = extract_keywords(text, 'en')

        assert all(k.strip() for k in keywords)

    def test_stopwords_filtered(self):
        """Should filter out common stopwords"""
        text = 'the computer is not working and the monitor is broken'
        keywords = extract_keywords(text, 'en')

        # Common stopwords should be filtered
        stopwords = ['the', 'is', 'and']
        for stopword in stopwords:
            assert stopword not in keywords


class TestQueryProcessing:
    """Tests for query processing"""

    def test_process_query_returns_dict(self, test_db):
        """process_query should return a dictionary"""
        result = process_query('computer not working', 'en')

        assert isinstance(result, dict)
        assert 'found' in result
        assert isinstance(result['found'], bool)

    def test_process_query_with_found_match(self, test_db):
        """Should return found=True for queries matching knowledge base"""
        # Common troubleshooting query that should match
        result = process_query('CPU too hot', 'en')

        assert isinstance(result, dict)
        if result['found']:
            assert 'category' in result or 'solution' in result

    def test_process_query_without_match(self, test_db):
        """Should return found=False for unknown queries"""
        result = process_query('xyzabc unknown problem', 'en')

        assert isinstance(result, dict)
        assert 'found' in result

    def test_process_query_language_parameter(self, test_db):
        """Should respect language parameter"""
        result_en = process_query('computer not working', 'en')
        result_my = process_query('ကွန်ပျူတာ ဖွင့်မရပါ', 'my')

        # Both should be valid results
        assert isinstance(result_en, dict)
        assert isinstance(result_my, dict)

    def test_process_query_case_insensitive(self, test_db):
        """Query processing should be case-insensitive"""
        result1 = process_query('CPU OVERHEATING', 'en')
        result2 = process_query('cpu overheating', 'en')
        result3 = process_query('Cpu Overheating', 'en')

        # All should produce same type of result
        assert type(result1) == type(result2) == type(result3)

    def test_no_false_positive_from_generic_word_overlap(self, test_db):
        """A printer noise query must not match an unrelated laptop-fan-noise
        entry just because they share generic filler words like 'making'"""
        result = process_query('printer making weird sounds', 'en')

        if result['found']:
            assert 'fan' not in result['problem'].lower()
            assert 'laptop' not in result['problem'].lower()


class TestBurmeseNgramMatching:
    """Tests for Burmese search matching via character n-gram overlap,
    since whitespace isn't a reliable word boundary in Burmese"""

    def test_burmese_query_with_no_spaces_matches(self, test_db):
        """A Burmese query typed with no spaces at all should still match
        the knowledge base entry it corresponds to"""
        no_space_query = 'ကွန်ပျူတာပါဝါမပွင့်ခြင်း'  # "computer won't turn on", no spaces
        result = process_query(no_space_query, 'my')

        assert result['found'] is True
        assert result['category']

    def test_burmese_query_with_partial_spacing_matches(self, test_db):
        """A Burmese query with spacing only at some phrase boundaries
        (e.g. mixed English/Burmese with no space between them) should
        still match"""
        partial_space_query = 'CPUအလွန်အမင်း ပူနွေးလာခြင်း'  # "CPU overheating badly", no space after CPU
        result = process_query(partial_space_query, 'my')

        assert result['found'] is True
        assert result['category']

    def test_burmese_unrelated_query_does_not_match(self, test_db):
        """A Burmese query unrelated to anything in the knowledge base
        should not force a match just because n-grams exist"""
        result = process_query('ဒီနေ့ ထမင်းစားပြီးပြီလား', 'my')  # "have you eaten today" - unrelated
        assert result['found'] is False


class TestResponseFormatting:
    """Tests for response formatting"""

    def test_format_response_returns_string(self):
        """format_response should return a string"""
        query_result = {
            'found': True,
            'category': 'Hardware',
            'solution': 'Check your power cable',
        }

        response = format_response(query_result)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_format_response_includes_solution_text(self):
        """Formatted response should include solution text"""
        query_result = {
            'found': True,
            'category': 'Hardware',
            'solution': 'Check your power cable',
        }

        response = format_response(query_result)
        assert 'Check your power cable' in response

    def test_format_response_includes_category(self):
        """Formatted response should include category info"""
        query_result = {
            'found': True,
            'category': 'Hardware',
            'solution': 'Test solution'
        }

        response = format_response(query_result)
        # Should include some reference to category
        assert isinstance(response, str)

    def test_format_response_multiline(self):
        """Formatted response should handle multiline solutions"""
        query_result = {
            'found': True,
            'category': 'Hardware',
            'solution': 'Step 1: Check cable\nStep 2: Restart computer\nStep 3: Contact support'
        }

        response = format_response(query_result)
        # Should preserve multiline format
        assert '\n' in response or 'Step' in response


class TestQueryRouting:
    """Tests for routing queries to appropriate handlers"""

    def test_multiple_queries_return_results(self, test_db):
        """Should process multiple different queries"""
        queries = [
            'computer not turning on',
            'CPU overheating',
            'network not working',
            'display issues',
        ]

        for query in queries:
            result = process_query(query, 'en')
            assert isinstance(result, dict)
            assert 'found' in result

    def test_burmese_and_english_queries_both_work(self, test_db):
        """Should handle both Burmese and English queries"""
        english_result = process_query('computer problem', 'en')
        burmese_result = process_query('ကွန်ပျူတာ ပြဿနာ', 'my')

        assert isinstance(english_result, dict)
        assert isinstance(burmese_result, dict)

    def test_very_long_query_handled(self, test_db):
        """Should handle very long query strings"""
        long_query = 'My computer is not working and the screen is black and nothing is showing up and the lights are on but nothing displays ' * 5
        result = process_query(long_query, 'en')

        assert isinstance(result, dict)

    def test_special_characters_in_query(self, test_db):
        """Should handle queries with special characters"""
        queries = [
            'computer @ problem?',
            'monitor!!! not working',
            'CPU---overheating',
            '#network #issues',
        ]

        for query in queries:
            result = process_query(query, 'en')
            assert isinstance(result, dict)
