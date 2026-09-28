"""
Tests for the Admin Dashboard API (backend/api/admin.py)
"""

import json


class TestAdminLogin:
    """Tests for /api/admin/login"""

    def test_login_missing_password_returns_400(self, client):
        response = client.post('/api/admin/login', json={})
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_login_wrong_password_returns_401(self, client):
        response = client.post('/api/admin/login', json={'password': 'wrong'})
        assert response.status_code == 401
        assert 'error' in response.get_json()

    def test_login_correct_password_returns_200(self, client):
        response = client.post('/api/admin/login', json={'password': 'test_password_12345'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_login_sets_admin_session(self, client):
        client.post('/api/admin/login', json={'password': 'test_password_12345'})
        with client.session_transaction() as sess:
            assert sess.get('is_admin') is True


class TestAdminLogout:
    """Tests for /api/admin/logout"""

    def test_logout_returns_200(self, client):
        response = client.post('/api/admin/logout')
        assert response.status_code == 200
        assert response.get_json()['success'] is True

    def test_logout_clears_admin_session(self, auth_session):
        auth_session.post('/api/admin/logout')
        with auth_session.session_transaction() as sess:
            assert sess.get('is_admin') is None


class TestAdminAuthRequired:
    """Tests that protected admin routes reject unauthenticated requests"""

    def test_metrics_requires_auth(self, client):
        response = client.get('/api/admin/metrics')
        assert response.status_code == 401

    def test_get_config_requires_auth(self, client):
        response = client.get('/api/admin/config')
        assert response.status_code == 401

    def test_set_config_requires_auth(self, client):
        response = client.post('/api/admin/config', json={'rate_limit_per_minute': 30})
        assert response.status_code == 401


class TestAdminMetrics:
    """Tests for /api/admin/metrics"""

    def test_metrics_returns_snapshot(self, auth_session):
        response = auth_session.get('/api/admin/metrics')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestAdminConfig:
    """Tests for /api/admin/config"""

    def test_get_config_returns_dict(self, auth_session):
        response = auth_session.get('/api/admin/config')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'rate_limit_per_minute' in data

    def test_set_config_missing_body_returns_400(self, auth_session):
        response = auth_session.post('/api/admin/config', data='', content_type='application/json')
        assert response.status_code == 400

    def test_set_config_updates_value(self, auth_session):
        response = auth_session.post('/api/admin/config', json={'rate_limit_per_minute': 42})
        assert response.status_code == 200
        data = response.get_json()
        assert data['rate_limit_per_minute'] == 42

    def test_set_config_unknown_key_returns_400(self, auth_session):
        response = auth_session.post('/api/admin/config', json={'not_a_real_key': 1})
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_set_config_invalid_value_returns_400(self, auth_session):
        response = auth_session.post('/api/admin/config', json={'rate_limit_per_minute': -5})
        assert response.status_code == 400
        assert 'error' in response.get_json()
