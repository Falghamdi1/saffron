"""Run the evaluation and write the report from measured results.

    python -m evaluation.run          # deterministic, no API key needed
    python -m evaluation.run --llm    # also score extraction with Gemini (uses quota)

Without --llm the report has no Gemini results, so regenerate with it before committing.
"""

import argparse
import itertools
import json
import platform
import re
import statistics
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
REPORT = ROOT_DIR / "docs" / "evaluation.md"
PARAPHRASES = Path(__file__).with_name("paraphrases.json")
ATTRIBUTION = Path(__file__).with_name("attribution.json")


class PacedProvider:
    """Keeps a real model inside free-tier rate limits and counts its failures."""

    name = "gemini"

    def __init__(self, provider) -> None:
        self._provider = provider
        self.calls = self.failures = 0
        self.seconds: list[float] = []  # successful calls, excluding the pacing pause

    def understand(self, message):
        time.sleep(SECONDS_BETWEEN_CALLS)
        self.calls += 1
        start = time.perf_counter()
        try:
            result = self._provider.understand(message)
        except LLMError:
            self.failures += 1
            raise
        self.seconds.append(time.perf_counter() - start)
        return result


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


METHOD = """## Method

| Layer | What it checks | How it is judged |
| --- | --- | --- |
| Unit and API tests (`pytest`) | policy, ranking, extraction, tokens, isolation | assertions |
| Scenarios (`evaluation/scenarios.py`) | whole turns through the HTTP API | expected state |
| Constraint sweep | every allergen pair, diet, budget and course | an independent checker |
| Held-out phrasings | preference extraction | exact match, precision, recall |
| Attribution set | whose statement it is | what is saved and what is enforced |
| Live check (`evaluation/live_check.py`) | the deployed app with two accounts | pass or fail |

The checker in `evaluation/harness.py` reads the raw menu records, so the recommender is
not graded by its own filtering code. Scenarios run on a throwaway PostgreSQL database.
"""

PHRASING_HISTORY = (
    "`evaluation/paraphrases.json` holds 30 messages written without consulting the "
    "extraction patterns. Three of them are no longer fully unseen, because later fixes "
    "touched them: “sesame seeds” was being stored as an unknown allergen (a safety defect "
    "found by this set), “My colleague loves lamb” is covered by the rule about other "
    "people, and a stop-word added for another bug removed a false positive in “the allergy "
    "test was negative”. The first run scored 12/30 exact, 25% recall and 2/5 allergy "
    "statements."
)

ATTRIBUTION_NOTE = (
    "`evaluation/attribution.json` has sentences about other people, or about the customer "
    "while mentioning others. The same author wrote it just before the attribution patterns, "
    "and the patterns’ words for other people overlap with it, so it is a regression check, "
    "not a held-out test. “Enforced” counts allergens applied either from memory or to the "
    "current chat."
)

# Recorded by hand, so that a later clean run does not hide earlier problems.
INCOMPLETE = """## Incomplete and failed runs

- 2026-11-27, complete run with Gemini: 29/30 scenarios with no model call failing. The one
  failure was a `MemoryError` on the test machine, whose memory another program had used up.
  That scenario passes with rules and passed in earlier Gemini runs.
- 2026-11-28, rerun: the free tier's limit of 500 requests a day for the model was reached
  part-way through the scenarios. The phrasing and attribution sets finished before that.
"""

NOT_COVERED = """## Not covered by this report

- The browser interface. It has no automated tests; screens were checked by hand.
- The deployed application. Run `evaluation/live_check.py` against it.
- Load, concurrency beyond one user at a time, and long-running memory growth.
- A real phone. Narrow layouts were checked in an emulated viewport.
- Independent test authors. The same author wrote the code, scenarios and sentence sets.
- Run-to-run variation. Model results come from one run; individual cases do change
  between runs.

See [limitations.md](limitations.md) for the product's known limitations.
"""


def _fallback_notes(scores: dict[str, dict]) -> list[str]:
    return [
        f"{name}: {s['fallbacks']} of {s['cases']} model calls failed and used rules, so this "
        "row is not a pure model result."
        for name, s in scores.items() if s["fallbacks"]
    ]


def _misses(scores: dict[str, dict], heading: str) -> list[str]:
    lines: list[str] = []
    for name, score in scores.items():
        if score["misses"]:
            lines += ["", f"{heading} with {name}:", ""]
            lines += [f"- {message}" for message in score["misses"]]
    return lines


