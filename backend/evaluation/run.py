"""Run the evaluation and write the report from measured results.

    python -m evaluation.run          # deterministic, no API key needed
    python -m evaluation.run --llm    # also score extraction with Gemini (uses quota)
"""

import argparse
import itertools
import json
import platform
import tempfile
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import pgserver
from fastapi.testclient import TestClient

from app.chat import context
from app.config import ROOT_DIR, Settings
from app.main import create_app
from app.memory.policy import normalize
from app.recommendation.engine import Profile, build_profile, recommend
from app.schemas import RequestConstraints
from app.setup_db import load_menu_file, setup_database
from app.understanding.llm import GeminiProvider, LLMError
from app.understanding.service import understand
from app.vocabulary import ALLERGENS, DIETS
from evaluation.harness import Limits, Tally, violations_by_oracle
from evaluation.scenarios import SCENARIOS, Context

SECONDS_BETWEEN_CALLS = 6.5
REPORT = ROOT_DIR / "docs" / "EVALUATION.md"
PARAPHRASES = Path(__file__).with_name("paraphrases.json")
ATTRIBUTION = Path(__file__).with_name("attribution.json")


class PacedProvider:
    """Keeps a real model inside free-tier rate limits and counts its failures."""

    name = "gemini"

    def __init__(self, provider) -> None:
        self._provider = provider
        self.calls = self.failures = 0

    def understand(self, message):
        time.sleep(SECONDS_BETWEEN_CALLS)
        self.calls += 1
        try:
            return self._provider.understand(message)
        except LLMError:
            self.failures += 1
            raise


def run_scenarios(settings: Settings, provider=None) -> tuple[list[dict], Tally]:
    tally = Tally()
    results = []
    with TestClient(create_app(settings, provider=provider)) as client:
        context = Context(client, settings, tally)
        for scenario in SCENARIOS:
            try:
                scenario.run(context)
                detail = ""
            except Exception as error:  # a crash is a failed scenario, not a failed run
                detail = f"{type(error).__name__}: {error}"[:200]
            results.append({
                "area": scenario.area, "title": scenario.title,
                "passed": not detail, "detail": detail,
            })
    return results, tally


def constraint_sweep() -> dict:
    """Every allergen pair, diet and budget combination, checked by the oracle."""
    menu = load_menu_file()
    allergy_sets = [()] + [(a,) for a in ALLERGENS] + list(itertools.combinations(ALLERGENS, 2))
    profiles = recommendations = violating = 0
    for allergies, diet, budget, category in itertools.product(
        allergy_sets, (None, *DIETS), (None, 30, 60), (None, "starter", "main", "dessert", "drink")
    ):
        diets = (diet,) if diet else ()
        result = recommend(menu, Profile(
            allergies=frozenset(allergies), diets=frozenset(diets),
            max_price=budget, category=category,
        ), limit=len(menu))
        limits = Limits(allergens=allergies, diets=diets, max_price=budget)
        profiles += 1
        recommendations += len(result.recommendations)
        violating += sum(
            bool(violations_by_oracle(r.item.id, limits)) for r in result.recommendations
        )
    # Allergies of other diners arrive through the conversation, not through memory.
    for allergies in allergy_sets[1:]:
        profile = build_profile([], RequestConstraints(allergies=list(allergies)))
        result = recommend(menu, profile, limit=len(menu))
        limits = Limits(allergens=allergies)
        profiles += 1
        recommendations += len(result.recommendations)
        violating += sum(
            bool(violations_by_oracle(r.item.id, limits)) for r in result.recommendations
        )
    return {"profiles": profiles, "recommendations": recommendations, "violations": violating}


def attribution_score(provider) -> dict:
    """Whose statement is it? Others' allergies apply to the chat and are never saved."""
    cases = json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    correct = enforced = expected = wrongly_saved = fallbacks = 0
    misses = []
    for case in cases:
        result, engine = understand(case["message"], provider)
        fallbacks += engine == "fallback"
        saved = {
            (c.category, c.value)
            for candidate in result.preferences
            if candidate.scope == "persistent" and candidate.operation == "assert"
            for c in normalize(candidate)
        }
        table = set(context.clean(result.request).allergies)
        own = {("allergy", value) for value in case["own"]}
        needed = set(case["own"]) | set(case["table"])
        expected += len(needed)
        enforced += len(needed & ({v for c, v in saved if c == "allergy"} | table))
        wrongly_saved += bool(saved - own)
        if saved == own and set(case["table"]) <= table:
            correct += 1
        else:
            misses.append(case["message"])
    return {
        "cases": len(cases), "correct": correct, "enforced": enforced, "expected": expected,
        "wrongly_saved": wrongly_saved, "fallbacks": fallbacks, "misses": misses,
    }


