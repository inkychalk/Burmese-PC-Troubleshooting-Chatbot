# Pre-Deployment Checklist - Production Ready

**Last Updated:** September 17, 2026

## Complete Pre-Deployment Checklist

### Phase 1: Configuration & Secrets (CRITICAL)

#### Environment Variables
```bash
# MUST be set before deployment
SECRET_KEY=<generate-new-secure-key>
ADMIN_PASSWORD=<generate-new-strong-password>
GEMINI_API_KEY=<your-gemini-api-key>
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
FLASK_ENV=production

# Generate new SECRET_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate new ADMIN_PASSWORD:
openssl rand -base64 32
```

**Checklist:**
- [ ] SECRET_KEY is new and cryptographically random
- [ ] ADMIN_PASSWORD is new and strong (32+ chars)
- [ ] GEMINI_API_KEY is set (or willing to use local KB only)
- [ ] ALLOWED_ORIGINS matches your production domain
- [ ] FLASK_ENV=production
- [ ] All secrets are in .env file (NOT committed to git)
- [ ] .env file is in .gitignore
- [ ] Different SECRET_KEY from development
- [ ] Different ADMIN_PASSWORD from development

#### Secrets Management
- [ ] No secrets in source code
- [ ] No API keys in git history (`git log --all -p | grep API`)
- [ ] Rotate secrets on first deployment
- [ ] Set up secrets management (LastPass, AWS Secrets Manager, etc.)
- [ ] Document secret rotation schedule
- [ ] Create emergency access procedures

### Phase 2: Code Quality & Testing

#### Test Suite
```bash
# Run all tests
pytest --cov=backend --cov-fail-under=70

# Security audit
safety check -r backend/requirements.txt

# Code formatting
black --check backend/

# Linting
flake8 backend/ --max-line-length=100
```

**Checklist:**
- [ ] All tests passing: `pytest` returns 0 exit code
- [ ] Coverage >= 70%: `pytest --cov-fail-under=70`
- [ ] No security vulnerabilities: `safety check` passes
- [ ] Code formatted with black
- [ ] No linting errors with flake8
- [ ] No hardcoded passwords/keys
- [ ] No debug print statements left
- [ ] No TODO comments without assignee
- [ ] Database migration tested

#### Code Review
- [ ] Security review completed
- [ ] Performance review done
- [ ] Database schema reviewed
- [ ] API endpoints documented
- [ ] Error handling reviewed
- [ ] Logging levels appropriate
- [ ] No deprecated libraries
- [ ] Dependencies audited

### Phase 3: Database Preparation

#### Database Setup
```bash
# Verify database schema
sqlite3 /data/db.sqlite ".schema"

# Check for seed data
sqlite3 /data/db.sqlite "SELECT COUNT(*) FROM troubleshooting;"

# Verify indexes
sqlite3 /data/db.sqlite "SELECT * FROM sqlite_master WHERE type='index';"
```

**Checklist:**
- [ ] Database initialized with correct schema
- [ ] Seed data loaded (150 troubleshooting entries)
- [ ] Database file permissions correct (644)
- [ ] Database directory permissions correct (755)
- [ ] Backup strategy defined
- [ ] Backup tested and verified
- [ ] Backup location is remote (not on same server)
- [ ] Backup retention policy documented
- [ ] Recovery procedure documented and tested
- [ ] WAL mode enabled for SQLite
- [ ] Database is NOT writable by web server user directly

#### Data Migration
- [ ] Data migration scripts tested
- [ ] Rollback procedure documented
- [ ] Data validation checks in place
- [ ] Data backup before migration
- [ ] Migration tested on copy of production data

### Phase 4: Infrastructure & Deployment

#### Docker Configuration
```bash
# Test Docker build
docker-compose build

# Test Docker run
docker-compose up -d

# Verify containers running
docker-compose ps

# Check logs
docker logs burmese-pc-chatbot-backend
docker logs burmese-pc-chatbot-frontend
```

**Checklist:**
- [ ] Docker images built successfully
- [ ] Container base images updated
- [ ] No hardcoded credentials in Dockerfile
- [ ] Health checks working
- [ ] Container resource limits set (CPU, memory)
- [ ] Container restart policy configured
- [ ] Volume mounts correct
- [ ] Network configuration correct
- [ ] Logging driver configured
- [ ] Container security options reviewed

#### SSL/HTTPS Configuration
```bash
# Verify SSL certificate
openssl x509 -in /path/to/cert.pem -text -noout

# Check certificate expiration
openssl x509 -enddate -noout -in /path/to/cert.pem

# Test HTTPS
curl -I https://yourdomain.com
```

