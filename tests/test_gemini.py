"""
Tests for the Gemini integration's off-topic rejection.

The chatbot must not use the LLM to answer questions unrelated to PC,
network, or software troubleshooting. Since the real Gemini API isn't
available in tests, the SDK client is mocked to simulate both an on-topic
and an OFF_TOPIC response from the model.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import integrations.gemini as gemini_module


def _mock_response(text):
    response = MagicMock()
    response.text = text
    return response


class TestOffTopicRejection:
    """Tests that non-troubleshooting questions are rejected, not answered"""

    def test_off_topic_query_is_rejected(self, test_db):
        """When Gemini signals a query is off-topic, the app must not
        surface it as a real answer"""
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('OFF_TOPIC')

            result = gemini_module.generate_troubleshooting_response('best playstation 5 deals', language='en')

            assert result['source'] == 'off_topic'
            assert result['category'] == 'Off-topic'
            assert 'computer' in result['solution'].lower() or 'pc' in result['solution'].lower()

    def test_off_topic_query_burmese_message(self, test_db):
        """Off-topic rejection message should be in Burmese when language='my'"""
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('OFF_TOPIC')

            result = gemini_module.generate_troubleshooting_response('ဒီနေ့ ထမင်းစားပြီးပြီလား', language='my')

            assert result['source'] == 'off_topic'
            assert 'ကွန်ပျူတာ' in result['solution']

    def test_on_topic_query_still_answered_normally(self, test_db):
        """A genuine troubleshooting question should still return a real
        answer with source='gemini', not be treated as off-topic"""
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response(
                '1. Check the power cable\n2. Try a different outlet'
            )

            result = gemini_module.generate_troubleshooting_response("computer won't turn on", language='en')

            assert result['source'] == 'gemini'
            assert result['category'] == 'AI Generated'
            assert 'power cable' in result['solution']

    def test_off_topic_response_not_cached(self, test_db):
        """An off-topic rejection must never be saved to learned_responses,
        since that would pollute the cache used for real troubleshooting
        answer reuse"""
        from database.models import get_connection

        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('OFF_TOPIC')
            with patch('app.gemini', gemini_module):
                import app as app_module
                app_module.app.config['TESTING'] = True
                with app_module.app.test_client() as client:
                    response = client.post('/api/chat', json={
                        'message': 'recommend a good pizza place for tonight',
                        'language': 'en',
                        'user_id': 'off_topic_test',
                    })
                    data = response.get_json()
                    assert data['source'] == 'off_topic'

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM learned_responses WHERE user_query = ?",
                    ('recommend a good pizza place for tonight',))
        count = cur.fetchone()['c']
        conn.close()
        assert count == 0


class TestIsConfigured:
    def test_not_configured_when_no_client(self, test_db):
        with patch.object(gemini_module, '_client', None):
            assert gemini_module.is_configured() is False

    def test_configured_when_client_present(self, test_db):
        with patch.object(gemini_module, '_client', MagicMock()):
            assert gemini_module.is_configured() is True


class TestNoApiKeyFallback:
    def test_generate_without_api_key_returns_error_source(self, test_db):
        with patch.object(gemini_module, '_client', None):
            result = gemini_module.generate_troubleshooting_response('computer wont boot', language='en')
            assert result['source'] == 'error_no_api_key'
            assert result['category'] == 'Unknown'

    def test_translate_without_api_key_returns_original_text(self, test_db):
        with patch.object(gemini_module, '_client', None):
            result = gemini_module.translate_text('hello world', target_language='my')
            assert result == 'hello world'


class TestDailyCapExceeded:
    def test_generate_respects_daily_cap(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            with patch.object(gemini_module, 'get_admin_config', return_value={'gemini_daily_cap': 0}):
                result = gemini_module.generate_troubleshooting_response('cpu overheating', language='en')
                assert result['source'] == 'error_daily_cap_exceeded'
                assert result['category'] == 'Cap Exceeded'
                mock_client.models.generate_content.assert_not_called()

    def test_translate_respects_daily_cap(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            with patch.object(gemini_module, 'get_admin_config', return_value={'gemini_daily_cap': 0}):
                result = gemini_module.translate_text('hello', target_language='my')
                assert result == 'hello'
                mock_client.models.generate_content.assert_not_called()


class TestDbLookupFailureFallsBackToZeroCount:
    def test_generate_continues_when_count_query_fails(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('1. Reboot your PC')
            with patch.object(gemini_module, 'get_connection', side_effect=Exception('db down')):
                result = gemini_module.generate_troubleshooting_response('pc wont start', language='en')
                assert result['source'] == 'gemini'


class TestGenerateContentException:
    def test_generate_content_error_returns_error_message(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.side_effect = Exception('api exploded')
            result = gemini_module.generate_troubleshooting_response('blue screen error', language='en')
            assert result['source'] == 'error_unknown'
            assert result['category'] == 'Error'

    def test_generate_content_error_burmese_message(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.side_effect = Exception('api exploded')
            result = gemini_module.generate_troubleshooting_response('blue screen error', language='my')
            assert 'အမှား' in result['solution']


class TestTranslateText:
    def test_translate_success_returns_translated_text(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('  မင်္ဂလာပါ  ')
            result = gemini_module.translate_text('hello', target_language='my')
            assert result == 'မင်္ဂလာပါ'

    def test_translate_unknown_language_code_still_calls_api(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.return_value = _mock_response('bonjour')
            result = gemini_module.translate_text('hello', target_language='fr')
            assert result == 'bonjour'

    def test_translate_exception_returns_original_text(self, test_db):
        with patch.object(gemini_module, '_client') as mock_client:
            mock_client.models.generate_content.side_effect = Exception('network error')
            result = gemini_module.translate_text('hello world', target_language='my')
            assert result == 'hello world'


class TestFallbackMessages:
    def test_no_api_message_burmese(self):
        assert 'AI' in gemini_module._fallback_no_api_message('my')

    def test_no_api_message_english(self):
        assert 'unavailable' in gemini_module._fallback_no_api_message('en')

    def test_cap_exceeded_message_english(self):
        assert 'limit' in gemini_module._fallback_cap_exceeded_message('en').lower()

    def test_cap_exceeded_message_burmese(self):
        assert gemini_module._fallback_cap_exceeded_message('my') != gemini_module._fallback_cap_exceeded_message('en')


class TestPlaceholderHooks:
    def test_text_to_speech_not_implemented(self):
        with pytest.raises(NotImplementedError):
            gemini_module.text_to_speech('hello')

    def test_speech_to_text_not_implemented(self):
        with pytest.raises(NotImplementedError):
            gemini_module.speech_to_text(b'audio-bytes')
