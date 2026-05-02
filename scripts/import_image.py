"""scripts/import_image.py — 把一张图走 OCR → 写 media_asset + memory。

用法:
  python scripts/import_image.py --root . --tenant-id alpha --image path/to.jpg \\
      --owner person_alice --scene scene_x --visibility shared
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.llm.providers.vision import MockVisionLLMClient
from we_together.services.ocr_service import ocr_to_memory
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser(description="Import an image into the SQLite graph via OCR")
    ap.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--image", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--scene", default=None)
    ap.add_argument("--visibility", default="shared",
                    choices=["private", "shared", "group"])
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id).resolve()
    db = tenant_root / "db" / "main.sqlite3"
    img = Path(args.image).resolve()
    if not img.exists():
        print(json.dumps({"error": "image not found"}))
        return 1
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    # 默认 Mock Vision；如需真 client 在此切换
    vision = MockVisionLLMClient(
        default_description=f"[imported image: {img.name}]",
    )
    result = ocr_to_memory(
        db, image_bytes=img.read_bytes(),
        owner_id=args.owner, scene_id=args.scene,
        visibility=args.visibility, vision_client=vision,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
