import tomllib
from pathlib import Path


def test_pyproject_declares_vector_extra():
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    assert "vector" in extras
    vector = extras["vector"]
    assert any(dep.startswith("sqlite-vec") for dep in vector)
    assert any(dep.startswith("faiss-cpu") for dep in vector)
    assert any(dep.startswith("numpy") for dep in vector)
