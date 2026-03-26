"""
Utility functions for file operations.
"""
from pathlib import Path
from typing import Optional

from app.config import get_settings

settings = get_settings()


def validate_file_type(filename: Optional[str]) -> bool:
    """Validate if file extension is allowed.

    Args:
        filename: Name of the file

    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False

    ext = Path(filename).suffix.lower()
    return ext in settings.ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get file extension from filename.

    Args:
        filename: Name of the file

    Returns:
        File extension including the dot
    """
    return Path(filename).suffix.lower()


async def save_upload_file(upload_file, destination: Path) -> int:
    """Save uploaded file to destination.

    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination path

    Returns:
        Size of saved file in bytes
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    content = await upload_file.read()
    with open(destination, "wb") as f:
        f.write(content)

    return len(content)


def get_mime_type(filename: str) -> str:
    """Get MIME type based on file extension.

    Args:
        filename: Name of the file

    Returns:
        MIME type string
    """
    ext = Path(filename).suffix.lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
    }

    return mime_types.get(ext, "application/octet-stream")
