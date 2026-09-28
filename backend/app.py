"""
Burmese PC Troubleshooting Chatbot - Main Flask Application
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import sys

from database.models import (init_db, seed_data, seed_admin_config, get_or_create_session, log_message,
                             save_learned_response, get_cached_response, check_and_record_rate_limit,
                             log_inflight_start, log_inflight_end)
from troubleshooting.engine import process_query, format_response, detect_language, extract_keywords
from integrations import gemini

app = Flask(__name__)

# Validate required environment variables
required_env_vars = ['SECRET_KEY', 'ADMIN_PASSWORD']
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these in your .env file or environment")
    sys.exit(1)

# Configure security
app.secret_key = os.environ.get('SECRET_KEY')

# CORS: restrict to known origins
allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost,http://127.0.0.1').split(',')
CORS(app, origins=allowed_origins, allow_headers=['Content-Type'], methods=['GET', 'POST', 'OPTIONS'])

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for Docker/monitoring"""
    return jsonify({'status': 'ok', 'service': 'burmese-pc-chatbot'})


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint.

    Request body:
    {
        "message": "Computer won't turn on",
        "language": "en" | "my" (optional, auto-detected),
        "platform": "web" | "facebook" | "tiktok" | "line" | "viber" (optional, default 'web'),
        "user_id": "unique_user_identifier" (optional)
    }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'Message field is required'}), 400

    client_ip = request.remote_addr
    user_message = data['message']
    language = data.get('language')
    platform = data.get('platform', 'web')
    user_id = data.get('user_id', 'anonymous')

    allowed, info = check_and_record_rate_limit(client_ip, 'chat', user_id=user_id)
    if not allowed:
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'error_my': 'တောင်းဆိုမှု အရေအတွက် ကန့်သတ်ချက်ကို ကျော်လွန်နေပါသည်။ ခဏနေမှ ထပ်ကြိုးစားပါ။',
            'limit_type': info['limit_type']
        }), 429

    if language is None:
        language = detect_language(user_message)

    inflight_id = log_inflight_start('chat')
    try:
        session = get_or_create_session(platform, user_id)
        log_message(session['id'], 'user', user_message, language)

        result = process_query(user_message, language=language)

        if result['found']:
            response_text = format_response(result)
            source = 'database'
        else:
            keywords = extract_keywords(user_message, language)
            cached = get_cached_response(user_message, language, keywords)

            if cached:
                response_text = cached['llm_response']
                source = 'cache'
            else:
                llm_result = gemini.generate_troubleshooting_response(user_message, language=language)
                response_text = llm_result['solution']
                source = llm_result['source']

                if source == 'gemini':
                    save_learned_response(user_message, language, llm_result.get('category', 'Unknown'), response_text)

        log_message(session['id'], 'assistant', response_text, language, source=source)

        return jsonify({
            'response': response_text,
            'language': language,
            'source': source,
            'session_id': session['id']
        })
    finally:
        log_inflight_end(inflight_id)


@app.route('/api/translate', methods=['POST'])
def translate():
    """
    Translation endpoint.

    Request body:
    {
        "text": "Hello world",
        "target_language": "my" | "en" | "th"
    }
    """
    data = request.get_json()

    if not data or 'text' not in data or 'target_language' not in data:
        return jsonify({'error': 'text and target_language are required'}), 400

    client_ip = request.remote_addr
    allowed, info = check_and_record_rate_limit(client_ip, 'translate')
    if not allowed:
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'error_my': 'တောင်းဆိုမှု အရေအတွက် ကန့်သတ်ချက်ကို ကျော်လွန်နေပါသည်။',
            'limit_type': info['limit_type']
        }), 429

    inflight_id = log_inflight_start('translate')
    try:
        translated = gemini.translate_text(data['text'], data['target_language'])
        return jsonify({'translated_text': translated})
    finally:
        log_inflight_end(inflight_id)


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Return list of available troubleshooting categories"""
    client_ip = request.remote_addr
    allowed, info = check_and_record_rate_limit(client_ip, 'categories')
    if not allowed:
        return jsonify({'error': 'Rate limit exceeded'}), 429

    from database.models import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM troubleshooting ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return jsonify({'categories': categories})


def initialize_app():
    """Run database initialization and seeding on startup"""
    init_db()
    seed_data()
    seed_admin_config()


from api.admin import admin_bp
app.register_blueprint(admin_bp)

initialize_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
