"""Shared harness for the security-audit verification probes.

Every probe asserts the SAFE behaviour for one finding in
docs/security-audit/NEEDS-VALIDATION.md:

  FAILED with AssertionError / "Failed:"  -> CONFIRMED (unsafe behaviour observed)
  PASSED                                  -> REFUTED   (the safe behaviour holds)
  FAILED with ProbeBroken or any other exception, or ERROR
                                          -> INCONCLUSIVE (the probe broke)
  SKIPPED                                 -> NOT RUN   (e.g. no local Postgres)

Tests whose finding id ends in ':control' check the harness can see the
behaviour at all; they must PASS, or the paired probe is INCONCLUSIVE.

The finding id travels into the JUnit XML as a <property name="finding">,
so the results report can be generated without re-reading test names.
"""

from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line('markers', 'finding(id): the audit finding id this probe verifies')


@pytest.fixture(autouse=True)
def _tag_finding(request, record_property):
    marker = request.node.get_closest_marker('finding')
    if marker is not None:
        record_property('finding', marker.args[0])