def extraction_score(provider) -> dict:
    """Preference extraction on phrasings the rules were not written against."""
    cases = json.loads(PARAPHRASES.read_text(encoding="utf-8"))
    true_positive = false_positive = false_negative = exact = fallbacks = 0
    allergy_found = allergy_total = 0
    misses = []
    for case in cases:
        result, engine = understand(case["message"], provider)
        fallbacks += engine == "fallback"
        got = {
            (c.category, c.value, c.operation)
            for candidate in result.preferences if candidate.scope == "persistent"
            for c in normalize(candidate)
        }
        want = {tuple(e) for e in case["expected"]}
        true_positive += len(got & want)
        false_positive += len(got - want)
        false_negative += len(want - got)
        exact += got == want
        for item in want:
            if item[0] == "allergy" and item[2] == "assert":
                allergy_total += 1
                allergy_found += item in got
        if got != want:
            misses.append(case["message"])
    return {
        "cases": len(cases),
        "exact": exact,
        "precision": true_positive / max(true_positive + false_positive, 1),
        "recall": true_positive / max(true_positive + false_negative, 1),
        "allergy_found": allergy_found,
        "allergy_total": allergy_total,
        "fallbacks": fallbacks,
        "misses": misses,
    }


def percent(part: float, whole: float) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def render(
    results: list[dict], tally: Tally, sweep: dict, extraction: dict[str, dict],
    live: dict | None = None, attribution: dict[str, dict] | None = None,
) -> str:
    by_area: dict[str, list[dict]] = defaultdict(list)
    for result in results:
        by_area[result["area"]].append(result)

    def area(name: str) -> str:
        rows = by_area[name]
        passed = sum(r["passed"] for r in rows)
        return f"{passed}/{len(rows)} ({percent(passed, len(rows))})"

    passed = sum(r["passed"] for r in results)
    lines = [
        "# Evaluation report",
        "",
        "Generated by `python -m evaluation.run`. Do not edit by hand.",
        "",
        f"Run on {date.today().isoformat()}, Python {platform.python_version()}, "
        "PostgreSQL via pgserver.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| End-to-end scenarios passed | {passed}/{len(results)} |",
        f"| Hard-constraint violations, constraint sweep | {sweep['violations']} of "
        f"{sweep['recommendations']:,} recommendations over {sweep['profiles']:,} profiles |",
        f"| Hard-constraint violations, scenarios | {len(tally.violations)} of "
        f"{tally.recommendations} recommendations |",
        f"| Memory retrieval scenarios | {area('memory')} |",
        f"| Preference update scenarios | {area('updates')} |",
        f"| Cross-user isolation scenarios | {area('isolation')} |",
        f"| Recommendation quality scenarios (expected results) | {area('quality')} |",
        "",
        "The table above and the sweep use the deterministic rule extractor, so they "
        "measure memory, filtering, ranking and access control, not language understanding. "
        "The scenarios were written by the same author as the code; they are regression "
        "evidence, not an independent benchmark.",
        "",
        "## Language understanding on unseen phrasings",
        "",
        "`evaluation/paraphrases.json` holds messages written without consulting the "
        "extraction patterns, and no pattern has been added to match them.",
        "",
        "The first run scored 12/30 exact, 25% recall and 2/5 allergy statements. It exposed a "
        "safety defect: “sesame seeds” was stored as an unknown allergen, so tahini dishes were "
        "not excluded. Allergen canonicalisation was fixed (and covered by tests), so that one "
        "case is no longer unseen. Later, an audit led to a general rule for statements about "
        "other people, which also covers the “My colleague loves lamb” case, so that case is "
        "no longer unseen either. A stop-word added for a related bug (“my allergy” read as an "
        "allergen) also removed the rules’ one false positive on this set, in “the allergy test "
        "was negative”, which is why rules precision is higher than in earlier runs.",
        "",
        "| Extractor | Exact match | Precision | Recall | Allergy statements caught |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, score in extraction.items():
        lines.append(
            f"| {name} | {score['exact']}/{score['cases']} | {score['precision']:.0%} | "
            f"{score['recall']:.0%} | {score['allergy_found']}/{score['allergy_total']} |"
        )
        if score["fallbacks"]:
            lines.append(
                f"\n{score['fallbacks']} of {score['cases']} model calls failed and used rules."
            )
    if not any(name.startswith("Gemini") for name in extraction):
        lines += ["", "Gemini has not been scored in this run (`--llm` with an API key)."]
    for name, score in extraction.items():
        if score["misses"]:
            lines += ["", f"Messages {name} got wrong:", ""]
            lines += [f"- {message}" for message in score["misses"]]

    lines += [
        "", "## Whose statement is it?", "",
        "`evaluation/attribution.json` has sentences about other people, or about the customer "
        "while mentioning others. The same author wrote it just before the attribution patterns, "
        "and the patterns’ words for other people overlap with it, so it is a regression check, "
        "not a held-out test. “Enforced” counts allergens applied either from memory or to the "
        "current chat.",
        "",
        "| Extractor | Fully correct | Allergens enforced | Messages saving something wrong |",
        "| --- | --- | --- | --- |",
    ]
    for name, score in (attribution or {}).items():
        lines.append(
            f"| {name} | {score['correct']}/{score['cases']} | "
            f"{score['enforced']}/{score['expected']} | {score['wrongly_saved']} |"
        )
        if score["fallbacks"]:
            lines.append(
                f"\n{score['fallbacks']} of {score['cases']} model calls failed and used rules."
            )
    for name, score in (attribution or {}).items():
        if score["misses"]:
            lines += ["", f"Not fully correct with {name}:", ""]
            lines += [f"- {message}" for message in score["misses"]]

    if live:
        passed_live = sum(r["passed"] for r in live["results"])
        lines += [
            "", "## Scenarios with Gemini", "",
            f"{passed_live}/{len(live['results'])} scenarios passed with {live['model']} reading "
            f"messages. {live['failures']} of {live['calls']} model calls failed and used rules. "
            f"Hard-constraint violations: {len(live['tally'].violations)} of "
            f"{live['tally'].recommendations} recommendations.",
        ]
        lines += [
            f"- Failed: {r['title']} ({r['detail']})" for r in live["results"] if not r["passed"]
        ]
        lines += [
            "",
            "The first live run passed 23/26. It showed a hedged statement (“I don't eat much "
            "meat”) stored as a firm dislike, and “Do you have sushi?” not saying that sushi "
            "is not served; both were fixed. The third failure was a scenario that accepted only "
            "one of two correct history events, and the scenario was corrected.",
        ]
    lines += ["", "## Scenarios", "", "| Area | Scenario | Result |", "| --- | --- | --- |"]
    for result in results:
        outcome = "Pass" if result["passed"] else f"**Fail**: {result['detail']}"
        lines.append(f"| {result['area']} | {result['title']} | {outcome} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llm", action="store_true", help="also run extraction and scenarios with Gemini"
    )
    args = parser.parse_args()

    extraction = {"Rules only": extraction_score(None)}
    attribution = {"Rules only": attribution_score(None)}
    provider = None
    if args.llm:
        configured = Settings()
        if not configured.gemini_api_key:
            parser.error("--llm needs GEMINI_API_KEY")
        model = configured.gemini_model
        provider = PacedProvider(GeminiProvider(configured.gemini_api_key, model))
        extraction[f"Gemini ({model}) + rules"] = extraction_score(provider)
        attribution[f"Gemini ({model}) + rules"] = attribution_score(provider)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        server = pgserver.get_server(directory, cleanup_mode="stop")
        try:
            setup_database(server.get_uri(), local=True)
            settings = Settings(
                _env_file=None, auth_mode="local", database_url=server.get_uri(),
                gemini_api_key="", chat_rate_limit_per_minute=1000,
            )
            results, tally = run_scenarios(settings)
            live = None
            if provider:
                provider.calls = provider.failures = 0
                live_results, live_tally = run_scenarios(settings, provider)
                live = {
                    "model": model, "results": live_results, "tally": live_tally,
                    "calls": provider.calls, "failures": provider.failures,
                }
        finally:
            server.cleanup()

    report = render(results, tally, constraint_sweep(), extraction, live, attribution)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8", newline="\n")
    print(report)


if __name__ == "__main__":
    main()
