const API_BASE_URL = window.CHATBOT_API_URL || '';
const LOGIN_FORM = document.getElementById('loginForm');
const PASSWORD_INPUT = document.getElementById('passwordInput');
const LOGIN_ERROR = document.getElementById('loginError');
const LOGIN_SECTION = document.getElementById('loginSection');
const DASHBOARD_SECTION = document.getElementById('dashboardSection');
const LOGOUT_BTN = document.getElementById('logoutBtn');
const CONFIG_FORM = document.getElementById('configForm');

let metricsInterval = null;

async function login(e) {
  e.preventDefault();
  const password = PASSWORD_INPUT.value;

  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ password })
    });

    if (response.ok) {
      showDashboard();
      loadConfig();
      startMetricsPolling();
    } else {
      const data = await response.json();
      LOGIN_ERROR.textContent = data.error || 'Login failed';
      LOGIN_ERROR.style.display = 'block';
    }
  } catch (err) {
    LOGIN_ERROR.textContent = 'Unable to reach server';
    LOGIN_ERROR.style.display = 'block';
  }
}

async function logout() {
  await fetch(`${API_BASE_URL}/api/admin/logout`, {
    method: 'POST',
    credentials: 'same-origin'
  });

  showLogin();
  stopMetricsPolling();
}

function showLogin() {
  LOGIN_SECTION.style.display = 'flex';
  DASHBOARD_SECTION.style.display = 'none';
  PASSWORD_INPUT.value = '';
  LOGIN_ERROR.style.display = 'none';
}

function showDashboard() {
  LOGIN_SECTION.style.display = 'none';
  DASHBOARD_SECTION.style.display = 'block';
}

async function fetchMetrics() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/metrics`, {
      credentials: 'same-origin'
    });

    if (response.status === 401) {
      showLogin();
      return;
    }

    if (!response.ok) return;

    const metrics = await response.json();
    updateMetricsDisplay(metrics);
  } catch (err) {
    console.error('Failed to fetch metrics:', err);
  }
}

function updateMetricsDisplay(metrics) {
  document.getElementById('metricConcurrent').textContent = metrics.concurrent_requests_now;
  document.getElementById('metricActiveUsers').textContent = metrics.active_users_5min;

  const geminiToday = metrics.gemini_calls_today.total;
  document.getElementById('metricGeminiToday').textContent = geminiToday;
  document.getElementById('metricGeminiDetails').textContent =
    `✓ ${metrics.gemini_calls_today.success} · ✗ ${metrics.gemini_calls_today.failed}`;

  document.getElementById('metricCapRemaining').textContent = metrics.gemini_cap_remaining_today;
  const capPercent = Math.round((geminiToday / metrics.gemini_daily_cap) * 100);
  document.getElementById('metricCapPercent').textContent = `${capPercent}% of daily cap`;

  document.getElementById('metricRateLimited').textContent = metrics.rate_limited_requests_today;

  document.getElementById('metricKbSize').textContent = metrics.troubleshooting_kb_size;
  document.getElementById('metricKbDetail').textContent =
    `${metrics.learned_responses_count} learned + ${metrics.total_sessions} sessions`;

  const sourceBreakdown = metrics.response_source_breakdown_today;
  document.getElementById('sourceDb').textContent = sourceBreakdown.database || 0;
  document.getElementById('sourceCache').textContent = sourceBreakdown.cache || 0;
  document.getElementById('sourceGemini').textContent = sourceBreakdown.gemini || 0;
}

async function loadConfig() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/config`, {
      credentials: 'same-origin'
    });

    if (!response.ok) return;

    const config = await response.json();
    document.getElementById('rateLimitMinute').value = config.rate_limit_per_minute;
    document.getElementById('rateLimitDay').value = config.rate_limit_per_day;
    document.getElementById('geminiCap').value = config.gemini_daily_cap;
    document.getElementById('adminLoginLimit').value = config.admin_login_limit_per_minute;
    document.getElementById('activeWindowMinutes').value = config.active_session_window_minutes;
    document.getElementById('concurrentStale').value = config.concurrent_request_stale_seconds;
  } catch (err) {
    console.error('Failed to load config:', err);
  }
}

async function saveConfig(e) {
  e.preventDefault();

  const updates = {
    rate_limit_per_minute: parseInt(document.getElementById('rateLimitMinute').value),
    rate_limit_per_day: parseInt(document.getElementById('rateLimitDay').value),
    gemini_daily_cap: parseInt(document.getElementById('geminiCap').value),
    admin_login_limit_per_minute: parseInt(document.getElementById('adminLoginLimit').value),
    active_session_window_minutes: parseInt(document.getElementById('activeWindowMinutes').value),
    concurrent_request_stale_seconds: parseInt(document.getElementById('concurrentStale').value)
  };

  const statusEl = document.getElementById('configStatus');

  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(updates)
    });

    if (response.ok) {
      statusEl.textContent = '✓ Configuration saved successfully';
      statusEl.className = 'status-message success';
      statusEl.style.display = 'block';
      setTimeout(() => { statusEl.style.display = 'none'; }, 3000);
    } else {
      const data = await response.json();
      statusEl.textContent = `✗ ${data.error || 'Failed to save'}`;
      statusEl.className = 'status-message error';
      statusEl.style.display = 'block';
    }
  } catch (err) {
    statusEl.textContent = '✗ Unable to reach server';
    statusEl.className = 'status-message error';
    statusEl.style.display = 'block';
  }
}

function startMetricsPolling() {
  if (metricsInterval) return;
  fetchMetrics();
  metricsInterval = setInterval(() => {
    if (document.visibilityState === 'visible') {
      fetchMetrics();
    }
  }, 10000);
}

function stopMetricsPolling() {
  if (metricsInterval) {
    clearInterval(metricsInterval);
    metricsInterval = null;
  }
}

LOGIN_FORM.addEventListener('submit', login);
LOGOUT_BTN.addEventListener('click', logout);
CONFIG_FORM.addEventListener('submit', saveConfig);

showLogin();
