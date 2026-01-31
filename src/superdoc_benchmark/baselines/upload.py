"""Internal baseline upload utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

from PIL import Image


@dataclass(frozen=True)
class UploadConfig:
    base_url: str
    api_key: str
    word_version_label: str
    platform_fingerprint: str


def _require_env(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(
            f"Missing {name}. Set it in your environment before using --with-upload."
        )
    return value


def load_upload_config(
    base_url: str | None = None,
    api_key: str | None = None,
    word_version_label: str | None = None,
    platform_fingerprint: str | None = None,
) -> UploadConfig:
    base_url = base_url or os.getenv("SUPERDOC_BASELINE_API_URL")
    api_key = api_key or os.getenv("BASELINE_UPLOAD_API_KEY")
    word_version_label = word_version_label or os.getenv("SUPERDOC_WORD_VERSION_LABEL")
    platform_fingerprint = platform_fingerprint or os.getenv("SUPERDOC_PLATFORM_FINGERPRINT")

    base_url = _require_env("SUPERDOC_BASELINE_API_URL", base_url).rstrip("/")
    api_key = _require_env("BASELINE_UPLOAD_API_KEY", api_key)
    word_version_label = _require_env(
        "SUPERDOC_WORD_VERSION_LABEL", word_version_label
    )
    platform_fingerprint = _require_env(
        "SUPERDOC_PLATFORM_FINGERPRINT", platform_fingerprint
    )

    return UploadConfig(
        base_url=base_url,
        api_key=api_key,
        word_version_label=word_version_label,
        platform_fingerprint=platform_fingerprint,
    )


def _normalize_doc_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-_.")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        raise RuntimeError(f"Could not derive a valid doc_id from '{value}'")
    return normalized.lower()


def parse_doc_id(docx_path: Path) -> tuple[str, str | None]:
    stem = docx_path.stem
    if "__" in stem:
        doc_id, doc_name = stem.split("__", 1)
        doc_id = _normalize_doc_id(doc_id)
        return doc_id, doc_name or None

    doc_id = _normalize_doc_id(stem)
    return doc_id, stem


def infer_category(docx_path: Path) -> str:
    for part in docx_path.parts:
        lowered = part.lower()
        if lowered in {"lists", "tables", "paragraphs"}:
            return lowered
    return "uncategorized"


def _normalize_group(value: str) -> str:
    if not re.match(r"^[A-Za-z0-9._-]+$", value):
        raise RuntimeError(
            f"Invalid group '{value}'. Use only letters, numbers, dot, underscore, or dash."
        )
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def _post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-sd-api-key", api_key)
    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        detail = f"{exc.code} {exc.reason}".strip()
        raise RuntimeError(f"Upload API request failed: {detail} {body}".strip()) from exc
    except Exception as exc:
        raise RuntimeError(f"Upload API request failed: {exc}") from exc


def _put_file(url: str, file_path: Path, content_type: str | None = None) -> None:
    data = file_path.read_bytes()
    req = request.Request(url, data=data, method="PUT")
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with request.urlopen(req, timeout=120) as resp:
            resp.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        detail = f"{exc.code} {exc.reason}".strip()
        raise RuntimeError(
            f"Failed to upload {file_path.name}: {detail} {body}".strip()
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to upload {file_path.name}: {exc}") from exc


def upload_word_baseline_capture(
    docx_path: Path,
    word_dir: Path,
    config: UploadConfig,
    group_override: str | None = None,
) -> dict[str, Any]:
    if not word_dir.exists():
        raise RuntimeError(f"Word output directory not found: {word_dir}")

    page_files = sorted(word_dir.glob("page_*.png"))
    if not page_files:
        raise RuntimeError(f"No Word pages found in {word_dir}")

    doc_id, doc_name = parse_doc_id(docx_path)
    doc_rev = sha256_file(docx_path)
    category = infer_category(docx_path)
    if group_override:
        category = _normalize_group(group_override)

    file_entries: list[dict[str, Any]] = []
    for page in page_files:
        width, height = _image_dimensions(page)
        file_entries.append(
            {
                "path": page.name,
                "size_bytes": page.stat().st_size,
                "sha256": sha256_file(page),
                "width": width,
                "height": height,
                "content_type": "image/png",
            }
        )

    init_payload = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "doc_rev": doc_rev,
        "generator": "msword",
        "generator_version": config.word_version_label,
        "baseline_type": "visual",
        "platform": config.platform_fingerprint,
        "category": category,
        "files": file_entries,
        "include_docx": True,
    }

    init_response = _post_json(
        f"{config.base_url}/api/baselines/init", init_payload, config.api_key
    )

    docx_upload = init_response.get("docx")
    if docx_upload and "upload_url" in docx_upload:
        _put_file(
            docx_upload["upload_url"],
            docx_path,
            docx_upload.get("content_type"),
        )

    uploads = init_response.get("files") or []
    upload_map = {
        str(item.get("path", "")).split("/")[-1]: item.get("upload_url")
        for item in uploads
    }

    for entry in file_entries:
        url = upload_map.get(entry["path"])
        if not url:
            raise RuntimeError(f"Missing upload URL for {entry['path']}")
        _put_file(url, word_dir / entry["path"], entry.get("content_type"))

    manifest_files = [
        {
            "path": entry["path"],
            "sha256": entry["sha256"],
            "size_bytes": entry["size_bytes"],
            "width": entry["width"],
            "height": entry["height"],
        }
        for entry in file_entries
    ]

    manifest_payload = {
        "doc_id": doc_id,
        "doc_rev": doc_rev,
        "doc_name": doc_name,
        "generator": "msword",
        "generator_version": config.word_version_label,
        "baseline_type": "visual",
        "platform": config.platform_fingerprint,
        "category": category,
        "files": manifest_files,
    }

    commit_response = _post_json(
        f"{config.base_url}/api/baselines/commit",
        {"manifest": manifest_payload},
        config.api_key,
    )

    return {
        "doc_id": doc_id,
        "doc_rev": doc_rev,
        "baseline_folder": init_response.get("baseline_folder"),
        "commit": commit_response,
    }
