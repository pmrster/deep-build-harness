"""Run the deterministic Node execution test for the parallel-build workflow.

The orchestration logic of workflows/harness-build-parallel.js is JavaScript, so
its contracts (write-only workers with COMMIT_MODE: defer, canonical auditor +
read-only Explore refuters, majority math, no file I/O) are asserted by a Node
harness with mocked agent()/parallel(). This wrapper runs that harness inside
pytest so a regression fails the normal suite. Skips if Node is unavailable.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SMOKE = REPO / "tests" / "workflow_harness_smoke.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_parallel_build_workflow_contracts():
    assert SMOKE.exists(), f"missing {SMOKE}"
    r = subprocess.run(
        ["node", str(SMOKE)], cwd=REPO, capture_output=True, text=True
    )
    assert r.returncode == 0, f"workflow smoke failed:\n{r.stdout}\n{r.stderr}"


def test_parallel_build_workflow_file_present():
    # Independent of Node: the shipped script and its driver must exist.
    assert (REPO / "workflows" / "harness-build-parallel.js").exists()
    assert (REPO / "skills" / "harness-work-parallel" / "SKILL.md").exists()
    assert (REPO / "commands" / "harness-work-parallel.md").exists()


def test_refuter_agent_is_read_only():
    # The adversarial refuter must enforce read-only via frontmatter (harness
    # principle #3: two-layer tool enforcement), not just a prompt instruction.
    p = REPO / "agents" / "harness-refuter.md"
    assert p.exists(), "missing agents/harness-refuter.md"
    text = p.read_text()
    assert "disallowedTools: Write, Edit" in text, "refuter must disallow Write/Edit"
    # It must not grant Write/Edit in its tools line.
    tools_line = next((l for l in text.splitlines() if l.startswith("tools:")), "")
    assert "Write" not in tools_line and "Edit" not in tools_line, tools_line
