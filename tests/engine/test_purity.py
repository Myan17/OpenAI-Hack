import json
import subprocess
import sys


def test_engine_imports_no_network_or_llm_clients() -> None:
    code = """
import importlib
import json
import sys

for module in (
    'interlock.engine.models',
    'interlock.engine.sqlkw',
    'interlock.engine.catalog',
    'interlock.engine.patterns',
    'interlock.engine.scope',
    'interlock.engine.enforcer',
    'interlock.engine.simulator',
):
    importlib.import_module(module)

print(json.dumps(sorted(sys.modules)))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    imported_modules = set(json.loads(result.stdout))
    forbidden_roots = {"anthropic", "httpx", "openai", "requests", "urllib3"}

    assert not (forbidden_roots & {name.partition(".")[0] for name in imported_modules})