def render(
    results: list[dict], tally: Tally, sweep: dict, extraction: dict[str, dict],
    attribution: dict[str, dict], live: dict | None = None,
) -> str:
    by_area: dict[str, list[dict]] = defaultdict(list)
    for result in results:
        by_area[result["area"]].append(result)

    def area(name: str) -> str:
        rows = by_area[name]
        return f"{sum(r['passed'] for r in rows)}/{len(rows)}"

    passed = sum(r["passed"] for r in results)
    lines = [
        "# Evaluation",
        "",
        "Generated by `python -m evaluation.run --llm`. Do not edit by hand.",
        "",
        f"Run on {date.today().isoformat()}, Python {platform.python_version()}, "
        "PostgreSQL via pgserver.",
        "",
        METHOD,
        "## Results without a language model",
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
        "These use the rule extractor, so they measure memory, filtering, ranking and access "
        "control, not language understanding. They are regression evidence, not an "
        "independent benchmark.",
        "",
    ]

    if live:
        passed_live = sum(r["passed"] for r in live["results"])
        timing = ""
        if live["seconds"]:
            timing = (
                f" Successful model calls took {statistics.median(live['seconds']):.1f} s at "
                f"the median and {max(live['seconds']):.1f} s at most, from one machine."
            )
        lines += [
            "## Scenarios with Gemini",
            "",
            f"{passed_live}/{len(live['results'])} scenarios passed with {live['model']} "
            f"reading messages. {live['failures']} of {live['calls']} model calls failed and "
            f"used rules. Hard-constraint violations: {len(live['tally'].violations)} of "
            f"{live['tally'].recommendations} recommendations.{timing}",
            "",
        ]
        if live["failures"]:
            lines += [
                "**This is not a complete model result:** the turns that failed were "
                "read by the rules, so the pass count above says little about the model.",
                "",
            ]
        lines += [
            f"- Failed: {r['title']} ({r['detail']})" for r in live["results"] if not r["passed"]
        ]
    else:
        lines += ["Gemini was not run (`--llm` with an API key).", ""]

    lines += [
        "## Language understanding on held-out phrasings",
        "",
        PHRASING_HISTORY,
        "",
        "| Extractor | Exact match | Precision | Recall | Allergy statements caught |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {name} | {s['exact']}/{s['cases']} | {s['precision']:.0%} | {s['recall']:.0%} | "
        f"{s['allergy_found']}/{s['allergy_total']} |"
        for name, s in extraction.items()
    ]
    lines += ["", *_fallback_notes(extraction), *_misses(extraction, "Messages wrong")]

    lines += [
        "", "## Whose statement is it?", "", ATTRIBUTION_NOTE, "",
        "| Extractor | Fully correct | Allergens enforced | Messages saving something wrong |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {name} | {s['correct']}/{s['cases']} | {s['enforced']}/{s['expected']} | "
        f"{s['wrongly_saved']} |"
        for name, s in attribution.items()
    ]
    lines += ["", *_fallback_notes(attribution), *_misses(attribution, "Not fully correct")]

    lines += [
        "",
        "## Failures found by evaluation",
        "",
        "Fixed, with tests unless noted:",
        "",
        "- “sesame seeds” stored as an unknown allergen, so tahini dishes were not excluded.",
        "- The first Gemini run passed 23/26 scenarios: a hedged statement stored as a firm "
        "dislike, an unknown dish not reported, and one scenario that was itself wrong.",
        "- The audit: another diner's allergy was not enforced, questions about other people "
        "were saved as the customer's allergy, spice limits were lost, and old requests "
        "shaped later answers ([engineering_audit.md](engineering_audit.md)).",
        "",
        "## Scenarios",
        "",
        "| Area | Scenario | Result |",
        "| --- | --- | --- |",
    ]
    for result in results:
        outcome = "Pass" if result["passed"] else f"**Fail**: {result['detail']}"
        lines.append(f"| {result['area']} | {result['title']} | {outcome} |")
    lines += ["", INCOMPLETE, NOT_COVERED]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"


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
                provider.seconds.clear()
                live_results, live_tally = run_scenarios(settings, provider)
                live = {
                    "model": model, "results": live_results, "tally": live_tally,
                    "calls": provider.calls, "failures": provider.failures,
                    "seconds": list(provider.seconds),
                }
        finally:
            server.cleanup()

    report = render(results, tally, constraint_sweep(), extraction, attribution, live)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8", newline="\n")
    print(report)


if __name__ == "__main__":
    main()
