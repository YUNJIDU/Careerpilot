from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePosixPath

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_RESUME_BYTES = 5 * 1024 * 1024

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
RESUME_EXTENSIONS = {".pdf", ".docx", ".txt"}


def clean_filename(value: str) -> str:
    if not value or "\x00" in value or "/" in value or "\\" in value:
        raise ValueError("unsafe filename")
    name = PurePosixPath(value).name.strip()
    if not name or name in {".", ".."} or len(name) > 255:
        raise ValueError("unsafe filename")
    return name


def classify_file(
    filename: str,
    content_type: str,
    *,
    resume_only: bool = False,
) -> tuple[bool, str | None]:
    try:
        name = clean_filename(filename)
    except ValueError:
        return False, "unsafe filename"
    extension = PurePosixPath(name).suffix.casefold()
    allowed = RESUME_EXTENSIONS if resume_only else set(ALLOWED_TYPES)
    if extension not in allowed:
        return False, "file type is not allowed"
    normalized_type = content_type.split(";", 1)[0].strip().casefold()
    if normalized_type != ALLOWED_TYPES[extension]:
        return False, "file extension and content type do not match"
    return True, None


def validate_file_content(
    content: bytes,
    filename: str,
    content_type: str,
    *,
    resume_only: bool = False,
    maximum: int = MAX_ATTACHMENT_BYTES,
) -> None:
    allowed, reason = classify_file(filename, content_type, resume_only=resume_only)
    if not allowed:
        raise ValueError(reason or "unsupported file")
    if not content:
        raise ValueError("file is empty")
    if len(content) > maximum:
        raise ValueError("file exceeds size limit")
    extension = PurePosixPath(filename).suffix.casefold()
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF signature")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG signature")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise ValueError("invalid JPEG signature")
    if extension == ".txt":
        if b"\x00" in content:
            raise ValueError("text file contains binary data")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("text file must be UTF-8") from exc
    if extension == ".docx":
        _validate_docx(content)


def _validate_docx(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise ValueError("invalid DOCX structure")
            if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 50 * 1024 * 1024:
                raise ValueError("DOCX expands beyond safe limits")
            for entry in entries:
                normalized = entry.filename.replace("\\", "/")
                if (
                    normalized.startswith("/")
                    or re.match(r"^[A-Za-z]:", normalized)
                    or ".." in PurePosixPath(normalized).parts
                    or normalized.casefold().endswith("vbaproject.bin")
                ):
                    raise ValueError("unsafe DOCX content")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid DOCX archive") from exc
