# Security Policy - Burmese PC Troubleshooting Chatbot

This document outlines the security architecture and controls implemented in the Burmese PC Troubleshooting Chatbot, following OWASP Top 10 guidelines.

## Threat Model

### Protected Assets
- User session data and conversation history
- Admin authentication credentials
- API keys and secrets
- Application source code and configuration
- Database integrity

### Identified Threats

| Threat | Severity | Mitigation |
|--------|----------|-----------|
| SQL Injection | HIGH | Parameterized queries, ORM usage |
| Cross-Site Scripting (XSS) | HIGH | HTML escaping, CSP headers |
| Cross-Site Request Forgery (CSRF) | MEDIUM | Session-based auth |
| Weak Authentication | CRITICAL | Enforce strong secrets |
| API Rate Limiting Bypass | MEDIUM | Token-based rate limiting |
| Man-in-the-Middle (MITM) | HIGH | HTTPS enforcement, HSTS |
| Information Disclosure | MEDIUM | Error message sanitization |
| Insecure Deserialization | LOW | JSON-only parsing |

## Security Controls Implemented

### Authentication & Authorization

#### Admin Authentication
```python
# ADMIN_PASSWORD is REQUIRED (enforced at startup)
# Use: openssl rand -base64 32 (or python -c "import secrets; print(secrets.token_base64(32))")
# Rate Limited: 5 attempts per minute per IP
# Session-based: Flask secure sessions
```

**Requirements:**
- ADMIN_PASSWORD must be set (fails to start if not)
- Strong password (minimum 32 characters recommended)
- HTTPS in production (enforce with HSTS header)
- Session timeout: 30 minutes inactivity
- Secure cookie: HttpOnly, Secure (production), SameSite=Strict

#### User Sessions
- No authentication required for chat (public API)
- Session tracking for analytics and conversation context
- User ID can be anonymous or provided by client

### API Security

#### Rate Limiting
```
Chat endpoint: 20 requests per minute (per IP)
Chat endpoint: 500 requests per day (per user/IP)
Admin login: 5 attempts per minute
Translate: 20 requests per minute
Categories: 20 requests per minute
```

**Implementation:**
- Sliding window rate limiting
- Tracks by IP address and user ID
- Returns HTTP 429 on limit exceeded
- Headers included: `Retry-After`, error messages in Burmese and English

#### CORS Security
```python
# Only allow specified origins (configured in .env)
ALLOWED_ORIGINS=http://localhost,https://yourdomain.com
```

**Restrictions:**
- Specific origins only (not wildcard)
- Allowed methods: GET, POST, OPTIONS
- Allowed headers: Content-Type
- No credentials by default

#### Input Validation
- Message length validation (max 1000 characters)
- Language parameter validation (enum: 'en', 'my')
- Platform parameter validation (enum: 'web', 'facebook', etc.)
- User ID format validation

### Data Protection

#### Encryption in Transit
- **HTTPS Required** in production (enforced via HSTS header)
- TLS 1.2+ only
- Certificate pinning recommended

#### Encryption at Rest
- Database: SQLite with WAL mode (Write-Ahead Logging)
- No sensitive data stored unencrypted in database
- Chat messages are plain text (acceptable for public troubleshooting)
- API keys stored in environment variables, not in code

#### Data Retention
- Chat messages: 90 days (configurable)
- Session data: 30 days (configurable)
- Request logs: 30 days (for rate limiting)
- Gemini API logs: 90 days

### API Key Management

#### GEMINI_API_KEY Security
```
# REQUIRED but can be empty (falls back to local KB)
# Store in: .env file (NEVER commit to git)
# Rotate: Every 90 days recommended
# Monitor: Check Google Cloud console for unusual activity
```

**Best Practices:**
- Use environment variables, never hardcode
- Rotate keys regularly
- Monitor API quota usage
- Use IP whitelisting if possible
- Create dedicated service accounts for API keys

### Secret Key Management

#### Flask SECRET_KEY
```
# REQUIRED - Application won't start without it
# Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
# Rotate: On each deployment to new environment
# Length: Minimum 32 characters (64+ recommended)
```

**Requirements:**
- Must be cryptographically random
- Different for dev/staging/production
- Never committed to version control
- Rotated when compromised or quarterly

## Security Headers

All HTTP responses include the following security headers:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com
```

### Header Purposes
| Header | Purpose | Value |
|--------|---------|-------|
| HSTS | Force HTTPS | 1 year, subdomains |
| X-Content-Type-Options | Prevent MIME sniffing | nosniff |
| X-Frame-Options | Prevent clickjacking | SAMEORIGIN |
| X-XSS-Protection | Browser XSS protection | enabled |
| CSP | Restrict resource loading | restrictive policy |

## Vulnerability Management

### Known Vulnerabilities
**None currently identified** (as of Sept 17, 2026)

### Dependency Management
```bash
# Check for vulnerabilities
pip install -U pip
pip install safety
safety check -r backend/requirements.txt

