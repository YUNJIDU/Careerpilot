from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePosixPath

MAX_RESUME_BYTES = 5 * 1024 * 1024
TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def clean_filename(value: str) -> str:
    if not value or "\x00" in value or "/" in value or "\\" in value:
        raise ValueError("unsafe filename")
    name = PurePosixPath(value).name.strip()
    if not name or name in {".", ".."} or len(name) > 255:
        raise ValueError("unsafe filename")
    return name


def validate_resume(content: bytes, filename: str, content_type: str) -> str:
    filename = clean_filename(filename)
    extension = PurePosixPath(filename).suffix.casefold()
    if (
        extension not in TYPES
        or content_type.split(";", 1)[0].strip().casefold() != TYPES[extension]
    ):
        raise ValueError("file extension and content type do not match")
    if not content:
        raise ValueError("file is empty")
    if len(content) > MAX_RESUME_BYTES:
        raise ValueError("resume exceeds 5 MiB")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF signature")
    if extension == ".txt":
        if b"\x00" in content:
            raise ValueError("text file contains binary data")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("text file must be UTF-8") from exc
    if extension == ".docx":
        _validate_docx(content)
    return filename


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
                name = entry.filename.replace("\\", "/")
                if (
                    name.startswith("/")
                    or re.match(r"^[A-Za-z]:", name)
                    or ".." in PurePosixPath(name).parts
                    or name.casefold().endswith("vbaproject.bin")
                ):
                    raise ValueError("unsafe DOCX content")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid DOCX archive") from exc
