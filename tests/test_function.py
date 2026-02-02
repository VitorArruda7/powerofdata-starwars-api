import os
import sys
import requests
import pytest

# Ensure project root is on sys.path for pytest import resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from function import starwars_function


class MockResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.HTTPError(f'status {self.status_code}')


def fake_get_factory(mapping):
    def _get(url, *args, **kwargs):
        # Normalize SWAPI base trailing slashes
        key = url
        if key.endswith('/'):
            key = key
        if key in mapping:
            data, status = mapping[key]
            return MockResponse(data, status)
        raise RuntimeError('Unexpected URL: ' + url)

    return _get


def test_search_people_filter(monkeypatch):
    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Luke Skywalker', 'gender': 'male'},
            {'name': 'Leia Organa', 'gender': 'female'}
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))

    from flask import Flask
    import os
    # ensure API_KEYS is set so function requires and accepts our key
    os.environ['API_KEYS'] = 'testkey'
    app = Flask(__name__)
    with app.test_request_context('/v1/search?resource=people&name=Luke', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 200
        data = r.get_json()
        assert data['count'] == 1
        assert data['results'][0]['name'] == 'Luke Skywalker'


def test_auth_missing_key(monkeypatch):
    """Test that requests without API key fail when API_KEYS is set"""
    import os
    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Luke Skywalker', 'gender': 'male'},
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))
    os.environ['API_KEYS'] = 'testkey'

    from flask import Flask
    app = Flask(__name__)
    # No X-API-KEY header, should be rejected
    with app.test_request_context('/v1/search?resource=people'):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 401
        data = r.get_json()
        assert data['error'] == 'unauthorized'


def test_auth_invalid_key(monkeypatch):
    """Test that invalid API key is rejected"""
    import os
    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Luke Skywalker', 'gender': 'male'},
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))
    os.environ['API_KEYS'] = 'testkey'

    from flask import Flask
    app = Flask(__name__)
    # Wrong API key
    with app.test_request_context('/v1/search?resource=people', headers={'X-API-KEY': 'wrongkey'}):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 401


def test_pagination(monkeypatch):
    """Test pagination with page and page_size"""
    import os
    # Clear cache between tests
    from function import _cache
    _cache.clear()
    
    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Luke', 'id': 1},
            {'name': 'Leia', 'id': 2},
            {'name': 'Han', 'id': 3},
            {'name': 'Yoda', 'id': 4},
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))
    os.environ['API_KEYS'] = 'testkey'

    from flask import Flask
    app = Flask(__name__)
    # Page 1, size 2
    with app.test_request_context('/v1/search?resource=people&page=1&page_size=2', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 200
        data = r.get_json()
        assert data['count'] == 4, f"Expected 4, got {data['count']}"
        assert data['page'] == 1
        assert data['page_size'] == 2
        assert len(data['results']) == 2
        assert data['results'][0]['name'] == 'Luke'

    # Page 2, size 2
    with app.test_request_context('/v1/search?resource=people&page=2&page_size=2', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        data = r.get_json()
        assert len(data['results']) == 2
        assert data['results'][0]['name'] == 'Han'


def test_sort_order_desc(monkeypatch):
    """Test descending sort order"""
    import os
    from function import _cache
    _cache.clear()
    
    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Alice', 'birth_year': '42'},
            {'name': 'Zoe', 'birth_year': '25'},
            {'name': 'Bob', 'birth_year': '50'},
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))
    os.environ['API_KEYS'] = 'testkey'

    from flask import Flask
    app = Flask(__name__)
    # Sort by name descending
    with app.test_request_context('/v1/search?resource=people&sort_by=name&sort_order=desc', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        data = r.get_json()
        names = [r['name'] for r in data['results']]
        assert names == sorted(names, reverse=True)


def test_film_characters(monkeypatch):
    film_url = 'https://swapi.dev/api/films/1/'
    char1 = 'https://swapi.dev/api/people/1/'
    char2 = 'https://swapi.dev/api/people/2/'

    mapping = {
        film_url: ({'title': 'A New Hope', 'characters': [char1, char2]}, 200),
        char1: ({'name': 'Luke Skywalker'}, 200),
        char2: ({'name': 'C-3PO'}, 200),
    }

    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))

    from flask import Flask
    import os
    os.environ['API_KEYS'] = 'testkey'
    app = Flask(__name__)
    with app.test_request_context('/v1/films/1/characters', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 200
        data = r.get_json()
        assert data['film'] == 'A New Hope'
        assert len(data['characters']) == 2


def test_film_characters_sorted(monkeypatch):
    """Test film_characters with sort_order descending"""
    film_url = 'https://swapi.dev/api/films/1/'
    char1 = 'https://swapi.dev/api/people/1/'
    char2 = 'https://swapi.dev/api/people/2/'

    mapping = {
        film_url: ({'title': 'A New Hope', 'characters': [char1, char2]}, 200),
        char1: ({'name': 'Luke Skywalker'}, 200),
        char2: ({'name': 'C-3PO'}, 200),
    }

    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))

    import os
    os.environ['API_KEYS'] = 'testkey'
    from flask import Flask
    app = Flask(__name__)
    # Sort by name descending
    with app.test_request_context('/v1/films/1/characters?sort_by=name&sort_order=desc', headers={'X-API-KEY': 'testkey'}):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 200
        data = r.get_json()
        # Descending: Luke comes after C-3PO
        assert data['characters'][0]['name'] == 'Luke Skywalker'
        assert data['characters'][1]['name'] == 'C-3PO'


def test_no_auth_required_when_not_set(monkeypatch):
    """Test that requests are allowed when API_KEYS env var is not set"""
    import os
    from function import _cache
    _cache.clear()
    
    # Remove API_KEYS if set
    os.environ.pop('API_KEYS', None)

    base = 'https://swapi.dev/api/people/'
    mapping = {
        base: ({'next': None, 'results': [
            {'name': 'Luke Skywalker', 'gender': 'male'},
        ]}, 200)
    }
    monkeypatch.setattr(requests, 'get', fake_get_factory(mapping))

    from flask import Flask
    app = Flask(__name__)
    # No API key header, should succeed (no auth required)
    with app.test_request_context('/v1/search?resource=people'):
        r = starwars_function(__import__('flask').request)
        assert r.status_code == 200
        data = r.get_json()
        assert data['count'] == 1
