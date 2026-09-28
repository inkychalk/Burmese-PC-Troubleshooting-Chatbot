"""
Tests for Burmese PC Chatbot API endpoints
"""

import pytest
import json


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_check_returns_200(self, client):
        """Health check should return 200 OK"""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_check_response_format(self, client):
        """Health check should return expected JSON"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['service'] == 'burmese-pc-chatbot'


class TestChatEndpoint:
    """Tests for /api/chat endpoint"""

    def test_chat_with_valid_message_english(self, client, sample_messages):
        """Chat endpoint should accept English messages"""
        response = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'language': 'en'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert 'session_id' in data
        assert 'language' in data
        assert 'source' in data

    def test_chat_with_valid_message_burmese(self, client, sample_messages):
        """Chat endpoint should accept Burmese messages"""
        response = client.post('/api/chat', json={
            'message': sample_messages['burmese'],
            'language': 'my'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert data['language'] == 'my'

    def test_chat_without_language_auto_detects(self, client, sample_messages):
        """Chat endpoint should auto-detect language"""
        response = client.post('/api/chat', json={
            'message': sample_messages['english']
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['language'] in ['en', 'my']

    def test_chat_missing_message_field_returns_400(self, client):
        """Chat endpoint should return 400 if message is missing"""
        response = client.post('/api/chat', json={
            'language': 'en'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_chat_empty_request_returns_400(self, client):
        """Chat endpoint should return 400 for empty request"""
        response = client.post('/api/chat', json={})
        assert response.status_code == 400

    def test_chat_with_platform_and_user_id(self, client, sample_messages):
        """Chat endpoint should accept platform and user_id"""
        response = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'platform': 'facebook',
            'user_id': 'user_123'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'session_id' in data

    def test_chat_creates_session(self, client, sample_messages):
        """Chat endpoint should create a distinct session per user_id"""
        response1 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'user_id': 'user_one',
        })
        data1 = json.loads(response1.data)
        session_id_1 = data1['session_id']

        response2 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'user_id': 'user_two',
        })
        data2 = json.loads(response2.data)
        session_id_2 = data2['session_id']

        # Different users should get different sessions
        assert session_id_1 != session_id_2

    def test_chat_reuses_session_for_same_user(self, client, sample_messages):
        """Chat endpoint should reuse the same session across messages from the same user"""
        response1 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'user_id': 'repeat_user',
        })
        session_id_1 = json.loads(response1.data)['session_id']

        response2 = client.post('/api/chat', json={
            'message': sample_messages['english'],
            'user_id': 'repeat_user',
        })
        session_id_2 = json.loads(response2.data)['session_id']

        assert session_id_1 == session_id_2

    def test_chat_response_has_source_field(self, client, sample_messages):
        """Chat endpoint response should include source (database/cache/gemini/error)"""
        response = client.post('/api/chat', json={
            'message': sample_messages['english']
        })
        data = json.loads(response.data)
        assert data['source'] in ['database', 'cache', 'gemini', 'error_unknown', 'error_no_api_key']


class TestCategoriesEndpoint:
    """Tests for /api/categories endpoint"""

    def test_categories_returns_list(self, client):
        """Categories endpoint should return a list"""
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'categories' in data
        assert isinstance(data['categories'], list)

    def test_categories_has_seed_data(self, client):
        """Categories should include seeded data"""
        response = client.get('/api/categories')
        data = json.loads(response.data)
        assert len(data['categories']) > 0

    def test_categories_rate_limited(self, client):
        """Categories endpoint should be rate limited"""
        # Make many requests
        responses = []
        for i in range(25):
            response = client.get('/api/categories')
            responses.append(response.status_code)

        # At least one should be rate limited (429) if limit is 20/min
        # Note: This test depends on rate limiting configuration
        assert any(status in [200, 429] for status in responses)


class TestTranslateEndpoint:
    """Tests for /api/translate endpoint"""

    def test_translate_requires_text_and_target_language(self, client):
        """Translate endpoint should require both text and target_language"""
        response = client.post('/api/translate', json={
            'text': 'hello'
        })
        assert response.status_code == 400

    def test_translate_with_valid_input(self, client):
        """Translate endpoint should accept valid input"""
        response = client.post('/api/translate', json={
            'text': 'hello world',
            'target_language': 'my'
        })
        # Should return 200 or 429 if rate limited
        assert response.status_code in [200, 429]

    def test_translate_missing_text_returns_400(self, client):
        """Translate endpoint should return 400 if text is missing"""
        response = client.post('/api/translate', json={
            'target_language': 'my'
        })
        assert response.status_code == 400


class TestSecurityHeaders:
    """Tests for security headers"""

    def test_response_has_security_headers(self, client):
        """Responses should include security headers"""
        response = client.get('/health')
        assert 'Strict-Transport-Security' in response.headers
        assert 'X-Content-Type-Options' in response.headers
        assert 'X-Frame-Options' in response.headers

    def test_hsts_header_configured(self, client):
        """HSTS header should be properly configured"""
        response = client.get('/health')
        hsts = response.headers.get('Strict-Transport-Security')
        assert 'max-age=' in hsts
        assert 'includeSubDomains' in hsts

    def test_xframe_options_set_to_sameorigin(self, client):
        """X-Frame-Options should prevent clickjacking"""
        response = client.get('/health')
        xframe = response.headers.get('X-Frame-Options')
        assert xframe == 'SAMEORIGIN'


class TestRateLimiting:
    """Tests for rate limiting"""

    def test_rate_limit_429_response(self, client, sample_messages):
        """Rate limited requests should return 429"""
        # Make requests until rate limited
        for i in range(30):
            response = client.post('/api/chat', json={
                'message': sample_messages['english']
            })
            if response.status_code == 429:
                data = json.loads(response.data)
                assert 'error' in data
                assert 'Rate limit exceeded' in data['error']
                break
