import re
from pathlib import Path

from fastapi import UploadFile

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_COVER_SIZE_BYTES = 5 * 1024 * 1024


def sanitize_isbn(isbn: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", isbn.strip())


def cover_file_path(upload_dir: Path, isbn: str, extension: str) -> Path:
    return upload_dir / "covers" / f"{sanitize_isbn(isbn)}{extension}"


def delete_cover_files(upload_dir: Path, isbn: str) -> None:
    covers_dir = upload_dir / "covers"
    if not covers_dir.exists():
        return
    prefix = sanitize_isbn(isbn)
    for path in covers_dir.glob(f"{prefix}.*"):
        path.unlink(missing_ok=True)


async def save_cover_file(upload_dir: Path, isbn: str, file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Cover must be a JPEG, PNG, WebP, or GIF image")

    data = await file.read()
    if not data:
        raise ValueError("Cover file is empty")
    if len(data) > MAX_COVER_SIZE_BYTES:
        raise ValueError("Cover file must be 5 MB or smaller")

    extension = ALLOWED_CONTENT_TYPES[content_type]
    covers_dir = upload_dir / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    delete_cover_files(upload_dir, isbn)
    destination = cover_file_path(upload_dir, isbn, extension)
    destination.write_bytes(data)
    return f"/uploads/covers/{destination.name}"
