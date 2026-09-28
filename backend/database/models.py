"""
Database models and initialization for Burmese PC Troubleshooting Chatbot
Uses SQLite for lightweight, Docker-friendly storage
"""

import sqlite3
import json
import os
import random
import re
import math
from collections import Counter
from datetime import datetime, timedelta

DB_PATH = os.environ.get('DATABASE_PATH', '/data/db.sqlite')

# Burmese text isn't reliably space-delimited between words the way English
# is (users often type whole phrases with no spaces, or spaces only at
# phrase boundaries), so whitespace-split "word count" isn't a stable unit
# for Burmese matching. Character n-grams sidestep tokenization entirely.
BURMESE_NGRAM_SIZE = 3


def generate_char_ngrams(text, n=BURMESE_NGRAM_SIZE):
    """Generate overlapping character n-grams from text, ignoring whitespace."""
    cleaned = re.sub(r'\s+', '', text or '')
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + n] for i in range(len(cleaned) - n + 1)}


def dice_coefficient(set_a, set_b):
    """Dice coefficient (overlap ratio, 0..1) between two sets of n-grams."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    return 2 * intersection / (len(set_a) + len(set_b))


def compute_ngram_idf(ngram_sets):
    """
    Compute inverse-document-frequency weights for n-grams across a corpus.

    Plain (unweighted) Dice overlap treats every n-gram as equally
    informative, but Burmese troubleshooting entries share a lot of generic
    connector words and grammar particles (e.g. "ကြောင်း", "ပြသခြင်း",
    "install", "error") regardless of topic. Two genuinely different
    problems that both happen to use that boilerplate phrasing can score a
    deceptively high overlap ratio, causing wrong-answer matches. Weighting
    each n-gram by how rare it is across the knowledge base down-weights
    that boilerplate and up-weights the topic-specific n-grams that
    actually distinguish one problem from another.
    """
    n_docs = len(ngram_sets)
    doc_freq = Counter()
    for ngrams in ngram_sets:
        doc_freq.update(ngrams)
    return {gram: math.log(n_docs / (1 + freq)) for gram, freq in doc_freq.items()}


def weighted_dice_coefficient(set_a, set_b, idf, default_idf=None):
    """
    IDF-weighted Dice coefficient (overlap ratio, 0..1) between two n-gram sets.

    `default_idf` is the weight given to n-grams absent from the reference
    corpus `idf` was computed from. Pass the corpus's own "never seen"
    weight (math.log(n_docs)) when available so the default is on the same
    scale as the rest of the weights; an unscaled default here (e.g. a
    fixed constant) can distort scores when the corpus is small.
    """
    if not set_a or not set_b:
        return 0.0
    if default_idf is None:
        default_idf = math.log(2)
    weight_a = sum(idf.get(g, default_idf) for g in set_a)
    weight_b = sum(idf.get(g, default_idf) for g in set_b)
    if weight_a + weight_b == 0:
        return 0.0
    weight_intersection = sum(idf.get(g, default_idf) for g in (set_a & set_b))
    return 2 * weight_intersection / (weight_a + weight_b)


def get_burmese_background_idf():
    """
    IDF weights computed from the full troubleshooting knowledge base's
    Burmese text (~150 entries), used as a stable reference corpus for
    scoring n-gram overlap.

    This is reused for both DB search and cache-lookup scoring rather than
    computing IDF from whatever's in `learned_responses` at the time: that
    table can have as few as 1-2 rows, and IDF computed from such a tiny
    corpus is unstable (can even go negative), which let clearly unrelated
    queries score a deceptively high "cache hit" ratio.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT problem_my, symptoms_my FROM troubleshooting')
    rows = cursor.fetchall()
    conn.close()

    ngram_sets = [generate_char_ngrams(f"{r['problem_my']} {r['symptoms_my']}") for r in rows]
    idf = compute_ngram_idf(ngram_sets) if ngram_sets else {}
    default_idf = math.log(len(ngram_sets)) if ngram_sets else math.log(2)
    return idf, default_idf


ADMIN_CONFIG_DEFAULTS = {
    'rate_limit_per_minute': 20,
    'rate_limit_per_day': 500,
    'gemini_daily_cap': 300,
    'concurrent_request_stale_seconds': 60,
    'active_session_window_minutes': 5,
    'admin_login_limit_per_minute': 5,
}


