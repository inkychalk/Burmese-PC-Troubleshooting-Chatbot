# Operations Guide

Running, maintaining, and troubleshooting the Burmese PC Troubleshooting Chatbot. For what the project is and why it was built, see the main [README](../README.md).

Commands use bash syntax (Git Bash, WSL, macOS, or Linux). Most single-line `docker` commands also work in Windows cmd; the multi-line Python examples need bash.

## Contents

- [Docker commands](#docker-commands)
- [Data storage](#data-storage)
- [Database commands](#database-commands)
- [Updating the knowledge base](#updating-the-knowledge-base)
- [Admin dashboard API](#admin-dashboard-api)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Docker commands

### Basic

```bash
docker compose up -d        # Start containers in the background
docker compose down         # Stop containers (keeps data)
docker compose restart      # Restart containers
docker compose ps           # List running containers
```

### Development

```bash
docker compose up -d --build                      # Rebuild after code changes
docker compose logs -f                            # Live logs, all services
docker logs burmese-pc-chatbot-backend -f         # Backend logs only
docker logs burmese-pc-chatbot-frontend -f        # Frontend logs only
docker logs burmese-pc-chatbot-backend --tail 50  # Last 50 lines
```

### Reset

```bash
docker compose down -v      # Stop and delete everything, including chat history and learned answers
docker compose up -d        # Start fresh
```

⚠️ `docker compose down -v` permanently deletes all saved chat messages and learned answers

## Data storage

Chat messages and conversation data are stored in SQLite.

- **Inside the container:** `/data/db.sqlite`
- **On the host:** Docker volume `burmese-pc_chatbot_chatbot-data`
- **Persists across** container restarts and rebuilds; deleted by `docker compose down -v`

Find the exact host location:

```bash
docker volume inspect burmese-pc_chatbot_chatbot-data
```

### Tables

| Table | Contents |
|---|---|
| `chat_messages` | All user and bot messages |
| `chat_sessions` | Conversation sessions, with platform and language |
| `troubleshooting` | Knowledge-base entries |
| `learned_responses` | Cached Gemini answers |

## Database commands

Show the 10 most recent chat messages:

```bash
docker exec -i burmese-pc-chatbot-backend python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/db.sqlite')
cursor = conn.cursor()
cursor.execute('SELECT id, session_id, role, message, timestamp FROM chat_messages ORDER BY timestamp DESC LIMIT 10')
for row in cursor.fetchall():
    print(row)
conn.close()
EOF
```

Open the database directly:

```bash
docker exec -it burmese-pc-chatbot-backend sqlite3 /data/db.sqlite
```

## Updating the knowledge base

`seed_data()` only inserts rows when the `troubleshooting` table is empty. Because the data lives in the persistent Docker volume, editing `troubleshooting_data.json` and restarting is not enough — the old entries stay.

To apply edits:

```bash
docker cp troubleshooting_data.json burmese-pc-chatbot-backend:/app/database/troubleshooting_data.json
docker exec -it burmese-pc-chatbot-backend python3 -c "
from database.models import get_connection, seed_data
conn = get_connection()
conn.execute(\"DELETE FROM troubleshooting WHERE source='seed'\")
conn.commit()
conn.close()
seed_data()
"
```

Then make the change survive future rebuilds:

```bash
docker compose build backend
docker compose up -d --force-recreate backend
```

After rewording entries, run the test suite — see the note in the README's Testing section about Burmese n-gram tests.

## Admin dashboard API

Session-based authentication: `POST /api/admin/login` sets a cookie, and every other route below requires an authenticated session.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/admin/login` | Body: `{"password": "..."}`. Rate-limited to 5 per minute |
| `POST` | `/api/admin/logout` | End the session |
| `GET` | `/api/admin/metrics` | Live snapshot: concurrent requests, active sessions, today's Gemini call count, and more |
| `GET` | `/api/admin/config` | Current tunables: rate limits, Gemini daily cap, session windows |
| `POST` | `/api/admin/config` | Update tunables, e.g. `{"rate_limit_per_minute": 30}` — must be a known key with a positive integer value |

## Development

### Where things live

| What | Where |
|---|---|
| Frontend | `frontend/` (HTML, CSS, JS) |
| Backend | `backend/` (Python, Flask) |
| Seed data | `troubleshooting_data.json` |
| Database schema | `backend/database/models.py` |

### Making changes

1. Edit files in `frontend/` or `backend/`
2. Rebuild and restart: `docker compose up -d --build`
3. Watch the logs: `docker compose logs -f`

### Testing the API directly

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "computer not turning on", "language": "en"}'

curl http://localhost:5000/health
curl http://localhost:5000/api/categories
```

## Troubleshooting

### "Server is not connected"

The backend API isn't responding.

```bash
docker compose ps                          # Is the backend running?
docker logs burmese-pc-chatbot-backend -f  # Look for errors
docker compose restart backend             # Restart it
```

### Database schema errors (`no such column`)

The database was created with an older schema. Recreate it:

```bash
docker compose down -v
docker compose up -d
```

This deletes chat history and learned answers.

### Port already in use

Port 80 or 5000 is taken by something else. Find what's using it:

```bash
netstat -ano | findstr :80     # Windows
netstat -ano | findstr :5000
```

Then either stop that process or change the ports in `docker-compose.yml`.

### Frontend loads but API calls fail

The frontend can't reach the backend.

```bash
curl http://localhost:5000/health
docker logs burmese-pc-chatbot-backend
docker compose ps
```

### Code changes not taking effect

Docker is using a cached image.

```bash
docker compose up -d --build
```

If that doesn't work, stop first:

```bash
docker compose down
docker compose up -d --build
```

### `nginx.conf` edits not taking effect

`docker/nginx.conf` is bind-mounted into the frontend container, but nginx only reads its config at startup, so a rebuild alone won't apply changes. Reload it:

```bash
docker exec burmese-pc-chatbot-frontend nginx -s reload
```

### Chatbot still gives old answers after editing the knowledge base

See [Updating the knowledge base](#updating-the-knowledge-base).
