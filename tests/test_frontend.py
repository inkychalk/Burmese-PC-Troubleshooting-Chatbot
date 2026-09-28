"""
Tests for frontend HTML/CSS/JS assets
"""

import pytest
import os
from pathlib import Path


class TestFrontendAssets:
    """Tests for frontend asset files"""

    def test_index_html_exists(self):
        """Frontend index.html should exist"""
        index_path = Path('frontend/index.html')
        assert index_path.exists(), "frontend/index.html not found"

    def test_admin_html_exists(self):
        """Admin dashboard HTML should exist"""
        admin_path = Path('frontend/admin.html')
        assert admin_path.exists(), "frontend/admin.html not found"

    def test_style_css_exists(self):
        """CSS stylesheet should exist"""
        css_path = Path('frontend/css/style.css')
        assert css_path.exists(), "frontend/css/style.css not found"

    def test_admin_css_exists(self):
        """Admin CSS should exist"""
        admin_css_path = Path('frontend/css/admin.css')
        assert admin_css_path.exists(), "frontend/css/admin.css not found"

    def test_chat_js_exists(self):
        """Main chat JavaScript should exist"""
        js_path = Path('frontend/js/chat.js')
        assert js_path.exists(), "frontend/js/chat.js not found"

    def test_admin_js_exists(self):
        """Admin JavaScript should exist"""
        admin_js_path = Path('frontend/js/admin.js')
        assert admin_js_path.exists(), "frontend/js/admin.js not found"


class TestIndexHtml:
    """Tests for index.html content"""

    @pytest.fixture
    def index_content(self):
        """Load index.html content"""
        with open('frontend/index.html', 'r', encoding='utf-8') as f:
            return f.read()

    def test_index_has_doctype(self, index_content):
        """HTML should have DOCTYPE"""
        assert '<!doctype html>' in index_content.lower()

    def test_index_has_title(self, index_content):
        """HTML should have title tag"""
        assert '<title>' in index_content.lower()
        assert 'Our Store' in index_content

    def test_index_has_chat_window(self, index_content):
        """HTML should have chat window element"""
        assert 'chatWindow' in index_content or 'chat-window' in index_content

    def test_index_has_message_input(self, index_content):
        """HTML should have message input field"""
        assert 'messageInput' in index_content or 'message-input' in index_content or 'textarea' in index_content

    def test_index_has_send_button(self, index_content):
        """HTML should have send button"""
        assert 'sendBtn' in index_content or 'send-btn' in index_content or 'Send' in index_content

    def test_index_has_language_toggle(self, index_content):
        """HTML should have language toggle buttons"""
        assert 'lang' in index_content.lower() or 'language' in index_content.lower()

    def test_index_loads_stylesheet(self, index_content):
        """HTML should load CSS stylesheet"""
        assert 'style.css' in index_content or 'css' in index_content

    def test_index_loads_javascript(self, index_content):
        """HTML should load JavaScript files"""
        assert 'chat.js' in index_content or 'script' in index_content

    def test_index_has_viewport_meta(self, index_content):
        """HTML should have viewport meta tag for responsive design"""
        assert 'viewport' in index_content

    def test_index_is_valid_html_structure(self, index_content):
        """HTML should have proper structure"""
        assert '<html' in index_content.lower()
        assert '<head' in index_content.lower()
        assert '<body' in index_content.lower()
        assert '</html>' in index_content.lower()


class TestStyleCss:
    """Tests for CSS stylesheet"""

    @pytest.fixture
    def style_content(self):
        """Load style.css content"""
        with open('frontend/css/style.css', 'r', encoding='utf-8') as f:
            return f.read()

    def test_style_css_not_empty(self, style_content):
        """CSS should not be empty"""
        assert len(style_content) > 100

    def test_style_css_has_styling_rules(self, style_content):
        """CSS should contain styling rules"""
        assert '{' in style_content and '}' in style_content

    def test_style_css_has_color_definitions(self, style_content):
        """CSS should define colors"""
        assert 'color' in style_content.lower() or '#' in style_content or 'rgb' in style_content

    def test_style_css_references_fonts(self, style_content):
        """CSS should reference font imports or families"""
        assert 'font' in style_content.lower() or 'family' in style_content.lower()


class TestChatJs:
    """Tests for chat.js JavaScript file"""

    @pytest.fixture
    def chat_content(self):
        """Load chat.js content"""
        with open('frontend/js/chat.js', 'r', encoding='utf-8') as f:
            return f.read()

    def test_chat_js_not_empty(self, chat_content):
        """JavaScript should not be empty"""
        assert len(chat_content) > 100

    def test_chat_js_has_api_base_url(self, chat_content):
        """Should define API base URL"""
        assert 'API_BASE_URL' in chat_content or 'localhost:5000' in chat_content or '/api' in chat_content

    def test_chat_js_has_send_function(self, chat_content):
        """Should have function to send messages"""
        assert 'send' in chat_content.lower() or 'submit' in chat_content.lower()

    def test_chat_js_has_fetch_call(self, chat_content):
        """Should use fetch API"""
        assert 'fetch' in chat_content

    def test_chat_js_references_dom_elements(self, chat_content):
        """Should reference DOM elements"""
        assert 'getElementById' in chat_content or 'querySelector' in chat_content or 'document' in chat_content

    def test_chat_js_handles_language_toggle(self, chat_content):
        """Should handle language selection"""
        assert 'language' in chat_content.lower() or 'lang' in chat_content.lower()

    def test_chat_js_has_message_append(self, chat_content):
        """Should have function to append messages"""
        assert 'append' in chat_content.lower() or 'innerHTML' in chat_content or 'textContent' in chat_content


class TestFrontendIntegration:
    """Tests for frontend file integration"""

    def test_html_references_css(self):
        """index.html should reference CSS file"""
        with open('frontend/index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        assert 'style.css' in html or 'css' in html

    def test_html_references_js(self):
        """index.html should reference JavaScript file"""
        with open('frontend/index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        assert 'chat.js' in html or 'js' in html

    def test_css_file_readable(self):
        """CSS file should be readable"""
        try:
            with open('frontend/css/style.css', 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 0
        except Exception as e:
            pytest.fail(f"Cannot read CSS file: {e}")

    def test_js_file_readable(self):
        """JavaScript file should be readable"""
        try:
            with open('frontend/js/chat.js', 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 0
        except Exception as e:
            pytest.fail(f"Cannot read JavaScript file: {e}")
