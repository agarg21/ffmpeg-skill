#!/usr/bin/env python3
"""End-to-end tests: build synthetic footage, run every script, verify with probe.

    python3 tests/test_all.py            # or: python3 -m unittest tests/test_all.py

The cases themselves live one module per tool group -- test_analysis, test_editing, test_audio,
test_picture, test_delivery, test_orchestration, test_accel, test_asr, test_cut_copy -- over the fixtures in _fixtures.py.
This file imports all nine so that the entry point every CI job, npm test and release_check.sh already runs
keeps running exactly the same set; each group module is also runnable on its own.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_accel  # noqa: E402
import test_analysis  # noqa: E402
import test_asr  # noqa: E402
import test_audio  # noqa: E402
import test_cut_copy  # noqa: E402
import test_delivery  # noqa: E402
import test_editing  # noqa: E402
import test_orchestration  # noqa: E402
import test_picture  # noqa: E402

MODULES = (test_analysis, test_editing, test_cut_copy, test_audio, test_picture, test_delivery, test_orchestration, test_accel,
           test_asr)


def load_tests(loader, tests, pattern):
    """unittest calls this instead of scanning this module: the cases are in the nine group
    modules, and naming them here keeps the set (and the order groups run in) explicit."""
    suite = unittest.TestSuite()
    for module in MODULES:
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


# `--jobs 3`: the groups run as 3 parallel processes, each with its own OUT directory (the fixtures are
# built once per process and many cases reuse output names). Split balanced by measured group times.
GROUPS_3 = (("test_picture", "test_cut_copy", "test_asr", "test_accel"),
            ("test_orchestration", "test_editing"),
            ("test_delivery", "test_analysis", "test_audio"))


def run_parallel(jobs):
    import os
    import subprocess
    import tempfile
    here = Path(__file__).resolve().parent
    names = [m.__name__ for m in MODULES]
    groups = GROUPS_3 if jobs == 3 else [names[i::jobs] for i in range(jobs)]
    assert sorted(n for g in groups for n in g) == sorted(names), "every group module runs exactly once"
    base = Path(os.environ.get("OUT", here / "out"))
    procs = []
    for k, group in enumerate(groups):
        env = dict(os.environ, OUT=str(base / f"shard-{k}"))
        log = tempfile.TemporaryFile()
        cmd = [sys.executable, "-m", "unittest", "-v", *group]
        procs.append((k, group, subprocess.Popen(cmd, cwd=str(here), env=env, stdout=log, stderr=subprocess.STDOUT), log))
    rc = 0
    for k, group, proc, log in procs:  # print each shard's whole log when it finishes, in order
        proc.wait()
        log.seek(0)
        print(f"===== shard {k}: {' '.join(group)} (exit {proc.returncode}) =====", flush=True)
        sys.stdout.buffer.write(log.read())
        sys.stdout.flush()
        rc = rc or proc.returncode
    return rc


if __name__ == "__main__":
    if "--jobs" in sys.argv:
        sys.exit(run_parallel(int(sys.argv[sys.argv.index("--jobs") + 1])))
    unittest.main(verbosity=2)
