"""Quick live TMDB connectivity test."""
import time
import httpx
from app.config import settings

print(f"Token configured: {bool(settings.tmdb_access_token)}")
print(f"Token length: {len(settings.tmdb_access_token)}")
print(f"Base URL: {settings.tmdb_base_url}")

headers = {
    "Authorization": f"Bearer {settings.tmdb_access_token}",
    "Accept": "application/json",
}

print("\n=== Authenticated search: bahubali ===")
start = time.time()
try:
    r = httpx.get(
        f"{settings.tmdb_base_url}/search/multi",
        params={"query": "bahubali", "page": 1, "language": "en-US"},
        headers=headers,
        timeout=15.0,
    )
    elapsed = time.time() - start
    print(f"  Status: {r.status_code} in {elapsed:.2f}s")
    data = r.json()
    results = data.get("results", [])
    tr = data.get("total_results", 0)
    print(f"  Total results: {tr}, page results: {len(results)}")
    for item in results[:5]:
        title = item.get("title") or item.get("name", "?")
        mt = item.get("media_type", "?")
        mid = item.get("id")
        print(f"    [{mt}] {title} (id={mid})")
except Exception as e:
    elapsed = time.time() - start
    print(f"  FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}")

print("\n=== Image configuration ===")
start = time.time()
try:
    r = httpx.get(
        f"{settings.tmdb_base_url}/configuration",
        headers=headers,
        timeout=15.0,
    )
    elapsed = time.time() - start
    print(f"  Status: {r.status_code} in {elapsed:.2f}s")
    data = r.json()
    images = data.get("images", {})
    print(f"  secure_base_url: {images.get('secure_base_url', 'N/A')}")
    print(f"  poster_sizes: {images.get('poster_sizes', [])}")
except Exception as e:
    elapsed = time.time() - start
    print(f"  FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}")

print("\n=== Movie details: Baahubali (264644) ===")
start = time.time()
try:
    r = httpx.get(
        f"{settings.tmdb_base_url}/movie/264644",
        params={"language": "en-US"},
        headers=headers,
        timeout=15.0,
    )
    elapsed = time.time() - start
    print(f"  Status: {r.status_code} in {elapsed:.2f}s")
    data = r.json()
    print(f"  Title: {data.get('title', 'N/A')}")
    print(f"  Release: {data.get('release_date', 'N/A')}")
    genres = [g.get("name") for g in data.get("genres", [])]
    print(f"  Genres: {genres}")
except Exception as e:
    elapsed = time.time() - start
    print(f"  FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}")
