"""self_introspection（Phase 60 RX）：让 we-together 能描述自己。

列出 ADR / 不变式 / service / migration / plugin，并回答自审问题。
这是 v0.18 的独特差异化能力——没有其他 memory 框架做过。
"""
from __future__ import annotations

import re
from pathlib import Path

# 定位仓库根（从本文件向上找 pyproject.toml）
_THIS = Path(__file__).resolve()


def _find_repo_root() -> Path:
    for p in [_THIS.parent, *_THIS.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return _THIS.parents[3]


REPO_ROOT = _find_repo_root()


# --- ADR ---

def list_adrs() -> list[dict]:
    """扫 docs/superpowers/decisions/ 返回所有 ADR。"""
    adr_dir = REPO_ROOT / "docs" / "superpowers" / "decisions"
    if not adr_dir.exists():
        return []
    out: list[dict] = []
    for md in sorted(adr_dir.glob("????-*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        num = md.stem.split("-", 1)[0]
        title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
        status_match = re.search(r"^status:\s*(\S+)", text, re.MULTILINE | re.IGNORECASE)
        out.append({
            "adr_id": f"ADR {num}",
            "file": str(md.relative_to(REPO_ROOT)),
            "title": title_match.group(1).strip() if title_match else md.stem,
            "status": status_match.group(1).strip() if status_match else "unknown",
        })
    return out


def list_adrs_count() -> int:
    return len(list_adrs())


# --- 不变式（复用 invariants.py）---

def list_invariants() -> list[dict]:
    from we_together.invariants import list_as_dicts
    return list_as_dicts()


def invariant_coverage() -> dict:
    from we_together.invariants import coverage_summary
    return coverage_summary()


def check_invariant(invariant_id: int) -> dict:
    from we_together.invariants import get_invariant
    inv = get_invariant(invariant_id)
    if inv is None:
        return {"found": False, "invariant_id": invariant_id}
    return {
        "found": True,
        **inv.to_dict(),
        "covered": len(inv.test_refs) > 0,
    }


# --- Services ---

def list_services() -> list[dict]:
    services_dir = REPO_ROOT / "src" / "we_together" / "services"
    if not services_dir.exists():
        return []
    out: list[dict] = []
    for py in sorted(services_dir.glob("*.py")):
        if py.name.startswith("_"):
            continue
        out.append({
            "service": py.stem,
            "file": str(py.relative_to(REPO_ROOT)),
            "size_bytes": py.stat().st_size,
        })
    return out


def count_services() -> int:
    return len(list_services())


# --- Migrations ---

def list_migrations() -> list[dict]:
    mig_dir = REPO_ROOT / "db" / "migrations"
    if not mig_dir.exists():
        return []
    out: list[dict] = []
    for sql in sorted(mig_dir.glob("*.sql")):
        num = sql.stem.split("_", 1)[0]
        first_comment = ""
        try:
            text = sql.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if line.strip().startswith("--"):
                    first_comment = line.lstrip("-").strip()
                    break
        except Exception:
            pass
        out.append({
            "migration_id": num,
            "file": str(sql.relative_to(REPO_ROOT)),
            "title": sql.stem.split("_", 1)[1] if "_" in sql.stem else sql.stem,
            "comment": first_comment,
        })
    return out


# --- Plugins ---

def list_plugins() -> dict:
    try:
        from we_together.plugins import plugin_registry as pr
        return pr.status()
    except Exception as exc:
        return {"error": str(exc)}


# --- Scripts ---

def list_scripts() -> list[dict]:
    scripts_dir = REPO_ROOT / "scripts"
    if not scripts_dir.exists():
        return []
    out: list[dict] = []
    for py in sorted(scripts_dir.glob("*.py")):
        if py.name.startswith("_"):
            continue
        out.append({
            "script": py.stem,
            "file": str(py.relative_to(REPO_ROOT)),
        })
    return out


# --- 综合 ---

def self_describe() -> dict:
    """一份完整自描述：我是什么？我有什么？"""
    try:
        from we_together.cli import VERSION
    except Exception:
        VERSION = "unknown"

    invs = list_invariants()
    cov = invariant_coverage()
    return {
        "name": "we-together",
        "version": VERSION,
        "tagline": "Skill-first 的社会 + 世界图谱运行时",
        "pillars": {
            "A_strict_engineering": "严格工程化：ADR + 不变式 + 测试覆盖",
            "B_universal_skill": "通用型 Skill：Claude/OpenAI/MCP 三路 + plugin 扩展点",
            "C_cyber_ecosystem": "数字赛博生态圈：tick + 神经网格 + 遗忘 + 世界建模 + Agent 自主",
        },
        "adrs_total": list_adrs_count(),
        "invariants_total": len(invs),
        "invariants_covered": cov["covered"],
        "invariants_coverage_ratio": cov["coverage_ratio"],
        "services_total": count_services(),
        "migrations_total": len(list_migrations()),
        "scripts_total": len(list_scripts()),
    }
