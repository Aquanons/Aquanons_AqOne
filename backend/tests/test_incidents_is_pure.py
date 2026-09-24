import importlib
import pkgutil
import types

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
