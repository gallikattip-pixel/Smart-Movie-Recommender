# Smart Movie Recommender

A personalized movie and TV series recommendation system using content-based filtering, graph search algorithms, and user feedback.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI + Python 3.13 + scikit-learn
- **Movie Data**: TMDB API (server-side only)
- **Storage**: Browser localStorage (no database, no auth)

## Prerequisites

- Python 3.11+
- Node.js 18+
- TMDB API credentials (get from https://www.themoviedb.org/settings/api)

## Quick Start

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your TMDB credentials
# TMDB_ACCESS_TOKEN=your_v4_access_token
```

### 2. Start Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend runs at http://127.0.0.1:8000
Health check: http://127.0.0.1:8000/api/health
API docs: http://127.0.0.1:8000/docs

### 3. Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at http://localhost:5173 (proxies API calls to backend)

### 4. Run Tests

```bash
# Backend tests
cd backend
.venv\Scripts\activate  # or source .venv/bin/activate
pytest -v

# Frontend build verification
cd frontend
npm run build
```

## TMDB API Configuration

### Obtaining Credentials

1. Create an account at https://www.themoviedb.org/
2. Go to Settings > API: https://www.themoviedb.org/settings/api
3. Request an API key (v3) or use the Read Access Token (v4)
4. For this project, use the **Read Access Token (v4 auth)**

### Configuration

Add your token to the backend `.env` file:

```
TMDB_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiJ9...
TMDB_BASE_URL=https://api.themoviedb.org/3
```

**Important**: 
- The application starts without TMDB credentials
- Search endpoints return a clear 503 error when credentials are missing
- Never commit `.env` files or expose the token to the browser
- All TMDB calls go through the backend

### TMDB Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.
TMDB data provided by The Movie Database (https://www.themoviedb.org/).

## API Endpoints

- `GET /api/health` - Service health check
- `GET /api/search?q={query}&type={type}&page={page}` - Search movies/TV series
  - `type`: `multi` (default), `movie`, or `tv`
  - Returns normalized results with poster URLs when available
  - Person results excluded from multi-search

### Search Examples

```bash
# Search all (movies + TV)
curl "http://127.0.0.1:8000/api/search?query=inception&type=multi"

# Search movies only
curl "http://127.0.0.1:8000/api/search?query=inception&type=movie"

# Search TV series only
curl "http://127.0.0.1:8000/api/search?query=breaking%20bad&type=tv"

# Pagination
curl "http://127.0.0.1:8000/api/search?query=star%20wars&type=multi&page=2"
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_QUERY | Empty or whitespace-only query |
| 422 | (validation) | Invalid parameters (FastAPI) |
| 401 | TMDB_AUTH_FAILED | Invalid/expired TMDB token |
| 429 | TMDB_RATE_LIMITED | TMDB rate limit exceeded |
| 502 | TMDB_UPSTREAM_ERROR | TMDB server error |
| 503 | TMDB_NOT_CONFIGURED | TMDB credentials not set |
| 503 | TMDB_NETWORK_ERROR | Network connection failed |
| 504 | TMDB_TIMEOUT | Request timed out |

## Project Structure

```
movie-recommender/
├── .env.example              # Environment variable template
├── .gitignore
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── schemas.py           # Request/response models
│   │   ├── tmdb/                # TMDB integration
│   │   │   ├── __init__.py
│   │   │   ├── client.py        # TMDB API client
│   │   │   └── models.py        # TMDB response models
│   │   ├── recommender/         # Recommendation engine (future)
│   │   └── api/                 # API routes
│   │       ├── __init__.py
│   │       ├── search.py        # Search endpoints
│   │       ├── recommend.py     # Recommendation endpoints (future)
│   │       └── feedback.py      # Feedback endpoints (future)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py
│   │   └── test_search.py
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   └── Search.tsx       # Search interface
│   │   ├── services/
│   │   │   └── search.ts        # Search API client
│   │   ├── types/
│   │   │   └── search.ts        # Search type definitions
│   │   └── styles/
│   │       └── index.css
│   └── public/
```

## Development Notes

- Backend `.venv/`, frontend `node_modules/`, and build outputs are gitignored
- Never commit `.env` files or API credentials
- TMDB API token never exposed to browser
- All TMDB calls go through backend
- Frontend uses Vite proxy to backend during development

## License

MIT