import shutil
import subprocess
from pathlib import Path


def test_e2e_smoke_script_completes(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "e2e_smoke.sh"
    if not shutil.which("bash"):
        return
    env = {"E2E_TMP_ROOT": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    result = subprocess.run(
        ["bash", str(script)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "===> OK" in result.stdout
