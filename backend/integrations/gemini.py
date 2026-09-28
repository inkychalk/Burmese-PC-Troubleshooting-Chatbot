"""
Gemini AI Integration
Handles: LLM fallback for unmatched queries, Burmese translation,
text-to-speech (TTS) and speech-to-text (STT) hooks.

Uses the current `google-genai` SDK (the older `google-generativeai`
package is deprecated as of 2025).

Requires: GEMINI_API_KEY environment variable
"""

import os
import sqlite3
from datetime import datetime
from google import genai
from google.genai import types

from database.models import log_gemini_call, get_admin_config, get_connection

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

_client = None
if GEMINI_API_KEY:
    _client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = 'gemini-3.6-flash'  # Fast + cheap, good for chat


def is_configured():
    """Check if Gemini API key is set"""
    return _client is not None


def generate_troubleshooting_response(user_query, language='my'):
    """
    Ask Gemini to generate a PC troubleshooting response when
    the local knowledge base has no match.

    Returns: dict with 'solution' and 'category' (best guess)
    """
    if not is_configured():
        return {
            'solution': _fallback_no_api_message(language),
            'category': 'Unknown',
            'source': 'error_no_api_key'
        }

    config = get_admin_config()
    today = datetime.utcnow().date().isoformat()

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as count FROM gemini_call_log WHERE DATE(timestamp) = ? AND success = 1',
            (today,)
        )
        today_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        today_count = 0

    daily_cap = config.get('gemini_daily_cap', 300)
    if today_count >= daily_cap:
        log_gemini_call('generate_troubleshooting_response', False, 'daily_cap_exceeded')
        return {
            'solution': _fallback_cap_exceeded_message(language),
            'category': 'Cap Exceeded',
            'source': 'error_daily_cap_exceeded'
        }

    system_prompt = f"""You are a PC troubleshooting assistant for a computer repair store.
You only answer questions about computer/PC hardware, software, operating systems,
networking, or peripheral (printer, monitor, etc.) troubleshooting.

If the customer's message is NOT a computer/PC/network/software troubleshooting
question (e.g. general chit-chat, unrelated topics, requests unrelated to fixing
a computer problem), respond with EXACTLY this token and nothing else: OFF_TOPIC

Otherwise, provide a clear, step-by-step solution.
Respond in {'Burmese (Myanmar language)' if language == 'my' else 'English'}.
Keep the response practical and focused on hardware, software, network, or installation troubleshooting.
Format as numbered steps."""

    try:
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        log_gemini_call('generate_troubleshooting_response', True)

        response_text = (response.text or '').strip()
        if response_text == 'OFF_TOPIC':
            return {
                'solution': _fallback_off_topic_message(language),
                'category': 'Off-topic',
                'source': 'off_topic'
            }

        return {
            'solution': response_text,
            'category': 'AI Generated',
            'source': 'gemini'
        }
    except Exception as e:
        import logging
        logging.error(f"Gemini API error in generate_troubleshooting_response: {str(e)}")
        log_gemini_call('generate_troubleshooting_response', False, str(e))
        return {
            'solution': _fallback_error_message(language),
            'category': 'Error',
            'source': 'error_unknown'
        }


def translate_text(text, target_language='en'):
    """
    Translate text using Gemini (Burmese <-> English <-> others)
    """
    if not is_configured():
        return text

    lang_names = {'en': 'English', 'my': 'Burmese (Myanmar)', 'th': 'Thai'}
    target_name = lang_names.get(target_language, target_language)

    config = get_admin_config()
    today = datetime.utcnow().date().isoformat()

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as count FROM gemini_call_log WHERE DATE(timestamp) = ? AND success = 1',
            (today,)
        )
        today_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        today_count = 0

    daily_cap = config.get('gemini_daily_cap', 300)
    if today_count >= daily_cap:
        log_gemini_call('translate_text', False, 'daily_cap_exceeded')
        return text

    try:
        prompt = f"Translate the following text to {target_name}. Only output the translation, nothing else:\n\n{text}"
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        log_gemini_call('translate_text', True)
        return response.text.strip()
    except Exception as e:
        log_gemini_call('translate_text', False, str(e))
        return text


def _fallback_no_api_message(language):
    if language == 'my':
        return "ဆောရီးပါ၊ ယခုအချိန်တွင် AI လုပ်ဆောင်ချက် ပိတ်ထားပါသည်။ ကျေးဇူးပြု၍ ကျွန်ုပ်တို့ဆိုင်သို့ ဆက်သွယ်ပါ။"
    return "Sorry, AI assistance is currently unavailable. Please contact our store directly."


def _fallback_error_message(language):
    if language == 'my':
        return "အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည်။ ကျေးဇူးပြု၍ ထပ်မံကြိုးစားပါ။"
    return "An error occurred. Please try again."


def _fallback_off_topic_message(language):
    if language == 'my':
        return "ဆောရီးပါ၊ ကျွန်ုပ်တို့သည် ကွန်ပျူတာ/PC၊ ကွန်ရက်နှင့် software ပြဿနာများကိုသာ ကူညီဖြေရှင်းပေးနိုင်ပါသည်။ ကွန်ပျူတာဆိုင်ရာ ပြဿနာတစ်ခုအား မေးမြန်းပေးပါ။"
    return "Sorry, I can only help with computer/PC, network, and software troubleshooting questions. Please ask about a computer-related problem."


def _fallback_cap_exceeded_message(language):
    if language == 'my':
        return "ယနေ့ AI အကူအညီ အပိုင်းအခြား မကြေးမီ ရှိပြီးဖြစ်ပါသည်။ ကျေးဇူးပြု၍ အခြား အကူအညီ ရှာဖွေပါ သို့မဟုတ် နက်သည် ထပ်မံကြိုးစားပါ။"
    return "Daily AI assistance limit has been reached. Please try again later."


# --- Placeholder hooks for TTS/STT (to be expanded) ---

def text_to_speech(text, language='my'):
    """
    Placeholder for Gemini TTS integration.
    Note: Requires a Gemini audio-output-capable model (e.g. a TTS-specific
    model) or a dedicated TTS API for production use.
    """
    raise NotImplementedError("TTS integration pending - requires Gemini audio model setup")


def speech_to_text(audio_data, language='my'):
    """
    Placeholder for Gemini STT integration.
    """
    raise NotImplementedError("STT integration pending - requires Gemini audio model setup")
