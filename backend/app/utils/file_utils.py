import re
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

from app.config import settings, UPLOAD_DIR, OUTPUT_DIR, TEMPLATE_DIR


def sanitize_filename(filename: str) -> str:
    """Removes unsafe characters while preserving extensions."""
    base = Path(filename).name
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)
    return cleaned or "document"


async def save_uploaded_file(file: UploadFile, target_dir: Path) -> tuple[str, Path]:
    """Saves uploaded file safely and returns (file_id, full_path)."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' is not supported. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    file_id = f"{uuid.uuid4().hex[:12]}_{sanitize_filename(file.filename)}"
    destination = target_dir / file_id

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {settings.MAX_FILE_SIZE_MB}MB limit."
        )

    with open(destination, "wb") as f:
        f.write(contents)

    await file.seek(0)
    return file_id, destination


def get_file_path(file_id: str, search_dirs: list[Path] = None) -> Optional[Path]:
    """Finds a file path by ID across uploads, outputs, and templates."""
    if search_dirs is None:
        search_dirs = [UPLOAD_DIR, OUTPUT_DIR, TEMPLATE_DIR]
    
    # Direct match or exact file_id
    for directory in search_dirs:
        path = directory / file_id
        if path.exists() and path.is_file():
            return path
        
        # Or search for matching file name
        matches = list(directory.glob(f"*{file_id}*"))
        if matches:
            return matches[0]
            
    return None
