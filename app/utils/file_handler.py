import os
import uuid
from pathlib import Path
from typing import List, Tuple
from fastapi import UploadFile
from app.config import settings
from app.core.exceptions import FileSizeException, FileTypeException


ALLOWED_MIME_TYPES = ["application/pdf"]
ALLOWED_EXTENSIONS = [".pdf"]


async def save_upload_file(
    upload_file: UploadFile,
    subdirectory: str,
    allowed_types: List[str] = ALLOWED_MIME_TYPES,
    allowed_extensions: List[str] = ALLOWED_EXTENSIONS,
) -> Tuple[str, str, int]:
    """
    Save uploaded file to disk
    Returns: (filename, file_path, file_size)
    """
    contents = await upload_file.read()
    file_size = len(contents)

    if file_size > settings.MAX_FILE_SIZE:
        raise FileSizeException(settings.MAX_FILE_SIZE)

    if upload_file.content_type not in allowed_types:
        raise FileTypeException(allowed_types)

    upload_file.filename = upload_file.filename or "no_name"
    original_ext = Path(upload_file.filename).suffix.lower()
    if original_ext not in allowed_extensions:
        raise FileTypeException(allowed_extensions)

    unique_filename = f"{uuid.uuid4()}{original_ext}"

    upload_dir = Path(settings.UPLOAD_DIR) / subdirectory
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(contents)

    return unique_filename, str(file_path), file_size


def delete_file(file_path: str) -> bool:
    """Delete file from disk"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception:
        pass
    return False