def get_connection():
    """Get a SQLite database connection with WAL mode and busy timeout"""
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()

    # Main troubleshooting knowledge base
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS troubleshooting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            problem_en TEXT NOT NULL,
            problem_my TEXT NOT NULL,
            symptoms_en TEXT,
            symptoms_my TEXT,
            solution_en TEXT NOT NULL,
            solution_my TEXT NOT NULL,
            source TEXT DEFAULT 'seed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Conversation history / learned responses from LLM fallback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_query TEXT NOT NULL,
            language TEXT NOT NULL,
            matched_category TEXT,
            llm_response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chat sessions (for tracking conversations across platforms)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            user_id TEXT NOT NULL,
            language_preference TEXT DEFAULT 'my',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chat messages log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            language TEXT,
            source TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        )
    ''')

    # Admin configuration (editable limits and settings)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Rate limit request log (sliding window enforcement)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            user_id TEXT,
            endpoint TEXT NOT NULL,
            blocked INTEGER NOT NULL DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_request_log_identifier
        ON request_log(identifier, endpoint, timestamp)
    ''')

    # Gemini API call tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gemini_call_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            function_name TEXT NOT NULL,
            success INTEGER NOT NULL,
            error_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # In-flight request tracking (for concurrency metrics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inflight_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: Add missing columns
    try:
        cursor.execute('PRAGMA table_info(chat_messages)')
        columns = [row[1] for row in cursor.fetchall()]
        if 'source' not in columns:
            cursor.execute('ALTER TABLE chat_messages ADD COLUMN source TEXT')
            print("✅ Added missing 'source' column to chat_messages")
    except sqlite3.OperationalError as e:
        print(f"⚠️  Migration check failed: {e}")

    conn.commit()
    conn.close()
    print("✅ Database schema initialized")


