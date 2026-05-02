"""Skill 打包 CLI: 把当前项目根打成 .weskill.zip。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.packaging.skill_packager import pack_skill, unpack_skill


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack")
    p_pack.add_argument("--root", default=".")
    p_pack.add_argument("--output", required=True)
    p_pack.add_argument("--skill-version", default=None)
    p_pack.add_argument("--schema-version", default=None)

    p_unp = sub.add_parser("unpack")
    p_unp.add_argument("package", type=str)
    p_unp.add_argument("--target", required=True)

    args = ap.parse_args()
    if args.cmd == "pack":
        r = pack_skill(Path(args.root).resolve(), Path(args.output).resolve(),
                       skill_version=args.skill_version,
                       schema_version=args.schema_version)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        r = unpack_skill(Path(args.package), Path(args.target).resolve())
        print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
