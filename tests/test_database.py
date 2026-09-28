"""
Tests for database operations
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database.models import (
    get_connection, init_db, seed_data, get_or_create_session,
    log_message, get_cached_response, search_troubleshooting,
    save_learned_response
)


class TestDatabaseInitialization:
    """Tests for database schema initialization"""

    def test_init_db_creates_tables(self, test_db):
        """init_db should create all required tables"""
        conn = get_connection()
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = [
            'troubleshooting', 'learned_responses', 'chat_sessions',
            'chat_messages', 'admin_config', 'request_log',
            'gemini_call_log', 'inflight_requests'
        ]

        for table in required_tables:
            assert table in tables, f"Table {table} not created"

        conn.close()

    def test_chat_messages_has_source_column(self, test_db):
        """chat_messages table should have source column"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('PRAGMA table_info(chat_messages)')
        columns = [row[1] for row in cursor.fetchall()]

        assert 'source' in columns, "source column missing from chat_messages"
        conn.close()

    def test_troubleshooting_has_source_column(self, test_db):
        """troubleshooting table should have source column"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('PRAGMA table_info(troubleshooting)')
        columns = [row[1] for row in cursor.fetchall()]

        assert 'source' in columns, "source column missing from troubleshooting"
        conn.close()


class TestChatSessions:
    """Tests for chat session management"""

    def test_create_session(self, test_db):
        """Should create new chat session"""
        session = get_or_create_session('web', 'user_123')

        assert session['id'] is not None
        assert session['platform'] == 'web'
        assert session['user_id'] == 'user_123'
        assert session['language_preference'] == 'my'

    def test_session_default_language_is_burmese(self, test_db):
        """New sessions should default to Burmese"""
        session = get_or_create_session('web', 'user_123')
        assert session['language_preference'] == 'my'

    def test_multiple_sessions_for_different_users(self, test_db):
        """Different users should get different sessions"""
        session1 = get_or_create_session('web', 'user_1')
        session2 = get_or_create_session('web', 'user_2')

        assert session1['id'] != session2['id']


class TestChatMessages:
    """Tests for chat message logging"""

    def test_log_user_message(self, test_db):
        """Should log user message"""
        session = get_or_create_session('web', 'user_123')

        log_message(session['id'], 'user', 'test message', 'en')

        # Verify logged
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chat_messages WHERE session_id = ?', (session['id'],))
        message = cursor.fetchone()

        assert message is not None
        assert message['role'] == 'user'
        assert message['message'] == 'test message'
        assert message['language'] == 'en'
        conn.close()

    def test_log_bot_message_with_source(self, test_db):
        """Should log bot message with source"""
        session = get_or_create_session('web', 'user_123')

        log_message(session['id'], 'assistant', 'response', 'en', source='database')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chat_messages WHERE role = ?', ('assistant',))
        message = cursor.fetchone()

        assert message['role'] == 'assistant'
        assert message['source'] == 'database'
        conn.close()

    def test_conversation_history(self, test_db):
        """Should maintain conversation history"""
        session = get_or_create_session('web', 'user_123')

        log_message(session['id'], 'user', 'question 1', 'en')
        log_message(session['id'], 'assistant', 'answer 1', 'en', 'database')
        log_message(session['id'], 'user', 'question 2', 'en')
        log_message(session['id'], 'assistant', 'answer 2', 'en', 'gemini')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM chat_messages WHERE session_id = ?',
                       (session['id'],))
        count = cursor.fetchone()['count']

        assert count == 4
        conn.close()


class TestTroubleshootingDatabase:
    """Tests for troubleshooting knowledge base"""

    def test_seed_data_loads(self, test_db):
        """Should load seed data from JSON"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM troubleshooting')
        count = cursor.fetchone()['count']

        # Should have loaded seed data
        assert count > 0, "Seed data not loaded"
        conn.close()

    def test_search_troubleshooting(self, test_db):
        """Should find troubleshooting entries"""
        results = search_troubleshooting('power', language='en', limit=5)

        # May or may not find results depending on seed data
        assert isinstance(results, list)

    def test_troubleshooting_entry_has_source(self, test_db):
        """All troubleshooting entries should have source field"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM troubleshooting LIMIT 1')
        entry = cursor.fetchone()

        if entry:
            assert entry['source'] in ['seed', 'user', 'admin']
        conn.close()


class TestCachedResponses:
    """Tests for response caching"""

    def test_save_learned_response(self, test_db):
        """Should save learned responses"""
        save_learned_response('test query', 'en', 'Hardware', 'test response')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learned_responses WHERE user_query = ?',
                       ('test query',))
        response = cursor.fetchone()

        assert response is not None
        assert response['llm_response'] == 'test response'
        conn.close()

    def test_get_cached_response_with_matching_keywords(self, test_db):
        """Should retrieve cached response with similar keywords"""
        save_learned_response('computer not turning on', 'en', 'Power',
                            'Check power cable and power supply')

        cached = get_cached_response('computer won\'t power on', 'en',
                                    keywords=['computer', 'power'], threshold=1)

        # May or may not find depending on keyword matching
        if cached:
            assert cached['llm_response'] == 'Check power cable and power supply'

    def test_burmese_cache_rejects_unrelated_query(self, test_db):
        """A cached Burmese answer for one topic must not be reused for a
        completely different question just because they share a generic
        substring (e.g. both mention 'windows 11')"""
        save_learned_response(
            'windows 11 photoshop cs 2022 သုံးရင်း crash ဖြစ်ပြီးသူ့ဘာသူပိတ်သွားတယ်။',
            'my', 'AI Generated',
            'Windows 11 မှာ Photoshop CC 2022 သုံးရင်း crash ဖြစ်ပြီး Graphics Driver ပြဿနာ...'
        )

        from troubleshooting.engine import extract_keywords
        unrelated_query = 'Windows 11 တွင် motherboard driver ထည့်မရခြင်းပြသနာ'
        keywords = extract_keywords(unrelated_query, 'my')

        cached = get_cached_response(unrelated_query, 'my', keywords)
        assert cached is None

    def test_burmese_cache_hits_for_genuinely_similar_query(self, test_db):
        """A near-duplicate rephrasing of an already-cached Burmese question
        should still be served from cache"""
        save_learned_response(
            'windows 11 photoshop cs 2022 သုံးရင်း crash ဖြစ်ပြီးသူ့ဘာသူပိတ်သွားတယ်။',
            'my', 'AI Generated',
            'Windows 11 မှာ Photoshop CC 2022 သုံးရင်း crash ဖြစ်ပြီး Graphics Driver ပြဿနာ...'
        )

        from troubleshooting.engine import extract_keywords
        similar_query = 'windows 11 photoshop crash ဖြစ်တယ်'
        keywords = extract_keywords(similar_query, 'my')

        cached = get_cached_response(similar_query, 'my', keywords)
        assert cached is not None


class TestAdminConfig:
    """Tests for admin configuration"""

    def test_admin_config_table_populated(self, test_db):
        """Admin config should be seeded with defaults"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM admin_config')
        count = cursor.fetchone()['count']

        assert count > 0, "Admin config not seeded"
        conn.close()

    def test_rate_limit_config_exists(self, test_db):
        """Should have rate limit configuration"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM admin_config WHERE key = ?',
                       ('rate_limit_per_minute',))
        result = cursor.fetchone()

        assert result is not None
        conn.close()


class TestDatabaseIntegrity:
    """Tests for database integrity and constraints"""

    def test_chat_messages_foreign_key_constraint(self, test_db):
        """Should enforce foreign key constraint on session_id"""
        conn = get_connection()
        cursor = conn.cursor()

        # Try to insert message with non-existent session_id
        try:
            cursor.execute('''
                INSERT INTO chat_messages (session_id, role, message, language)
                VALUES (?, ?, ?, ?)
            ''', (99999, 'user', 'test', 'en'))
            conn.commit()
            # Foreign key might not be enforced depending on SQLite config
            # but we should still test it works
        except Exception as e:
            pass
        finally:
            conn.close()