def seed_data(json_path='/app/database/troubleshooting_data.json'):
    """Load seed data from JSON file into database (only if empty)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute('SELECT COUNT(*) as count FROM troubleshooting')
    count = cursor.fetchone()['count']

    if count > 0:
        print(f"ℹ️  Database already has {count} entries. Skipping seed.")
        conn.close()
        return

    if not os.path.exists(json_path):
        print(f"⚠️  Seed file not found: {json_path}")
        conn.close()
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for entry in data:
        cursor.execute('''
            INSERT INTO troubleshooting
            (category, problem_en, problem_my, symptoms_en, symptoms_my, solution_en, solution_my, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'seed')
        ''', (
            entry.get('category', ''),
            entry.get('problem_en', ''),
            entry.get('problem_my', ''),
            entry.get('symptoms_en', ''),
            entry.get('symptoms_my', ''),
            entry.get('solution_en', ''),
            entry.get('solution_my', '')
        ))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(data)} troubleshooting entries")


def seed_admin_config():
    """Seed admin_config with default values (only if not already set)"""
    conn = get_connection()
    cursor = conn.cursor()

    for key, value in ADMIN_CONFIG_DEFAULTS.items():
        cursor.execute('''
            INSERT OR IGNORE INTO admin_config (key, value)
            VALUES (?, ?)
        ''', (key, str(value)))

    conn.commit()
    conn.close()
    print("✅ Admin config seeded with defaults")


def search_troubleshooting(query, language='en', limit=5, keywords=None):
    """
    Search the troubleshooting knowledge base.

    For English, scores each row by how many whitespace-split keywords match
    across problem/symptom fields (SQL LIKE), and returns the best matches
    ordered by score.

    For Burmese, whitespace isn't a reliable word boundary, so whitespace-
    split keyword counting doesn't work. Instead, candidate rows are fetched
    broadly and re-scored in Python using IDF-weighted character n-gram
    overlap (weighted Dice coefficient) between the query and each row's
    problem/symptom text. Plain (unweighted) overlap let two different
    problems that share generic connector words/grammar particles (e.g.
    "ကြောင်း", "install", "error") score a deceptively high match, so
    n-grams are weighted by how rare they are across the whole knowledge
    base, down-weighting that boilerplate. `match_score` is therefore a
    0..1 ratio for Burmese, not a keyword count.

    Args:
        query: raw query string (used as single-keyword fallback if keywords not given,
            and as the basis for n-gram scoring when language='my')
        keywords: optional list of individual keywords for OR-based matching (English only)
    """
    conn = get_connection()
    cursor = conn.cursor()

    if language == 'my':
        query_ngrams = generate_char_ngrams(query)
        cursor.execute('SELECT * FROM troubleshooting')
        rows = cursor.fetchall()
        conn.close()

        row_ngram_sets = [generate_char_ngrams(f"{r['problem_my']} {r['symptoms_my']}") for r in rows]
        idf = compute_ngram_idf(row_ngram_sets + [query_ngrams])

        scored = []
        for row, row_ngrams in zip(rows, row_ngram_sets):
            ratio = weighted_dice_coefficient(query_ngrams, row_ngrams, idf)
            if ratio > 0:
                row_dict = dict(row)
                row_dict['match_score'] = ratio
                scored.append(row_dict)

        scored.sort(key=lambda r: r['match_score'], reverse=True)
        return scored[:limit]

    field = 'problem_en'
    symptom_field = 'symptoms_en'

    terms = keywords if keywords else [query]
    terms = [t for t in terms if t.strip()]

    if not terms:
        conn.close()
        return []

    # Build a WHERE clause that matches ANY keyword, and a score expression
    # that counts how many keywords matched (for ranking).
    where_clauses = []
    score_parts = []
    score_params = []
    where_params = []

    for term in terms:
        like_term = f'%{term}%'
        where_clauses.append(f'({field} LIKE ? OR {symptom_field} LIKE ?)')
        where_params.extend([like_term, like_term])
        score_parts.append(f'(CASE WHEN {field} LIKE ? OR {symptom_field} LIKE ? THEN 1 ELSE 0 END)')
        score_params.extend([like_term, like_term])

    where_sql = ' OR '.join(where_clauses)
    score_sql = ' + '.join(score_parts)

    sql = f'''
        SELECT *, ({score_sql}) as match_score
        FROM troubleshooting
        WHERE {where_sql}
        ORDER BY match_score DESC
        LIMIT ?
    '''
    # Params must follow the order placeholders appear in `sql`: score_sql
    # (in SELECT) comes before where_sql (in WHERE).
    params = score_params + where_params + [limit]

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def save_learned_response(user_query, language, category, llm_response):
    """Save a new LLM-generated response for future reuse"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO learned_responses (user_query, language, matched_category, llm_response)
        VALUES (?, ?, ?, ?)
    ''', (user_query, language, category, llm_response))

    conn.commit()
    conn.close()


def get_or_create_session(platform, user_id):
    """Get existing session or create a new one"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM chat_sessions WHERE platform = ? AND user_id = ?
    ''', (platform, user_id))
    session = cursor.fetchone()

    if session:
        cursor.execute('''
            UPDATE chat_sessions SET last_active = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session['id'],))
        conn.commit()
        conn.close()
        return dict(session)

    cursor.execute('''
        INSERT INTO chat_sessions (platform, user_id) VALUES (?, ?)
    ''', (platform, user_id))
    conn.commit()

    session_id = cursor.lastrowid
    cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
    session = dict(cursor.fetchone())
    conn.close()
    return session


def log_message(session_id, role, message, language='my', source=None):
    """Log a chat message"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO chat_messages (session_id, role, message, language, source)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, role, message, language, source))

    conn.commit()
    conn.close()


# Reusing a cached LLM answer for the wrong question is more visibly wrong
# than a troubleshooting-DB miss (it reads as a confident answer to a
# different topic), so cache reuse for Burmese requires a stricter overlap
# ratio than the troubleshooting-DB match threshold.
CACHE_BURMESE_MATCH_THRESHOLD = 0.55


def get_cached_response(user_query, language, keywords=None, threshold=2):
    """
    Search learned_responses for a similar cached response to avoid repeat
    LLM API calls for the same/similar question.

    For English, scores cached rows by how many whitespace-split keywords
    appear in the cached query (SQL LIKE), same mechanism as before.

    For Burmese, `keywords` are character n-grams (see extract_keywords),
    not whitespace-split words, so a keyword-*count* threshold isn't
    meaningful: two completely unrelated questions that happen to share
    even a couple of 3-char fragments (e.g. both mention "windows 11")
    could hit a low count threshold and return a wrong, off-topic cached
    answer. Instead this re-scores candidate rows in Python using
    IDF-weighted n-gram overlap (Dice coefficient) against each cached
    user_query, and requires a meaningfully high overlap ratio.

    Args:
        user_query: The user's query
        language: The language (en or my)
        keywords: List of keywords extracted from the query (English: words, Burmese: n-grams)
        threshold: English only - minimum number of matching keywords to consider a cache hit

    Returns:
        dict with cached response if found, None otherwise
    """
    if not keywords:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    if language == 'my':
        cursor.execute('SELECT * FROM learned_responses WHERE language = ?', (language,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        query_ngrams = set(keywords)
        row_ngram_sets = [generate_char_ngrams(row['user_query']) for row in rows]
        # learned_responses is often just a handful of rows, too small for
        # stable IDF stats on its own (see get_burmese_background_idf), so
        # score against the much larger troubleshooting corpus instead.
        idf, default_idf = get_burmese_background_idf()

        best_row, best_ratio = None, 0.0
        for row, row_ngrams in zip(rows, row_ngram_sets):
            ratio = weighted_dice_coefficient(query_ngrams, row_ngrams, idf, default_idf)
            if ratio > best_ratio:
                best_row, best_ratio = row, ratio

        if best_row and best_ratio >= CACHE_BURMESE_MATCH_THRESHOLD:
            return {
                'llm_response': best_row['llm_response'],
                'matched_category': best_row['matched_category'],
                'source': 'cache'
            }
        return None

    # English: keyword-count based (unchanged mechanism)
    keyword_patterns = ['%' + k + '%' for k in keywords]

    placeholders = ' OR '.join(['user_query LIKE ?' for _ in keyword_patterns])
    score_sql = ' + '.join(['(CASE WHEN user_query LIKE ? THEN 1 ELSE 0 END)' for _ in keyword_patterns])
    query_sql = f'''
        SELECT *,
               ({score_sql}) as keyword_matches
        FROM learned_responses
        WHERE language = ? AND ({placeholders})
        GROUP BY id
        HAVING keyword_matches >= ?
        ORDER BY keyword_matches DESC, created_at DESC
        LIMIT 1
    '''

    params = keyword_patterns + [language] + keyword_patterns + [threshold]

    try:
        cursor.execute(query_sql, params)
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'llm_response': result['llm_response'],
                'matched_category': result['matched_category'],
                'source': 'cache'
            }
    except Exception as e:
        print(f"Cache lookup error: {e}")
        conn.close()

    return None


def get_admin_config():
    """Get all admin configuration as a dict with int values"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM admin_config')
    config = {row['key']: int(row['value']) for row in cursor.fetchall()}
    conn.close()
    return config


def update_admin_config(updates):
    """Update admin config with validated changes"""
    if not updates:
        return get_admin_config()

    for key, value in updates.items():
        if key not in ADMIN_CONFIG_DEFAULTS:
            raise ValueError(f"Unknown config key: {key}")
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"Config value must be positive integer: {key}={value}")

    conn = get_connection()
    cursor = conn.cursor()

    for key, value in updates.items():
        cursor.execute('''
            INSERT OR REPLACE INTO admin_config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, str(value)))

    conn.commit()
    conn.close()

    return get_admin_config()


