"""Smoke test a running deployment: memory across conversations and user isolation.

    python -m evaluation.live_check https://your-app.onrender.com

Against Supabase it signs in two existing test accounts, read from the environment:
CHECK_USER_A, CHECK_PASSWORD_A, CHECK_USER_B, CHECK_PASSWORD_B.
It removes the preference it creates. The conversations it starts remain.
"""

import argparse
import os
import sys

import httpx


def sign_in(client: httpx.Client, config: dict, suffix: str) -> dict[str, str]:
    if config["auth_mode"] == "local":
        response = client.post("/api/local-auth/session", json={"name": f"check {suffix}"})
    else:
        response = client.post(
            f"{config['supabase_url']}/auth/v1/token?grant_type=password",
            headers={"apikey": config["supabase_anon_key"]},
            json={
                "email": os.environ[f"CHECK_USER_{suffix}"],
                "password": os.environ[f"CHECK_PASSWORD_{suffix}"],
            },
        )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def run(client: httpx.Client) -> list[tuple[str, bool]]:
    results: list[tuple[str, bool]] = []

    def check(name: str, passed: bool) -> None:
        results.append((name, passed))
        print(f"{'PASS' if passed else 'FAIL'}  {name}")

    check("health endpoint reaches the database", client.get("/api/health").is_success)
    check("web client is served", "Saffron" in client.get("/").text)
    check("API rejects anonymous requests", client.get("/api/memory").status_code == 401)
    config = client.get("/api/config").json()
    first, second = sign_in(client, config, "A"), sign_in(client, config, "B")

    told = client.post("/api/chat", headers=first, json={"message": "I'm allergic to sesame"})
    told.raise_for_status()
    engine = told.json()["message"]["payload"]["engine"]
    print(f"      message understanding engine: {engine}")
    check("language model is in use", engine == "gemini")

    later = client.post("/api/chat", headers=first, json={"message": "recommend a starter"})
    later.raise_for_status()
    picks = later.json()["message"]["payload"]["recommendations"]
    check(
        "a new conversation applies the remembered allergy",
        bool(picks) and all(
            "sesame" not in p["item"]["allergens"] + p["item"]["may_contain"] for p in picks
        ),
    )

    conversation = told.json()["conversation_id"]
    foreign = client.get(f"/api/conversations/{conversation}/messages", headers=second)
    check("another user cannot read the conversation", foreign.status_code == 404)

    own = client.get("/api/memory", headers=first).json()["preferences"]
    sesame = next(p for p in own if (p["category"], p["value"]) == ("allergy", "sesame"))
    foreign = client.delete(f"/api/memory/{sesame['id']}", headers=second)
    check("another user cannot change the allergy", foreign.status_code == 404)
    check("test preference removed", client.delete(
        f"/api/memory/{sesame['id']}", headers=first
    ).is_success)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    args = parser.parse_args()
    # The first request to a sleeping free-tier service can take a minute.
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=90) as client:
        results = run(client)
    sys.exit(0 if all(passed for _, passed in results) else 1)


if __name__ == "__main__":
    main()
