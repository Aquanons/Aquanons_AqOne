import ast
import importlib
import pkgutil
import types
from pathlib import Path

import app.incidents


def test_incident_policy_modules_are_framework_free():
    forbidden = {'fastapi', 'asyncpg', 'httpx', 'app.db'}
    for item in pkgutil.iter_modules(app.incidents.__path__, app.incidents.__name__ + '.'):
        module = importlib.import_module(item.name)
        imported = {
            value.__name__
            for value in vars(module).values()
            if isinstance(value, types.ModuleType)
        }
        assert not forbidden.intersection(imported), f'{item.name} imports {forbidden.intersection(imported)}'


def _fleet_watch_sources():
    # Imported here, not at the top, so the incidents check above still runs while app.fleet_watch is missing.
    package = importlib.import_module('app.fleet_watch')
    paths = sorted(Path(package.__path__[0]).glob('*.py'))
    assert {path.name for path in paths} >= {'tier.py', 'watch.py', 'trips.py', 'slots.py'}
    return paths


def test_fleet_watch_policy_imports_nothing_but_the_standard_library_and_itself():
    # docs/fleet-watch/PHASE_2_PLAN.md T2-43. app.geo is excluded too: "at sea" arrives as a callable.
    forbidden = ('fastapi', 'asyncpg', 'httpx', 'app.db', 'app.geo', 'app.api', 'app.ai', 'numpy')
    for path in _fleet_watch_sources():
        tree = ast.parse(path.read_text(encoding='utf-8'))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
                names += [f'{node.module}.{alias.name}' for alias in node.names]
        bad = [name for name in names if name.startswith(forbidden) or name == 'app']
        assert bad == [], f'{path.name} imports {bad}'


BANNED_CALLS = ('datetime.now(', 'datetime.utcnow(', 'time.time(', 'date.today(', 'import random', 'from random')


def test_fleet_watch_policy_never_reads_the_clock_or_randomness():
    # docs/fleet-watch/PHASE_2_PLAN.md T2-44: every function that needs the time takes `now`.
    for path in _fleet_watch_sources():
        source = path.read_text(encoding='utf-8')
        for banned in BANNED_CALLS:
            assert banned not in source, f'{path.name} uses {banned}'
