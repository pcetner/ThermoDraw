"""Consumer mistakes must not disappear into Any at public entry points."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("mypy")
ROOT = Path(__file__).resolve().parents[1]


def test_consumer_types(tmp_path):
    valid = tmp_path / "valid.py"
    valid.write_text('''from thermodraw import Diagram, DiagramBuilder, PhysicsResult, solve_physics
d: Diagram = DiagramBuilder(T="K").node("hot", value=400).build()
loaded: Diagram = Diagram.from_dict({})
result: PhysicsResult = solve_physics(d)
status: str = result.to_dict()["status"]
svg: str = d.svg("light")
''', encoding="utf-8")
    invalid = tmp_path / "invalid.py"
    invalid.write_text('''from thermodraw import Diagram, DiagramBuilder, solve_physics
d: str = DiagramBuilder().build()
r: int = solve_physics(123)
Diagram.from_dict([])
DiagramBuilder().node(123)
Diagram().svg(123)
''', encoding="utf-8")
    env = {**os.environ, "MYPYPATH": str(ROOT / "src")}
    def check(path):
        return subprocess.run([sys.executable, "-m", "mypy", "--follow-imports=silent",
                               "--check-untyped-defs", "--cache-dir", str(tmp_path / "cache"), str(path)],
                              capture_output=True, text=True, env=env)
    good = check(valid)
    assert good.returncode == 0, good.stdout + good.stderr
    bad = check(invalid)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    for line in range(2, 7):
        assert f"invalid.py:{line}: error:" in bad.stdout, bad.stdout
