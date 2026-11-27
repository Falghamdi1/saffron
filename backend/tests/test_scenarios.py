"""The evaluation scenarios double as end-to-end regression tests."""

import pytest

from evaluation.harness import Tally
from evaluation.scenarios import SCENARIOS, Context


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.key)
def test_scenario(scenario, client, settings):
    scenario.run(Context(client, settings, Tally()))
