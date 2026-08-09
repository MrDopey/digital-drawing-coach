#!/usr/bin/env python3
"""Headless CLI for the overlay debug tool. Runs one LLM request against an
image and prints a structured JSON result to stdout, so a calling agent loop
can inspect "ok"/"warning" and the exit code to decide whether to tweak the
prompt or schema and retry — no browser required.

Exit codes:
  0 - clean success: got a response that parsed against the schema.
  1 - got a response, but it didn't parse as valid structured output
      (see "warning" in the JSON) — a signal to revise the prompt/schema.
  2 - couldn't even complete the request (bad image, no LLM configured,
      malformed --schema-file, or the LLM call itself failed).

Typical agent workflow:
  overlay_debug_cli.py --dump-defaults /tmp/work
  # edit /tmp/work/prompt.txt and/or /tmp/work/schema.json
  overlay_debug_cli.py frame.png --prompt-file /tmp/work/prompt.txt \
      --schema-file /tmp/work/schema.json --pretty
  # inspect stdout / exit code, edit again, repeat
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import litellm
from PIL import Image

from drawing_coach.config_manager import ConfigManager
from drawing_coach.llm_debug_log import DebugIOLogger
from drawing_coach.overlay_debug_runner import (
    DEFAULT_SCHEMA,
    DEFAULT_SYSTEM_PROMPT,
    run_debug_request,
)


def _parse_bbox(text: str | None) -> tuple[int, int, int, int] | None:
    if not text:
        return None
    parts = [int(p.strip()) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError(
            "--character-bbox must be 4 comma-separated integers: x0,y0,x1,y1"
        )
    return (parts[0], parts[1], parts[2], parts[3])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "image", type=Path, nargs="?", help="path to the drawing screenshot to test"
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="system prompt text file (default: current app prompt)",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        help="response_format JSON schema file (default: current app schema)",
    )
    parser.add_argument(
        "--character-bbox",
        help="x0,y0,x1,y1 in pixels, to also compute the H5 hypothesis",
    )
    parser.add_argument(
        "--out", type=Path, help="also write the full JSON result to this file"
    )
    parser.add_argument(
        "--pretty", action="store_true", help="pretty-print the JSON result to stdout"
    )
    parser.add_argument(
        "--dump-defaults",
        type=Path,
        help="write the current app prompt/schema into this directory as "
        "prompt.txt and schema.json, then exit without calling the LLM",
    )
    args = parser.parse_args(argv)

    if args.dump_defaults:
        args.dump_defaults.mkdir(parents=True, exist_ok=True)
        (args.dump_defaults / "prompt.txt").write_text(DEFAULT_SYSTEM_PROMPT)
        (args.dump_defaults / "schema.json").write_text(
            json.dumps(DEFAULT_SCHEMA, indent=2)
        )
        print(json.dumps({"ok": True, "wrote": str(args.dump_defaults)}))
        return 0

    if args.image is None:
        parser.error("image is required unless --dump-defaults is given")

    try:
        character_bbox = _parse_bbox(args.character_bbox)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    try:
        image = Image.open(args.image).convert("RGB")
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Could not open image: {exc}"}))
        return 2

    system_prompt = args.prompt_file.read_text() if args.prompt_file else None

    response_format = None
    if args.schema_file:
        try:
            response_format = json.loads(args.schema_file.read_text())
        except json.JSONDecodeError as exc:
            print(
                json.dumps({"ok": False, "error": f"Schema is not valid JSON: {exc}"})
            )
            return 2

    config = ConfigManager().load()
    config.debug_log_llm_io = True
    litellm.callbacks.append(DebugIOLogger(config))

    result = run_debug_request(
        config,
        image,
        system_prompt=system_prompt,
        response_format=response_format,
        character_bbox=character_bbox,
    )

    output = json.dumps(result, indent=2 if args.pretty else None)
    print(output)
    if args.out:
        args.out.write_text(output)

    if not result["ok"]:
        return 2
    if result.get("warning"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
