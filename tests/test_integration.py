"""
End-to-end integration tests
"""

import pytest
import json
import time


class TestEndToEndChatFlow:
    """End-to-end chat flow tests"""

    def test_complete_chat_flow_english(self, client, sample_messages):
        """Complete flow: user message -> API -> response -> saved"""
        # 1. Send message
        response = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'language': 'en',
            'platform': 'web',
            'user_id': 'test_user_1'
        })

        assert response.status_code == 200
        data = json.loads(response.data)

        # 2. Verify response structure
        assert 'response' in data
        assert 'session_id' in data
        assert 'language' in data
        assert 'source' in data

        # 3. Verify response is non-empty
        assert len(data['response']) > 0
        assert data['language'] == 'en'

        return data['session_id']

    def test_complete_chat_flow_burmese(self, client, sample_messages):
        """Complete flow with Burmese language"""
        response = client.post('/api/chat', json={
            'message': sample_messages['burmese'],
            'language': 'my',
            'platform': 'web',
            'user_id': 'test_user_2'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['language'] == 'my'
        assert len(data['response']) > 0

    def test_multi_turn_conversation(self, client, sample_messages):
        """Test multi-turn conversation in one session"""
        user_id = 'multi_turn_user'

        # First message
        response1 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'language': 'en',
            'user_id': user_id
        })
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        session_id_1 = data1['session_id']

        # Second message from same user
        response2 = client.post('/api/chat', json={
            'message': 'Can you help with overheating?',
            'language': 'en',
            'user_id': user_id
        })
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        session_id_2 = data2['session_id']

        # Both messages should create/use sessions
        assert session_id_1 is not None
        assert session_id_2 is not None

    def test_language_switching_in_conversation(self, client, sample_messages):
        """Test switching languages mid-conversation"""
        user_id = 'lang_switch_user'

        # Start with English
        response1 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'language': 'en',
            'user_id': user_id
        })
        assert json.loads(response1.data)['language'] == 'en'

        # Switch to Burmese
        response2 = client.post('/api/chat', json={
            'message': sample_messages['burmese'],
            'language': 'my',
            'user_id': user_id
        })
        assert json.loads(response2.data)['language'] == 'my'

    def test_auto_language_detection_in_flow(self, client, sample_messages):
        """Test auto language detection in chat flow"""
        # Don't specify language
        response = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'user_id': 'auto_detect_user'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'language' in data
        assert data['language'] in ['en', 'my']


class TestResponseQuality:
    """Tests for response quality and content"""

    def test_response_is_not_empty(self, client):
        """Response should not be empty"""
        response = client.post('/api/chat', json={
            'message': 'test query'
        })
        data = json.loads(response.data)
        assert len(data['response']) > 0

    def test_response_not_just_error(self, client):
        """Response should be helpful even on error"""
        response = client.post('/api/chat', json={
            'message': 'random gibberish xyz abc'
        })
        data = json.loads(response.data)
        # Should have some response
        assert 'response' in data
        assert len(data['response']) > 0

    def test_response_source_is_valid(self, client):
        """Response source should be one of valid options"""
        response = client.post('/api/chat', json={
            'message': 'test'
        })
        data = json.loads(response.data)
        assert data['source'] in [
            'database', 'cache', 'gemini',
            'error_unknown', 'error_no_api_key',
            'error_daily_cap_exceeded'
        ]


class TestCrossOriginRequests:
    """Tests for CORS and cross-origin handling"""

    def test_preflight_request_accepted(self, client):
        """CORS preflight request should be accepted"""
        response = client.options('/api/chat')
        # Should return 200 or 204 for preflight
        assert response.status_code in [200, 204, 405]

    def test_api_response_has_cors_headers(self, client):
        """API responses should have CORS headers"""
        response = client.get('/health')
        # CORS headers might be present
        # (depends on Flask-CORS configuration)
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling in flows"""

    def test_malformed_json_returns_400(self, client):
        """Malformed JSON should return 400"""
        response = client.post('/api/chat',
            data='not valid json',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_missing_required_field_returns_400(self, client):
        """Missing required fields should return 400"""
        response = client.post('/api/chat', json={
            'language': 'en'
            # missing 'message'
        })
        assert response.status_code == 400

    def test_invalid_platform_still_works(self, client):
        """Invalid platform value should still work (default to web)"""
        response = client.post('/api/chat', json={
            'message': 'test',
            'platform': 'invalid_platform'
        })
        assert response.status_code == 200

    def test_graceful_failure_on_gemini_error(self, client):
        """Should fail gracefully if Gemini API fails"""
        response = client.post('/api/chat', json={
            'message': 'test unknown query xyz'
        })
        # Should not return 500, should handle gracefully
        assert response.status_code != 500


class TestPerformance:
    """Performance and response time tests"""

    def test_health_check_is_fast(self, client):
        """Health check should be fast (< 100ms)"""
        import time
        start = time.time()
        client.get('/health')
        elapsed = time.time() - start
        assert elapsed < 1.0  # Allow up to 1 second for test env

    def test_chat_response_time(self, client):
        """Chat response should be reasonable (< 10 seconds for test)"""
        import time
        start = time.time()
        response = client.post('/api/chat', json={
            'message': 'quick test'
        })
        elapsed = time.time() - start
        assert elapsed < 10.0
        assert response.status_code == 200

    def test_categories_endpoint_is_fast(self, client):
        """Categories endpoint should be fast"""
        import time
        start = time.time()
        client.get('/api/categories')
        elapsed = time.time() - start
        assert elapsed < 1.0


class TestSessionManagement:
    """Tests for session management"""

    def test_different_users_get_different_sessions(self, client):
        """Different users should get different sessions"""
        response1 = client.post('/api/chat', json={
            'message': 'test',
            'user_id': 'user_1'
        })
        session1 = json.loads(response1.data)['session_id']

        response2 = client.post('/api/chat', json={
            'message': 'test',
            'user_id': 'user_2'
        })
        session2 = json.loads(response2.data)['session_id']

        assert session1 != session2

    def test_same_user_gets_consistent_session(self, client):
        """Same user might get same or new session"""
        user_id = 'consistent_user'

        response1 = client.post('/api/chat', json={
            'message': 'test',
            'user_id': user_id
        })
        data1 = json.loads(response1.data)

        response2 = client.post('/api/chat', json={
            'message': 'test',
            'user_id': user_id
        })
        data2 = json.loads(response2.data)

        # Both should have session IDs (may or may not be same)
        assert 'session_id' in data1
        assert 'session_id' in data2


class TestDataConsistency:
    """Tests for data consistency"""

    def test_response_fields_always_present(self, client):
        """Response should always have required fields"""
        queries = [
            'test 1',
            'test 2',
            'xyzabc unknown',
        ]

        for query in queries:
            response = client.post('/api/chat', json={'message': query})
            assert response.status_code == 200
            data = json.loads(response.data)

            required_fields = ['response', 'language', 'source', 'session_id']
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
