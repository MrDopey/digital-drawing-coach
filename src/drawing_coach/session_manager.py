from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from drawing_coach.paths import sessions_dir

_DIR_FORMAT = "%Y-%m-%d_%H%M%S"


def default_session_name(start_time: datetime, drawing_app: str = "") -> str:
    label = start_time.strftime("%Y-%m-%d-%H-%M-%S")
    return f"{label} | {drawing_app}" if drawing_app else label


def _read_meta(session_dir: Path) -> dict:
    meta_path = session_dir / "meta.json"
    try:
        return json.loads(meta_path.read_text())
    except (OSError, ValueError):
        return {}


def _parse_start_time(meta: dict, session_dir: Path) -> datetime:
    value = meta.get("start_time")
    if value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    try:
        return datetime.strptime(session_dir.name, _DIR_FORMAT)
    except ValueError:
        return datetime.now()


def read_session_name(session_dir: Path) -> str:
    meta = _read_meta(session_dir)
    name = meta.get("name")
    if name:
        return name
    start_time = _parse_start_time(meta, session_dir)
    return default_session_name(start_time, meta.get("drawing_app", ""))


def write_session_name(session_dir: Path, name: str) -> None:
    meta = _read_meta(session_dir)
    name = name.strip()
    if name:
        meta["name"] = name
    else:
        meta.pop("name", None)
    (session_dir / "meta.json").write_text(json.dumps(meta, indent=2))


@dataclass
class SessionInfo:
    path: Path
    name: str
    start_time: datetime
    thumbnail: Path | None
    drawing_app: str = ""


def _last_frame(session_dir: Path) -> Path | None:
    frames_dir = session_dir / "frames"
    if not frames_dir.exists():
        return None
    frames = sorted(frames_dir.glob("*.png"))
    return frames[-1] if frames else None


def list_sessions(base_dir: Path | None = None) -> list[SessionInfo]:
    sd = base_dir if base_dir is not None else sessions_dir()
    if not sd.exists():
        return []
    infos: list[SessionInfo] = []
    for candidate in sd.iterdir():
        if not candidate.is_dir() or not (candidate / "meta.json").exists():
            continue
        meta = _read_meta(candidate)
        start_time = _parse_start_time(meta, candidate)
        name = meta.get("name") or default_session_name(
            start_time, meta.get("drawing_app", "")
        )
        infos.append(
            SessionInfo(
                path=candidate,
                name=name,
                start_time=start_time,
                thumbnail=_last_frame(candidate),
                drawing_app=meta.get("drawing_app", ""),
            )
        )
    infos.sort(key=lambda info: info.start_time, reverse=True)
    return infos


def delete_session(session_dir: Path) -> None:
    shutil.rmtree(session_dir, ignore_errors=True)