def check_and_record_rate_limit(identifier, endpoint, user_id=None):
    """
    Check and record rate limit for a given identifier (IP address).
    Returns (allowed: bool, info: dict)
    """
    conn = get_connection()
    cursor = conn.cursor()
    config = get_admin_config()

    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    day_ago = now - timedelta(days=1)

    minute_count = cursor.execute('''
        SELECT COUNT(*) as count FROM request_log
        WHERE identifier = ? AND endpoint = ? AND timestamp > ?
    ''', (identifier, endpoint, minute_ago.isoformat())).fetchone()['count']

    day_count = cursor.execute('''
        SELECT COUNT(*) as count FROM request_log
        WHERE identifier = ? AND endpoint = ? AND timestamp > ?
    ''', (identifier, endpoint, day_ago.isoformat())).fetchone()['count']

    per_minute_limit = config.get('rate_limit_per_minute', 20)
    per_day_limit = config.get('rate_limit_per_day', 500)

    blocked = 0
    limit_type = None

    if minute_count >= per_minute_limit:
        blocked = 1
        limit_type = 'minute'
    elif day_count >= per_day_limit:
        blocked = 1
        limit_type = 'day'

    cursor.execute('''
        INSERT INTO request_log (identifier, user_id, endpoint, blocked)
        VALUES (?, ?, ?, ?)
    ''', (identifier, user_id, endpoint, blocked))

    conn.commit()

    lazy_prune_chance = 100
    if random.randint(1, lazy_prune_chance) == 1:
        two_days_ago = now - timedelta(days=2)
        cursor.execute('DELETE FROM request_log WHERE timestamp < ?', (two_days_ago.isoformat(),))
        conn.commit()

    conn.close()

    return (blocked == 0, {'limit_type': limit_type})


