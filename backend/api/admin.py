"""
Admin Dashboard API
Provides routes for authentication, metrics viewing, and configuration management
"""

import hmac
import os
import sys
from functools import wraps
from flask import Blueprint, request, jsonify, session

from database.models import (check_and_record_rate_limit, get_admin_config,
                             update_admin_config, get_metrics_snapshot)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Require ADMIN_PASSWORD to be set
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    print("❌ ERROR: ADMIN_PASSWORD environment variable must be set")
    sys.exit(1)


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') is not True:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['POST'])
def login():
    """Admin login endpoint"""
    data = request.get_json()

    if not data or 'password' not in data:
        return jsonify({'error': 'Password field is required'}), 400

    client_ip = request.remote_addr
    allowed, _ = check_and_record_rate_limit(client_ip, 'admin_login')
    if not allowed:
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429

    provided_password = data['password']

    if hmac.compare_digest(provided_password.encode(), ADMIN_PASSWORD.encode()):
        session['is_admin'] = True
        session.permanent = True
        return jsonify({'success': True, 'message': 'Logged in successfully'}), 200
    else:
        return jsonify({'error': 'Invalid password'}), 401


@admin_bp.route('/logout', methods=['POST'])
def logout():
    """Admin logout endpoint"""
    session.pop('is_admin', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200


@admin_bp.route('/metrics', methods=['GET'])
@admin_required
def metrics():
    """Get current metrics snapshot"""
    return jsonify(get_metrics_snapshot()), 200


@admin_bp.route('/config', methods=['GET'])
@admin_required
def get_config():
    """Get current admin configuration"""
    return jsonify(get_admin_config()), 200


@admin_bp.route('/config', methods=['POST'])
@admin_required
def set_config():
    """Update admin configuration"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    try:
        updated_config = update_admin_config(data)
        return jsonify(updated_config), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