**Checklist:**
- [ ] SSL certificate obtained (Let's Encrypt recommended)
- [ ] Certificate not self-signed
- [ ] Certificate covers your domain
- [ ] Certificate valid for at least 90 days
- [ ] Certificate auto-renewal configured
- [ ] Private key securely stored
- [ ] Private key not in source code
- [ ] Certificate chain complete
- [ ] TLS 1.2+ enforced
- [ ] Weak ciphers disabled

#### Reverse Proxy (nginx)
- [ ] Nginx configuration reviewed
- [ ] Security headers configured (6 headers)
- [ ] CORS properly configured
- [ ] Rate limiting configured
- [ ] Compression enabled (gzip)
- [ ] Caching headers set appropriately
- [ ] Logging configured
- [ ] Error pages customized
- [ ] Upstream server configured correctly

### Phase 5: Security Hardening

#### API Security
```bash
# Test rate limiting
for i in {1..25}; do curl http://localhost:5000/api/chat; done

# Test CORS
curl -I -H "Origin: http://example.com" http://localhost:5000/api/chat

# Test security headers
curl -I http://localhost:5000/
```

**Checklist:**
- [ ] Rate limiting tested (20 req/min for chat)
- [ ] CORS restricted to specific origins
- [ ] Admin login rate limited (5 attempts/min)
- [ ] Security headers present (curl -I)
  - [ ] Strict-Transport-Security (HSTS)
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-Frame-Options: SAMEORIGIN
  - [ ] X-XSS-Protection: 1; mode=block
  - [ ] Content-Security-Policy configured
- [ ] HTTPS enforced (HTTP → HTTPS redirect)
- [ ] Session cookies secure (HttpOnly, Secure, SameSite)
- [ ] CSRF protection configured
- [ ] Input validation tested
- [ ] Error messages don't leak information

#### Authentication & Access Control
- [ ] Admin password is strong and unique
- [ ] Session timeout configured (30 min)
- [ ] No default/hardcoded credentials
- [ ] User roles defined (admin, user, anonymous)
- [ ] Authorization checks in place
- [ ] Login attempt logging enabled
- [ ] Failed login alerts configured

#### Data Protection
- [ ] Database encryption at rest (if sensitive data)
- [ ] Backups encrypted
- [ ] Secrets encrypted in transit (HTTPS)
- [ ] API keys rotated (GEMINI_API_KEY)
- [ ] No sensitive data in logs
- [ ] PII handling documented
- [ ] Data retention policy defined
- [ ] Data deletion procedures documented

### Phase 6: Monitoring & Logging

#### Logging Configuration
```bash
# Check logs are being created
docker logs burmese-pc-chatbot-backend | tail -20
docker logs burmese-pc-chatbot-frontend | tail -20

# Verify log levels
# Backend should have: INFO, WARNING, ERROR
# Frontend should have: access logs, error logs
```

**Checklist:**
- [ ] Application logging configured
- [ ] Access logs enabled (nginx)
- [ ] Error logs enabled
- [ ] Log rotation configured
- [ ] Logs not stored on server with app (use centralized logging)
- [ ] Sensitive data not logged (passwords, API keys)
- [ ] Log aggregation set up (ELK, Splunk, etc.)
- [ ] Log retention policy defined
- [ ] Log access controls configured

#### Monitoring & Alerts
```bash
# Services to monitor:
# - Docker container health
# - CPU and memory usage
# - Disk space
# - API response times
# - Error rates
# - Rate limit violations
# - Database connection pool
```

**Checklist:**
- [ ] Health check endpoint configured (`/health`)
- [ ] Uptime monitoring in place
- [ ] CPU monitoring enabled
- [ ] Memory monitoring enabled
- [ ] Disk space alerts configured
- [ ] API response time monitoring
- [ ] Error rate monitoring
- [ ] Rate limit violation alerts
- [ ] Database monitoring
- [ ] Alert recipients configured
- [ ] Incident response procedures documented

#### Metrics Collection
- [ ] Prometheus/Grafana setup (optional)
- [ ] Application metrics exposed
- [ ] System metrics collected

### Phase 7: Performance & Capacity

#### Load Testing
```bash
# Test API response time under load
ab -n 100 -c 10 https://yourdomain.com/health

# Or use Apache JMeter for more complex testing
```

**Checklist:**
- [ ] Load testing completed
- [ ] Response times acceptable (< 2 seconds)
- [ ] Capacity planning done
- [ ] Scalability documented
- [ ] Database connection pooling configured
- [ ] Caching strategy implemented
- [ ] CDN configured (if applicable)
- [ ] Static assets served from CDN
- [ ] Compression enabled
- [ ] Query optimization completed

#### Performance Benchmarks
- [ ] API response time: < 2 seconds
- [ ] Page load time: < 3 seconds
- [ ] Database query time: < 100ms
- [ ] Cache hit ratio: > 50%
- [ ] Server CPU: < 70% under normal load
- [ ] Server memory: < 80% under normal load

### Phase 8: Backup & Disaster Recovery

#### Backup Strategy
```bash
# Test database backup
docker exec burmese-pc-chatbot-backend \
  sqlite3 /data/db.sqlite ".backup backup.db"

# Verify backup
docker exec burmese-pc-chatbot-backend \
  sqlite3 backup.db "SELECT COUNT(*) FROM troubleshooting;"
```

**Checklist:**
- [ ] Backup schedule defined (daily recommended)
- [ ] Automated backups configured
- [ ] Backups stored remotely
- [ ] Backups encrypted
- [ ] Backup retention policy (30+ days)
- [ ] Backup integrity verified
- [ ] Recovery procedure documented
- [ ] Recovery tested (restore from backup)
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined
- [ ] Disaster recovery plan documented
- [ ] Disaster recovery drill completed

#### Rollback Procedure
- [ ] Rollback procedure documented
- [ ] Rollback tested
- [ ] Previous version available
- [ ] Data rollback procedure defined
- [ ] Communication plan for rollback

### Phase 9: Documentation

- [ ] Deployment steps written down somewhere you'll find them again
- [ ] Configuration documented (README.md, .env.example)
- [ ] API documented (README.md)
- [ ] Troubleshooting guide written (README.md, TESTING.md)
- [ ] Access credentials stored somewhere safe (password manager, not git)

### Phase 10: Final Pre-Deployment

#### Verification Tests
```bash
# Production simulation test
docker-compose down -v
docker-compose up -d
docker-compose ps

# Verify all services
curl http://localhost/
curl http://localhost:5000/health
curl http://localhost:5000/api/categories

# Wait 30 seconds and check logs
sleep 30
docker logs burmese-pc-chatbot-backend | tail -20
docker logs burmese-pc-chatbot-frontend | tail -20
```

**Checklist:**
- [ ] Production environment simulated
- [ ] All services start successfully
- [ ] Health checks pass
- [ ] API endpoints respond correctly
- [ ] Database accessible
- [ ] Logs clean (no errors)
- [ ] Security headers present
- [ ] SSL certificate valid
- [ ] CORS working correctly
- [ ] Rate limiting active

#### Go/No-Go Decision
- [ ] All checklist items completed
- [ ] All tests passing
- [ ] All security checks passed
- [ ] Monitoring and alerts ready
- [ ] Backup and recovery tested
- [ ] Rollback plan ready

## Critical Items (MUST COMPLETE)

These items **MUST** be completed before any deployment:

1. **SECRET_KEY Generated & Set**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   # Copy to .env
   ```

2. **ADMIN_PASSWORD Generated & Set**
   ```bash
   openssl rand -base64 32
   # Copy to .env
   ```

3. **GEMINI_API_KEY Configured**
   - Get from Google AI Studio
   - Set in .env

4. **ALLOWED_ORIGINS Set**
   - Your production domain
   - Set in .env

5. **HTTPS/SSL Certificate**
   - Valid certificate installed
   - Not self-signed
   - Auto-renewal configured

6. **Database Backup**
   - Tested backup/restore
   - Remote backup location

7. **All Tests Passing**
   ```bash
   pytest --cov-fail-under=70
   ```

8. **Security Audit**
   ```bash
   safety check -r backend/requirements.txt
   ```

9. **Security Headers Verified**
   ```bash
   curl -I https://yourdomain.com
   # Should have 6 security headers
   ```

10. **Monitoring Configured**
    - Health check alerts
    - Error rate alerts
    - Disk space alerts

## Deployment Day Checklist

### 1 Hour Before Deployment
- [ ] Rollback plan reviewed
- [ ] Backup created
- [ ] Monitoring dashboard open

### During Deployment
- [ ] Follow deployment guide step-by-step
- [ ] Monitor logs in real-time
- [ ] Check API responses
- [ ] Verify database connectivity
- [ ] Test with sample requests
- [ ] Monitor error rates

### After Deployment
- [ ] Smoke tests passed
- [ ] Health checks green
- [ ] Error rates normal
- [ ] Response times normal
- [ ] Database backup created

## Emergency Rollback Procedure

If deployment fails:

```bash
# 1. Stop new containers
docker-compose down

# 2. Restore from backup
docker exec burmese-pc-chatbot-backend \
  sqlite3 /data/db.sqlite < /path/to/backup.db

# 3. Start previous version
git checkout <previous-version-tag>
docker-compose up -d

# 4. Verify
curl http://localhost:5000/health

# 5. Document what went wrong and plan a fix before retrying
```

## Post-Deployment Targets

| Metric | Target |
|--------|--------|
| API Response Time | < 2 seconds |
| Error Rate | < 0.1% |
| CPU Usage | < 70% |
| Memory Usage | < 80% |
| Security Headers | 6/6 present |

See SECURITY.md and TESTING.md for more detail.