def log_inflight_start(endpoint):
    """Record start of in-flight request processing"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO inflight_requests (endpoint) VALUES (?)', (endpoint,))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def log_inflight_end(row_id):
    """Record end of in-flight request processing"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM inflight_requests WHERE id = ?', (row_id,))
    conn.commit()
    conn.close()


def log_gemini_call(function_name, success, error_message=None):
    """Log a Gemini API call"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO gemini_call_log (function_name, success, error_message)
        VALUES (?, ?, ?)
    ''', (function_name, 1 if success else 0, error_message))
    conn.commit()
    conn.close()


def get_metrics_snapshot():
    """Get current metrics for the admin dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    config = get_admin_config()
    now = datetime.utcnow()

    stale_seconds = config.get('concurrent_request_stale_seconds', 60)
    stale_time = (now - timedelta(seconds=stale_seconds)).isoformat()

    concurrent_now = cursor.execute('''
        SELECT COUNT(*) as count FROM inflight_requests
        WHERE started_at > ?
    ''', (stale_time,)).fetchone()['count']

    active_window_minutes = config.get('active_session_window_minutes', 5)
    active_time = (now - timedelta(minutes=active_window_minutes)).isoformat()

    active_users = cursor.execute('''
        SELECT COUNT(DISTINCT user_id) as count FROM chat_sessions
        WHERE last_active > ?
    ''', (active_time,)).fetchone()['count']

    today = now.date().isoformat()

    gemini_today = cursor.execute('''
        SELECT COUNT(*) as total, SUM(success) as success FROM gemini_call_log
        WHERE DATE(timestamp) = ?
    ''', (today,)).fetchone()

    gemini_total = cursor.execute('''
        SELECT COUNT(*) as total FROM gemini_call_log
    ''').fetchone()['total']

    gemini_by_function = cursor.execute('''
        SELECT function_name, COUNT(*) as count FROM gemini_call_log
        WHERE DATE(timestamp) = ?
        GROUP BY function_name
    ''', (today,)).fetchall()

    gemini_today_total = gemini_today['total'] or 0
    gemini_today_success = gemini_today['success'] or 0
    gemini_daily_cap = config.get('gemini_daily_cap', 300)

    source_breakdown = cursor.execute('''
        SELECT source, COUNT(*) as count FROM chat_messages
        WHERE DATE(timestamp) = ? AND source IS NOT NULL
        GROUP BY source
    ''', (today,)).fetchall()

    rate_limited_today = cursor.execute('''
        SELECT COUNT(*) as count FROM request_log
        WHERE DATE(timestamp) = ? AND blocked = 1
    ''', (today,)).fetchone()['count']

    kb_size = cursor.execute('SELECT COUNT(*) as count FROM troubleshooting').fetchone()['count']
    learned_count = cursor.execute('SELECT COUNT(*) as count FROM learned_responses').fetchone()['count']
    session_count = cursor.execute('SELECT COUNT(*) as count FROM chat_sessions').fetchone()['count']
    message_count = cursor.execute('SELECT COUNT(*) as count FROM chat_messages').fetchone()['count']

    conn.close()

    return {
        'concurrent_requests_now': concurrent_now,
        'active_users_5min': active_users,
        'gemini_calls_today': {
            'total': gemini_today_total,
            'success': gemini_today_success,
            'failed': gemini_today_total - gemini_today_success,
            'by_function': {row['function_name']: row['count'] for row in gemini_by_function}
        },
        'gemini_calls_total': gemini_total,
        'gemini_daily_cap': gemini_daily_cap,
        'gemini_cap_remaining_today': max(0, gemini_daily_cap - gemini_today_total),
        'response_source_breakdown_today': {
            row['source']: row['count'] for row in source_breakdown
        },
        'rate_limited_requests_today': rate_limited_today,
        'troubleshooting_kb_size': kb_size,
        'learned_responses_count': learned_count,
        'total_sessions': session_count,
        'total_messages': message_count
    }
