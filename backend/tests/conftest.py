"""Shared fixtures. Database tests run against a real, throwaway PostgreSQL."""

import os
import uuid

import pgserver
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.setup_db import load_menu_file, setup_database


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


class Diner:
    """A signed-in test user talking to the API."""

    def __init__(self, client: TestClient, name: str | None = None) -> None:
        self.client = client
        self.name = name or f"diner-{uuid.uuid4().hex[:10]}"
        response = client.post("/api/local-auth/session", json={"name": self.name})
        response.raise_for_status()
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        self.conversation_id = None

    def say(self, message: str) -> dict:
        response = self.client.post(
            "/api/chat",
            json={"message": message, "conversation_id": self.conversation_id},
            headers=self.headers,
        )
        response.raise_for_status()
        body = response.json()
        self.conversation_id = body["conversation_id"]
        return body["message"]

    def new_conversation(self) -> None:
        self.conversation_id = None

    def get(self, path: str):
        return self.client.get(path, headers=self.headers)

    def memory(self) -> dict:
        return self.get("/api/memory").json()

    def preferences(self, status: str = "active") -> set[tuple[str, str]]:
        return {
            (p["category"], p["value"])
            for p in self.memory()["preferences"] if p["status"] == status
        }

    def preference_id(self, category: str, value: str) -> str:
        return next(
            p["id"] for p in self.memory()["preferences"]
            if (p["category"], p["value"]) == (category, value)
        )


@pytest.fixture()
def diner(client):
    return Diner(client)


def picks(message: dict) -> list[str]:
    return [r["item"]["id"] for r in message["payload"]["recommendations"]]
