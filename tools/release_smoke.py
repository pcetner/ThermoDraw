"""Exercise both distribution paths in clean environments outside the checkout."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


SMOKE = '''
import json
from pathlib import Path
from importlib.resources import files
from thermodraw import Diagram, solve_physics, assess_physics
data = {"units": {"T": "K", "R": "K/W"},
        "nodes": [{"id": "hot", "kind": "fixed", "value": 400},
                  {"id": "mid"}, {"id": "cold", "kind": "fixed", "value": 300}],
        "branches": [{"from": "hot", "to": "mid", "value": 2},
                     {"from": "mid", "to": "cold", "value": 3}],
        "analysis": {"network": {"steady": True, "unknowns": ["mid"]}}}
d = Diagram.from_dict(data)
r = solve_physics(d)
assert r.status == "solved" and abs(r.updates[0]["value"] - 360) < 1e-9
assert assess_physics(d)["status"] == "solved"
solved = r.apply(d)
assert "<svg" in solved.svg("light") and "<html" in solved.page()
assert len(list(files("thermodraw").joinpath("fonts").iterdir())) >= 4
assert files("thermodraw").joinpath("py.typed").is_file()
cv = Diagram.from_dict({"control_volumes": [{"id": "cv", "generation": 0, "steady": True}]})
assert solve_physics(cv).status == "solved" and "<svg" in cv.svg()
Path("input.json").write_text(solved.to_json(), encoding="utf-8")
print("Installed API, analysis, physical geometry, SVG, HTML, fonts and typing marker passed")
'''


def main(argv=None):
    dist = Path((argv or sys.argv[1:])[0]).resolve()
    wheels, sdists = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("Expected exactly one wheel and one sdist")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    with tempfile.TemporaryDirectory(prefix="thermodraw-artifacts-") as tmp:
        root = Path(tmp)
        for label, artifact in (("wheel", wheels[0]), ("sdist", sdists[0])):
            work = root / label
            work.mkdir()
            venv.create(work / "venv", with_pip=True)
            python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            def run(*args):
                subprocess.run([str(python), *args], cwd=work, env=env, check=True)
            # pip rebuilds the sdist in isolation, with its declared build dependencies.
            run("-m", "pip", "install", "--no-deps", "--no-cache-dir", str(artifact))
            run("-c", SMOKE)
            run("-m", "thermodraw", "render", "input.json", "--mode", "light", "-o", "out.svg")
            run("-m", "thermodraw", "solve-physics", "input.json", "--json")
            assert (work / "out.svg").is_file()
            print(f"{label}: passed", flush=True)


if __name__ == "__main__":
    main()
