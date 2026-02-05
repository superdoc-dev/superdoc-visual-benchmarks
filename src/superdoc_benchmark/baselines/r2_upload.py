"""R2 baseline upload utilities for Word captures."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from PIL import Image

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class R2Config:
    """Cloudflare R2 configuration for bucket access."""

    account_id: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    bucket_name: str
    word_bucket_name: str

    @property
    def endpoint_url(self) -> str:
        """Return the R2 endpoint URL for this account."""
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


def _require_env(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"Missing {name}. Set it in your environment first.")
    return value


def load_r2_config() -> R2Config:
    """Load R2 configuration from environment variables.

    Raises:
        RuntimeError: If any required environment variable is missing.

    Returns:
        R2Config with credentials and bucket names.
    """
    account_id = _require_env(
        "SD_TESTING_R2_ACCOUNT_ID", os.getenv("SD_TESTING_R2_ACCOUNT_ID")
    )
    access_key_id = _require_env(
        "SD_TESTING_R2_ACCESS_KEY_ID", os.getenv("SD_TESTING_R2_ACCESS_KEY_ID")
    )
    secret_access_key = _require_env(
        "SD_TESTING_R2_SECRET_ACCESS_KEY", os.getenv("SD_TESTING_R2_SECRET_ACCESS_KEY")
    )
    bucket_name = _require_env(
        "SD_TESTING_R2_BUCKET_NAME", os.getenv("SD_TESTING_R2_BUCKET_NAME")
    )
    word_bucket_name = _require_env(
        "SD_TESTING_R2_WORD_BUCKET_NAME", os.getenv("SD_TESTING_R2_WORD_BUCKET_NAME")
    )
    return R2Config(
        account_id=account_id,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        bucket_name=bucket_name,
        word_bucket_name=word_bucket_name,
    )


def create_r2_client(config: R2Config) -> "S3Client":
    """Create a boto3 S3 client configured for Cloudflare R2.

    Args:
        config: R2 configuration with credentials and endpoint.

    Raises:
        RuntimeError: If boto3 is not installed.

    Returns:
        Configured S3 client for R2 operations.
    """
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except Exception as exc:
        raise RuntimeError(
            "Missing boto3. Install it with `pip install boto3` before uploading."
        ) from exc

    return boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def normalize_r2_key(value: str) -> str:
    """Normalize an R2 object key, validating against path traversal.

    Args:
        value: Raw R2 key string.

    Raises:
        RuntimeError: If key is empty or contains path traversal segments.

    Returns:
        Normalized key with consistent forward slashes.
    """
    cleaned = value.strip().replace("\\", "/")
    cleaned = re.sub(r"/{2,}", "/", cleaned).lstrip("/")
    if not cleaned:
        raise RuntimeError("R2 key must not be empty.")
    if any(part in {".", ".."} for part in cleaned.split("/") if part):
        raise RuntimeError("R2 key must not contain '.' or '..' path segments.")
    return cleaned


def normalize_filter(value: str) -> str:
    """Normalize a filter/prefix string, validating against path traversal.

    Args:
        value: Raw filter string (e.g., folder prefix).

    Raises:
        RuntimeError: If filter is empty or contains path traversal segments.

    Returns:
        Normalized filter with consistent forward slashes, no leading/trailing slashes.
    """
    cleaned = value.strip().replace("\\", "/")
    cleaned = re.sub(r"/{2,}", "/", cleaned).strip("/")
    if not cleaned:
        raise RuntimeError("Filter must not be empty.")
    parts = [part for part in cleaned.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise RuntimeError("Filter must not contain '.' or '..' path segments.")
    return "/".join(parts)


def _normalize_filter_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = value.strip().replace("\\", "/")
    cleaned = re.sub(r"/{2,}", "/", cleaned).strip("/")
    if not cleaned:
        return ""
    parts = [part for part in cleaned.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise RuntimeError("Filter must not contain '.' or '..' path segments.")
    return "/".join(parts)


def _folder_from_key(docx_key: str | None) -> str:
    if not docx_key:
        return ""
    parts = [part for part in docx_key.replace("\\", "/").split("/") if part]
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1])


def build_baseline_prefix(
    filter_name: str | None, docx_path: Path, docx_key: str | None = None
) -> str:
    """Build the R2 prefix path for a baseline capture.

    Args:
        filter_name: Optional explicit folder prefix (e.g., "lists", "tables").
        docx_path: Path to the docx file (used for filename).
        docx_key: Optional original R2 key (folder derived if filter_name is None).

    Raises:
        RuntimeError: If docx filename is invalid.

    Returns:
        R2 prefix like "lists/document.docx" or just "document.docx".
    """
    if filter_name is not None:
        folder = normalize_filter(filter_name)
    else:
        folder = _normalize_filter_or_empty(_folder_from_key(docx_key))
    docx_name = docx_path.name
    if not docx_name:
        raise RuntimeError(f"Invalid docx filename: {docx_path}")
    return f"{folder}/{docx_name}" if folder else docx_name


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to the file to hash.

    Returns:
        Hash string in format "sha256:<hexdigest>".
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def _list_objects(client: "S3Client", bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        params: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            params["ContinuationToken"] = token
        response = client.list_objects_v2(**params)
        for item in response.get("Contents", []) or []:
            key = item.get("Key")
            if key:
                keys.append(key)
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
    return keys


def _head_object(client: "S3Client", bucket: str, key: str) -> None:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        raise RuntimeError(f"R2 object not found: s3://{bucket}/{key}") from exc


def _object_exists(client: "S3Client", bucket: str, key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def resolve_docx_keys(
    config: R2Config,
    key_or_prefix: str | None,
    client: "S3Client | None" = None,
) -> list[str]:
    """Resolve a key or prefix to a list of .docx object keys.

    Args:
        config: R2 configuration.
        key_or_prefix: Single .docx key, folder prefix, or None for all.
        client: Optional pre-created S3 client (created if not provided).

    Raises:
        RuntimeError: If no .docx files found or key doesn't exist.

    Returns:
        List of .docx object keys sorted alphabetically.
    """
    if client is None:
        client = create_r2_client(config)
    if key_or_prefix is None:
        cleaned = ""
    else:
        cleaned = normalize_r2_key(key_or_prefix)
    if cleaned.lower().endswith(".docx"):
        _head_object(client, config.bucket_name, cleaned)
        return [cleaned]

    prefix = f"{cleaned.rstrip('/')}/" if cleaned else ""
    keys = _list_objects(client, config.bucket_name, prefix)
    docx_keys = sorted(
        key for key in keys if key.lower().endswith(".docx") and not key.endswith("/")
    )
    if not docx_keys:
        location = f"s3://{config.bucket_name}/{prefix}" if prefix else f"s3://{config.bucket_name}/"
        raise RuntimeError(f"No .docx files found at {location}")
    return docx_keys


def download_docx_keys(
    config: R2Config,
    keys: list[str],
    client: "S3Client | None" = None,
) -> tuple[list[Path], tempfile.TemporaryDirectory]:
    """Download .docx files from R2 to a temporary directory.

    Args:
        config: R2 configuration.
        keys: List of R2 object keys to download.
        client: Optional pre-created S3 client (created if not provided).

    Raises:
        RuntimeError: If download fails for any key.

    Returns:
        Tuple of (list of local file paths, TemporaryDirectory to cleanup).
    """
    if client is None:
        client = create_r2_client(config)
    temp_dir = tempfile.TemporaryDirectory(prefix="sd-word-docx-")
    root = Path(temp_dir.name)

    local_paths: list[Path] = []
    for key in keys:
        local_path = root / key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        response = client.get_object(Bucket=config.bucket_name, Key=key)
        body = response.get("Body")
        if body is None:
            raise RuntimeError(f"Missing body for s3://{config.bucket_name}/{key}")
        with local_path.open("wb") as handle:
            shutil.copyfileobj(body, handle)
        local_paths.append(local_path)

    return local_paths, temp_dir


def baseline_exists(
    config: R2Config,
    prefix: str,
    client: "S3Client | None" = None,
) -> bool:
    """Check if a baseline manifest exists at the given prefix.

    Args:
        config: R2 configuration.
        prefix: Baseline prefix (e.g., "lists/document.docx").
        client: Optional pre-created S3 client (created if not provided).

    Returns:
        True if manifest.json exists at the prefix.
    """
    if client is None:
        client = create_r2_client(config)
    key = f"{prefix.rstrip('/')}/{MANIFEST_NAME}"
    return _object_exists(client, config.word_bucket_name, key)


def _chunked(items: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _delete_keys(client: "S3Client", bucket: str, keys: list[str]) -> int:
    deleted = 0
    for batch in _chunked(keys, 1000):
        response = client.delete_objects(
            Bucket=bucket, Delete={"Objects": [{"Key": key} for key in batch]}
        )
        errors = response.get("Errors")
        if errors:
            detail = "; ".join(
                f"{err.get('Key')}: {err.get('Message')}" for err in errors
            )
            raise RuntimeError(f"Failed to delete existing objects: {detail}")
        deleted += len(batch)
    return deleted


def _collect_page_files(word_dir: Path) -> list[Path]:
    page_files = sorted(word_dir.glob("page_*.png"))
    if not page_files:
        raise RuntimeError(f"No Word pages found in {word_dir}")
    return page_files


def _build_manifest(docx_path: Path, page_files: list[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for page in page_files:
        width, height = _image_dimensions(page)
        files.append(
            {
                "path": page.name,
                "size_bytes": page.stat().st_size,
                "sha256": sha256_file(page),
                "width": width,
                "height": height,
            }
        )

    return {
        "docx_name": docx_path.name,
        "docx_sha256": sha256_file(docx_path),
        "page_count": len(page_files),
        "captured_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "files": files,
    }


def upload_word_baseline_capture(
    docx_path: Path,
    word_dir: Path,
    config: R2Config,
    filter_name: str | None,
    docx_key: str | None = None,
    dry_run: bool = False,
    client: "S3Client | None" = None,
) -> dict[str, Any]:
    """Upload Word baseline capture (page images + manifest) to R2.

    Args:
        docx_path: Path to the original .docx file.
        word_dir: Directory containing page_*.png captures.
        config: R2 configuration.
        filter_name: Optional folder prefix for the baseline.
        docx_key: Optional original R2 key (for folder derivation).
        dry_run: If True, check what would be uploaded without uploading.
        client: Optional pre-created S3 client (created if not provided).

    Raises:
        RuntimeError: If word_dir doesn't exist or has no page captures.

    Returns:
        Summary dict with keys: dry_run, bucket, prefix, pages, and either
        (uploaded, deleted) for real uploads or (existing, missing, extra) for dry runs.
    """
    if not word_dir.exists():
        raise RuntimeError(f"Word output directory not found: {word_dir}")

    page_files = _collect_page_files(word_dir)
    prefix = build_baseline_prefix(filter_name, docx_path, docx_key=docx_key)
    object_prefix = f"{prefix}/"
    bucket = config.word_bucket_name

    if client is None:
        client = create_r2_client(config)
    existing_keys = _list_objects(client, bucket, object_prefix)
    existing_set = set(existing_keys)

    expected_keys = [f"{object_prefix}{page.name}" for page in page_files]
    expected_keys.append(f"{object_prefix}{MANIFEST_NAME}")

    if dry_run:
        missing = [key for key in expected_keys if key not in existing_set]
        extra = [key for key in existing_set if key not in expected_keys]
        return {
            "dry_run": True,
            "bucket": bucket,
            "prefix": prefix,
            "pages": len(page_files),
            "existing": len(existing_keys),
            "missing": missing,
            "extra": extra,
        }

    deleted = _delete_keys(client, bucket, existing_keys) if existing_keys else 0

    for page in page_files:
        client.put_object(
            Bucket=bucket,
            Key=f"{object_prefix}{page.name}",
            Body=page.read_bytes(),
            ContentType="image/png",
        )

    manifest = _build_manifest(docx_path, page_files)
    client.put_object(
        Bucket=bucket,
        Key=f"{object_prefix}{MANIFEST_NAME}",
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "dry_run": False,
        "bucket": bucket,
        "prefix": prefix,
        "pages": len(page_files),
        "uploaded": len(page_files) + 1,
        "deleted": deleted,
    }
