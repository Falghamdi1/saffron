"""Shared fixtures. Database tests run against a real, throwaway PostgreSQL."""

import os

import pgserver
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.setup_db import load_menu_file, setup_database
from evaluation.harness import Diner


@pytest.fixture(scope="session")
def database_url(tmp_path_factory):
    # CI can point TEST_DATABASE_URL at a disposable local server instead.
    url = os.environ.get("TEST_DATABASE_URL")
    server = None
    if not url:
        server = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="delete")
        url = server.get_uri()
    setup_database(url, local=True)
    yield url
    if server:
        server.cleanup()


@pytest.fixture()
def settings(database_url):
    return Settings(
        _env_file=None, auth_mode="local", database_url=database_url, gemini_api_key="",
        chat_rate_limit_per_minute=1000,
    )


@pytest.fixture()
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def menu():
    return load_menu_file()


@pytest.fixture()
def admin(database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        yield connection


@pytest.fixture()
def diner(client):
    return Diner(client)
