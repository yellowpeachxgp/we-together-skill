"""Import audio CLI。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.importers.audio_importer import import_audio
from we_together.llm.providers.audio import MockAudioTranscriber


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--language", default=None)
    ap.add_argument("--provider", default="mock")
    args = ap.parse_args()

    if args.provider == "mock":
        t = MockAudioTranscriber()
    elif args.provider == "whisper":
        from we_together.llm.providers.audio import WhisperTranscriber
        t = WhisperTranscriber()
    else:
        print(f"unknown provider: {args.provider}", file=sys.stderr)
        return 2

    result = import_audio(Path(args.audio).resolve(), t, language=args.language)
    print(json.dumps({k: v for k, v in result.items() if k != "full_text"},
                      ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