# Update dependencies
pip install --upgrade -r backend/requirements.txt
```

### Security Audit Recommendations
- Run `safety check` before each deployment
- Review dependencies periodically for known CVEs
- Consider an OWASP ZAP scan before major releases

## Incident Response Plan

### Incident Classification

| Severity | Response Time | Example |
|----------|---------------|---------|
| CRITICAL | Immediate | API key compromised, data breach |
| HIGH | 1 hour | Authentication bypass, code injection |
| MEDIUM | 24 hours | XSS vulnerability, weak encryption |
| LOW | 1 week | Information disclosure, missing header |

### Response Steps

1. **Identify:** Confirm the security incident
2. **Contain:** Stop further damage (disable service if necessary)
3. **Analyze:** Determine scope and impact
4. **Eradicate:** Remove the vulnerability
5. **Recover:** Restore service safely
6. **Post-Mortem:** Review and document lessons learned

## Deployment Security

### Production Checklist

Before deploying to production:

```markdown
- [ ] Generate new SECRET_KEY (python3 -c "import secrets; print(secrets.token_hex(32))")
- [ ] Generate new ADMIN_PASSWORD (openssl rand -base64 32)
- [ ] Update ALLOWED_ORIGINS for your domain
- [ ] Set FLASK_ENV=production
- [ ] Verify GEMINI_API_KEY is set
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure database backups (daily)
- [ ] Set up monitoring and alerts
- [ ] Review and rotate all secrets
- [ ] Run security tests: pytest tests/ --cov
- [ ] Run dependency audit: safety check
- [ ] Enable WAF (Web Application Firewall) if available
- [ ] Configure CDN with HTTPS
- [ ] Set up rate limiting in nginx
- [ ] Enable logging and monitoring
- [ ] Test disaster recovery plan
```

### Environment Variables Checklist

```bash
# REQUIRED - Application won't start without these
GEMINI_API_KEY=your_key_here
ADMIN_PASSWORD=your_strong_password_here
SECRET_KEY=your_random_secret_key_here

# RECOMMENDED
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_PATH=/data/db.sqlite
FLASK_ENV=production
```

### Docker Security

**Security Best Practices:**
- Use specific Python version (3.11) not 'latest'
- Run as non-root user (implement in Dockerfile)
- Scan images: `docker scan burmese-pc_chatbot-backend`
- Use secrets management for sensitive data
- Implement resource limits
- Keep base images updated

## Compliance & Standards

### OWASP Top 10 Coverage

| OWASP Risk | Status | Mitigation |
|-----------|--------|-----------|
| A01:2021 - Broken Access Control | Protected | Rate limiting, CORS, auth |
| A02:2021 - Cryptographic Failures | Protected | HTTPS, HSTS, secrets in env |
| A03:2021 - Injection | Protected | Parameterized queries, input validation |
| A04:2021 - Insecure Design | Protected | Security-first architecture |
| A05:2021 - Security Misconfiguration | Protected | Secure defaults, validation |
| A06:2021 - Vulnerable Components | Monitored | Dependency audits, safety checks |
| A07:2021 - Authentication Failures | Protected | Strong auth, rate limiting |
| A08:2021 - Software & Data Integrity | Protected | Dependency verification |
| A09:2021 - Logging & Monitoring | Monitored | Structured logging, alerts |
| A10:2021 - SSRF | Protected | Input validation, no arbitrary URLs |

## Security Testing

### Automated Testing

```bash
# Run all security tests
pytest tests/ -v --cov=backend

# Run specific security tests
pytest tests/test_api.py::TestSecurityHeaders -v
pytest tests/ -k "security" -v

# Code quality
flake8 backend/
black --check backend/

# Dependency audit
safety check -r backend/requirements.txt
```

### Manual Testing

**OWASP Testing Guide Implementation:**
- [ ] SQL Injection testing
- [ ] XSS testing
- [ ] CSRF testing
- [ ] Authentication bypass testing
- [ ] Authorization bypass testing
- [ ] Session management testing
- [ ] Input validation testing
- [ ] Cryptography testing

### Penetration Testing

**Recommended Services:**
- OWASP ZAP (free, open-source)
- Burp Suite (professional)
- Qualys SSL Labs (free for HTTPS)

```bash
# OWASP ZAP scan
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost
```

## Monitoring & Logging

### Security Events to Log

```
- All admin login attempts (success/failure)
- Rate limit violations
- API errors and exceptions
- Database query errors
- Failed input validation
- Unusual patterns or suspicious activity
```

### Log Locations

```
- Application logs: stdout/stderr
- Request logs: nginx access log
- Error logs: Flask error logger
- Database logs: sqlite3 WAL
```

### Monitoring Recommendations

**Alerts to Set Up:**
- Multiple failed login attempts (>5 in 5 min)
- High rate limit violations
- API errors/5xx responses
- Unusual response times
- Database connection failures
- Disk space issues
- Memory usage spikes

## Reporting Security Issues

### Responsible Disclosure

This is a small customer-support chatbot rather than a project with a
dedicated security team. If you find a vulnerability, please open a GitHub
issue or contact the maintainer directly rather than disclosing it publicly.

## Security Resources

### References
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org/)

### Tools
- OWASP ZAP: Free web application security scanner
- Burp Suite: Professional security testing
- npm audit / pip audit: Dependency vulnerability scanning
- Snyk: Continuous vulnerability monitoring

## Change Log

Initial security hardening pass added:
- CORS restrictions
- Security headers
- Required secrets (app refuses to start without SECRET_KEY/ADMIN_PASSWORD)
- Rate limiting on all endpoints
- Sanitized error messages

## Appendix: Quick Security Checklist

### Pre-Deployment
- [ ] All environment variables set (SECRET_KEY, ADMIN_PASSWORD, GEMINI_API_KEY)
- [ ] ALLOWED_ORIGINS configured for your domain
- [ ] SSL/HTTPS certificate installed
- [ ] Database backups configured
- [ ] Monitoring and alerts enabled
- [ ] Security headers verified (curl -I http://localhost/)
- [ ] Rate limiting tested
- [ ] Tests passing (pytest tests/)
- [ ] Dependency audit passed (safety check)

### Runtime Security
- [ ] Monitor logs for suspicious activity
- [ ] Check API quota usage
- [ ] Verify backups are working
- [ ] Monitor error rates
- [ ] Review rate limiting hits
- [ ] Check for security updates monthly

### Emergency Procedures
- [ ] Know how to restart services
- [ ] Know how to disable admin access
- [ ] Know how to rollback changes
- [ ] Have backup recovery procedures documented
