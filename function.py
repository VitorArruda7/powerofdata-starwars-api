import os
import json
import requests
from flask import jsonify, make_response

SWAPI_BASE = "https://swapi.dev/api"

# Simple in-memory cache for the duration of process
_cache = {}

# Optional Redis client (if REDIS_URL provided)
_redis = None
try:
    import redis
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        _redis = redis.from_url(redis_url)
except Exception:
    _redis = None


def cache_get(key):
    if _redis:
        v = _redis.get(key)
        if v:
            return json.loads(v)
        return None
    return _cache.get(key)


def cache_set(key, value, ttl=None):
    if _redis:
        _redis.set(key, json.dumps(value), ex=ttl)
    else:
        _cache[key] = value


def fetch_url(url):
    cached = cache_get(url)
    if cached is not None:
        return cached
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    cache_set(url, data, ttl=300)
    return data


def get_resource_list(resource, filters=None):
    results = []
    url = f"{SWAPI_BASE}/{resource}/"
    while url:
        data = fetch_url(url)
        results.extend(data.get('results', []))
        url = data.get('next')

    if filters:
        for k, v in filters.items():
            results = [r for r in results if v.lower() in str(r.get(k, '')).lower()]

    return results


def film_characters(film_id, sort_by=None, sort_order='asc'):
    film_url = f"{SWAPI_BASE}/films/{film_id}/"
    film = fetch_url(film_url)
    chars = []
    for c_url in film.get('characters', []):
        try:
            chars.append(fetch_url(c_url))
        except Exception:
            continue

    if sort_by:
        reverse = sort_order == 'desc'
        chars.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)

    return {'film': film.get('title'), 'characters': chars}


def _require_api_key(request):
    keys = os.environ.get('API_KEYS')
    if not keys:
        return True, None
    allowed = [k.strip() for k in keys.split(',') if k.strip()]
    provided = request.headers.get('X-API-KEY') or request.args.get('api_key')
    if provided and provided in allowed:
        return True, provided
    return False, None


def starwars_function(request):
    """Entrypoint para Google Cloud Functions (HTTP).

    Suporta:
    - GET /v1/search?resource=people&name=Luke&page=1&page_size=10&sort_by=name&sort_order=asc
    - GET /v1/films/<id>/characters?sort_by=name&sort_order=asc
    Autenticação: se `API_KEYS` estiver setada, é necessário enviar header `X-API-KEY`.
    """
    # API key enforcement
    ok, _ = _require_api_key(request)
    if not ok:
        return make_response(jsonify({'error': 'unauthorized'}), 401)

    path = request.path

    # /v1/search
    if path.startswith('/v1/search'):
        resource = request.args.get('resource')
        if not resource:
            return make_response(jsonify({'error': 'resource query param required'}), 400)

        allowed = ['people', 'planets', 'starships', 'films']
        if resource not in allowed:
            return make_response(jsonify({'error': f'resource must be one of {allowed}'}), 400)

        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order', 'asc')
        page = request.args.get('page')
        page_size = request.args.get('page_size')
        limit = request.args.get('limit')

        try:
            page = int(page) if page else None
        except Exception:
            page = None
        try:
            page_size = int(page_size) if page_size else None
        except Exception:
            page_size = None
        if limit:
            try:
                limit = int(limit)
            except Exception:
                limit = None

        skip_keys = ('resource', 'sort_by', 'sort_order', 'limit', 'page', 'page_size')
        filters = {k: v for k, v in request.args.items() if k not in skip_keys}
        results = get_resource_list(resource, filters if filters else None)

        if sort_by:
            reverse = sort_order == 'desc'
            results.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)

        # pagination / limit
        if page and page_size:
            start = (page - 1) * page_size
            end = start + page_size
            paged = results[start:end]
            return make_response(jsonify({'count': len(results), 'page': page, 'page_size': page_size, 'results': paged}), 200)

        if limit:
            results = results[:limit]

        return make_response(jsonify({'count': len(results), 'results': results}), 200)

    # /v1/films/<id>/characters
    if path.startswith('/v1/films/') and path.endswith('/characters'):
        parts = path.strip('/').split('/')
        try:
            film_id = int(parts[2])
        except Exception:
            return make_response(jsonify({'error': 'invalid film id'}), 400)

        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order', 'asc')
        try:
            res = film_characters(film_id, sort_by, sort_order)
            return make_response(jsonify(res), 200)
        except requests.HTTPError:
            return make_response(jsonify({'error': 'film not found'}), 404)

    return make_response(jsonify({'error': 'not found'}), 404)
