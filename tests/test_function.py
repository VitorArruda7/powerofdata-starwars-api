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
