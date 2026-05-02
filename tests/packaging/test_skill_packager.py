import json
import zipfile
from pathlib import Path

from we_together.packaging.skill_packager import pack_skill, unpack_skill


def _make_fake_root(tmp_path: Path) -> Path:
    root = tmp_path / "src_root"
    (root / "db" / "migrations").mkdir(parents=True)
    (root / "db" / "seeds").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "src" / "we_together").mkdir(parents=True)

    (root / "SKILL.md").write_text("# skill")
    (root / "db" / "migrations" / "0001.sql").write_text("CREATE TABLE t(x);")
    (root / "db" / "seeds" / "seed.yaml").write_text("a: 1")
    (root / "scripts" / "hello.py").write_text("print('hi')")
    (root / "src" / "we_together" / "__init__.py").write_text("")
    return root


def test_pack_and_unpack_roundtrip(tmp_path):
    root = _make_fake_root(tmp_path)
    out = tmp_path / "dist" / "we-together.weskill.zip"

    result = pack_skill(root, out, skill_version="0.8.0", schema_version="0007")
    assert out.exists()
    assert result["file_count"] >= 5
    assert result["manifest"]["skill_version"] == "0.8.0"

    with zipfile.ZipFile(out, "r") as zf:
        names = set(zf.namelist())
    assert "manifest.json" in names
    assert "SKILL.md" in names
    assert "db/migrations/0001.sql" in names

    target = tmp_path / "unpacked"
    unpack_result = unpack_skill(out, target)
    assert unpack_result["manifest"]["skill_version"] == "0.8.0"
    assert (target / "SKILL.md").read_text() == "# skill"
    assert (target / "db" / "migrations" / "0001.sql").exists()


def test_manifest_schema(tmp_path):
    root = _make_fake_root(tmp_path)
    out = tmp_path / "out.weskill.zip"
    pack_skill(root, out)
    with zipfile.ZipFile(out, "r") as zf:
        m = json.loads(zf.read("manifest.json"))
    assert m["format_version"] == 1
    assert m["name"] == "we-together"
    assert "created_at" in m
    assert "SKILL.md" in m["files"]


def test_pack_skill_rejects_forbidden_release_artifacts(tmp_path):
    root = _make_fake_root(tmp_path)
    (root / "dist").mkdir()
    (root / "dist" / "old.whl").write_text("wheel")
    out = tmp_path / "out.weskill.zip"

    try:
        pack_skill(root, out, include_globs=["SKILL.md", "dist/*"])
    except ValueError as exc:
        assert "forbidden package path" in str(exc)
    else:
        raise AssertionError("pack_skill accepted dist artifacts")


def test_unpack_skill_rejects_zip_slip_entries(tmp_path):
    pkg = tmp_path / "bad.weskill.zip"
    with zipfile.ZipFile(pkg, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", "{}")
        zf.writestr("../evil.py", "print('no')")

    try:
        unpack_skill(pkg, tmp_path / "unpacked")
    except ValueError as exc:
        assert "unsafe zip member" in str(exc)
    else:
        raise AssertionError("unpack_skill accepted a path traversal member")
