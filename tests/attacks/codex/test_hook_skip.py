#!/usr/bin/env python3
"""Exercise hook path decisions without writing to the user's real hook cache."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("audit_hook", ROOT / "skill" / "hook.py")
hook = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hook)


def run(which: str) -> int:
    watched = HERE / "hook_watch"
    if which == "internal":
        target = watched / "Opponent" / "Internal" / "received.pdf"
    elif which == "symlink":
        target = watched / "external-link.pdf"
    else:
        raise SystemExit("usage: test_hook_skip.py internal|symlink")
    config = dict(hook.DEFAULT_CFG)
    config["roots"] = [str(watched.resolve())]
    hook.cfg = lambda: config
    sys.stdin = io.StringIO(json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(target)}}))
    rc = hook.hook()
    result = {
        "case": which,
        "requested_path": str(target),
        "resolved_path": str(target.resolve()),
        "hook_return": rc,
        "meaning": "ALLOW" if rc == 0 else "BLOCK",
    }
    results = ROOT / "work" / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / f"hook-{which}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else ""))
