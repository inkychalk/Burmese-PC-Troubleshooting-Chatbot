"""
Troubleshooting Engine
Handles intent matching, language detection, and response generation.
Flow: User Query -> Language Detection -> DB Search -> (if not found) LLM Fallback -> Save
"""

import re
from database.models import search_troubleshooting, save_learned_response, generate_char_ngrams

# Ratio of overlapping character n-grams (Dice coefficient) required for a
# Burmese query to count as a match. Burmese isn't reliably space-delimited,
# so a percentage-based overlap is used instead of a fixed keyword count.
BURMESE_MATCH_THRESHOLD = 0.4


def detect_language(text):
    """
    Simple language detection based on Unicode ranges.
    Burmese Unicode block: U+1000–U+109F
    """
    burmese_pattern = re.compile(r'[\u1000-\u109F]')
    if burmese_pattern.search(text):
        return 'my'
    return 'en'


def extract_keywords(text, language='en'):
    """
    Extract meaningful keywords from user query for matching.

    English: split on whitespace, lowercase, strip punctuation, filter stop
    words and short tokens.

    Burmese: whitespace isn't a reliable word boundary (users often type
    whole phrases with no spaces, or space only at phrase boundaries), so
    whitespace-split "words" are not returned. Instead this returns
    character n-grams, which don't depend on spacing at all.
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s\u1000-\u109F]', ' ', text)

    if language == 'en':
        stop_words_en = {
            'the', 'a', 'an', 'is', 'are', 'and', 'or', 'my', 'i', 'to', 'not',
            'won\'t', 'cant', 'doesnt', 'making', 'getting', 'having', 'doing', 'being',
        }
        words = text.split()
        return [w for w in words if w not in stop_words_en and len(w) > 2]

    return sorted(generate_char_ngrams(text))


def process_query(user_message, language=None):
    """
    Main entry point for processing a troubleshooting query.

    Args:
        user_message: The raw text from the user
        language: Optional override ('en', 'my'). Auto-detected if not provided.

    Returns:
        dict with keys: found, category, problem, solution, source, language
    """
    if language is None:
        language = detect_language(user_message)

    # Step 1: Search local knowledge base
    keywords = extract_keywords(user_message, language)

    results = search_troubleshooting(
        query=user_message,
        language=language,
        limit=3,
        keywords=keywords if keywords else None
    )

    if language == 'my':
        # match_score is a 0..1 n-gram overlap ratio for Burmese, not a
        # keyword count, since whitespace-split "keyword count" isn't a
        # stable unit for Burmese without real word segmentation.
        results = [r for r in results if r.get('match_score', 0) >= BURMESE_MATCH_THRESHOLD]
    else:
        # Require at least 2 keyword matches (or 1 if query was very short) to
        # avoid false positives from a single generic word matching many rows.
        min_score = 1 if len(keywords) <= 1 else 2
        results = [r for r in results if r.get('match_score', 0) >= min_score]

    if results:
        best_match = results[0]
        return {
            'found': True,
            'source': 'database',
            'language': language,
            'category': best_match['category'],
            'problem': best_match[f'problem_{language}'],
            'solution': best_match[f'solution_{language}'],
            'all_matches': results
        }

    # Step 2: Not found in DB -> fallback to LLM (Gemini)
    # This is a placeholder; actual Gemini call happens in integrations/gemini.py
    return {
        'found': False,
        'source': 'llm_needed',
        'language': language,
        'query': user_message,
        'keywords': keywords
    }


def format_response(result, include_category=True):
    """
    Format the engine's result into a user-friendly chat response.
    """
    if not result['found']:
        if result['language'] == 'my':
            return "ဆောရီးပါ၊ ဒီပြဿနာအတွက် အဖြေရှာမတွေ့သေးပါ။ AI ကို မေးမြန်းပေးပါမည်..."
        return "Sorry, I couldn't find a direct match. Let me ask our AI assistant..."

    response = result['solution']
    if include_category:
        prefix = f"[{result['category']}]\n\n"
        response = prefix + response

    return response
