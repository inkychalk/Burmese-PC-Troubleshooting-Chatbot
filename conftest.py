"""
Pytest configuration and fixtures for Burmese PC Chatbot tests
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path

# Add backend to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# app.py validates these at import time and models.py reads DATABASE_PATH
# into a module-level constant at import time, so both must be set before
# `from app import app` runs below.
os.environ.setdefault('SECRET_KEY', 'test_secret_key_for_pytest')
os.environ.setdefault('ADMIN_PASSWORD', 'test_password_12345')
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix='.db')
os.close(_test_db_fd)
os.environ['DATABASE_PATH'] = _test_db_path

from app import app as flask_app
import database.models as db_models
from database.models import init_db, seed_data, seed_admin_config

REPO_ROOT = os.path.dirname(__file__)
SEED_JSON_PATH = os.path.join(REPO_ROOT, 'troubleshooting_data.json')


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # database.models.DB_PATH is captured once at import time, so setting
    # DATABASE_PATH alone would not affect get_connection() after import.
    # Patch the module attribute directly so each test gets its own file.
    os.environ['DATABASE_PATH'] = db_path
    db_models.DB_PATH = db_path

    # Initialize database
    init_db()
    seed_data(json_path=SEED_JSON_PATH)
    seed_admin_config()

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(test_db):
    """Create a Flask test client with test database"""
    flask_app.config['TESTING'] = True
    flask_app.config['SESSION_TYPE'] = 'filesystem'

    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


@pytest.fixture
def auth_session(client):
    """Create an authenticated admin session"""
    # Set admin password for test
    os.environ['ADMIN_PASSWORD'] = 'test_password_12345'

    # Login
    response = client.post('/api/admin/login', json={'password': 'test_password_12345'})
    assert response.status_code == 200

    yield client


@pytest.fixture
def sample_messages():
    """Sample test data"""
    return {
        'english': 'computer not turning on',
        'burmese': 'ကွန်ပျူတာ ဖွင့်မရပါ',
        'mixed': 'ကွန်ပျူတာ computer problem',
        'cpu_hot': 'CPU is too hot',
        'invalid': '   ',
    }
