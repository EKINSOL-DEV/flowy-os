"""
Photos Cog: manages photo albums, photo uploads with resizing, and photo themes.
Storage is JSON-based with photos stored as JPEG files on disk.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from pydantic import BaseModel, Field

# Pillow is optional; endpoints that need it will fail gracefully.
try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PHOTOS_DIR = Path(os.environ.get("FLOWY_PHOTOS_DIR", "/flowy/photos"))
ALBUMS_JSON = PHOTOS_DIR / "albums.json"
THEMES_JSON = PHOTOS_DIR / "themes.json"

MAX_DIMENSION = 1920
JPEG_QUALITY = 85
THUMB_SIZE = 200

router = APIRouter(prefix="/photos", tags=["Photos"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Album(BaseModel):
    id: str
    name: str
    createdAt: str
    photoCount: int = 0


class AlbumCreate(BaseModel):
    name: str


class Photo(BaseModel):
    id: str
    albumId: str
    filename: str
    thumbnailFilename: str
    uploadedAt: str
    width: int
    height: int


class PhotoMoveRequest(BaseModel):
    albumId: str


class PhotoTheme(BaseModel):
    id: str
    name: str
    compositionId: str
    albumId: str
    baseThemeId: Optional[str] = None
    rotationIntervalS: int = 30


class PhotoThemeCreate(BaseModel):
    name: str
    compositionId: str
    albumId: str
    baseThemeId: Optional[str] = None
    rotationIntervalS: int = 30


class PhotoThemeUpdate(BaseModel):
    name: Optional[str] = None
    compositionId: Optional[str] = None
    albumId: Optional[str] = None
    baseThemeId: Optional[str] = None
    rotationIntervalS: Optional[int] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> None:
    """Create directory (and parents) if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> list:
    """Read a JSON array file, returning an empty list if missing or corrupt."""
    if not path.exists():
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _write_json(path: Path, data: list) -> None:
    """Atomically write a JSON array file."""
    _ensure_dir(path.parent)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _album_dir(album_id: str) -> Path:
    return PHOTOS_DIR / album_id


def _photos_json(album_id: str) -> Path:
    return _album_dir(album_id) / "photos.json"


def _require_pillow() -> None:
    if Image is None:
        raise HTTPException(
            status_code=500,
            detail="Pillow (PIL) is not installed; photo upload is unavailable.",
        )


def _find_album(albums: list, album_id: str) -> dict:
    for a in albums:
        if a.get("id") == album_id:
            return a
    raise HTTPException(status_code=404, detail=f"Album not found: {album_id}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Album endpoints
# ---------------------------------------------------------------------------

@router.get("/albums", summary="List albums", response_model=List[Album])
def list_albums():
    albums = _read_json(ALBUMS_JSON)
    # Recalculate photo counts from disk
    for album in albums:
        photos = _read_json(_photos_json(album["id"]))
        album["photoCount"] = len(photos)
    return albums


@router.post("/albums", summary="Create album", response_model=Album, status_code=201)
def create_album(body: AlbumCreate):
    albums = _read_json(ALBUMS_JSON)
    album = {
        "id": str(uuid4()),
        "name": body.name,
        "createdAt": _now_iso(),
        "photoCount": 0,
    }
    albums.append(album)
    _write_json(ALBUMS_JSON, albums)
    _ensure_dir(_album_dir(album["id"]))
    return album


@router.get("/albums/{album_id}", summary="Album detail with photo list")
def get_album(album_id: str):
    albums = _read_json(ALBUMS_JSON)
    album = _find_album(albums, album_id)
    photos = _read_json(_photos_json(album_id))
    album["photoCount"] = len(photos)
    return {"album": album, "photos": photos}


@router.delete("/albums/{album_id}", summary="Delete album and all its photos")
def delete_album(album_id: str):
    albums = _read_json(ALBUMS_JSON)
    _find_album(albums, album_id)  # raises 404 if missing
    albums = [a for a in albums if a["id"] != album_id]
    _write_json(ALBUMS_JSON, albums)
    # Remove album directory from disk
    album_path = _album_dir(album_id)
    if album_path.exists():
        shutil.rmtree(album_path)
    return {"ok": True}

# ---------------------------------------------------------------------------
# Photo upload / delete / move
# ---------------------------------------------------------------------------

@router.post(
    "/albums/{album_id}/upload",
    summary="Upload photo (multipart)",
    response_model=Photo,
    status_code=201,
)
async def upload_photo(album_id: str, file: UploadFile = File(...)):
    _require_pillow()

    # Verify album exists
    albums = _read_json(ALBUMS_JSON)
    _find_album(albums, album_id)

    # Read uploaded bytes
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file upload")

    import io

    try:
        img = Image.open(io.BytesIO(contents))
        img = img.convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    # Resize if larger than MAX_DIMENSION
    w, h = img.size
    if max(w, h) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    final_w, final_h = img.size

    # Generate filenames
    photo_id = str(uuid4())
    filename = f"{photo_id}.jpg"
    thumb_filename = f"{photo_id}_thumb.jpg"

    album_path = _album_dir(album_id)
    _ensure_dir(album_path)

    # Save full-size JPEG
    img.save(album_path / filename, "JPEG", quality=JPEG_QUALITY)

    # Save thumbnail
    thumb = img.copy()
    thumb.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    thumb.save(album_path / thumb_filename, "JPEG", quality=JPEG_QUALITY)

    # Update photos.json
    photo = {
        "id": photo_id,
        "albumId": album_id,
        "filename": filename,
        "thumbnailFilename": thumb_filename,
        "uploadedAt": _now_iso(),
        "width": final_w,
        "height": final_h,
    }
    photos = _read_json(_photos_json(album_id))
    photos.append(photo)
    _write_json(_photos_json(album_id), photos)

    return photo


@router.delete("/{photo_id}", summary="Delete a photo")
def delete_photo(photo_id: str):
    # We need to find which album this photo belongs to
    albums = _read_json(ALBUMS_JSON)
    for album in albums:
        photos_path = _photos_json(album["id"])
        photos = _read_json(photos_path)
        for photo in photos:
            if photo.get("id") == photo_id:
                # Remove files from disk
                album_path = _album_dir(album["id"])
                _safe_unlink(album_path / photo["filename"])
                _safe_unlink(album_path / photo["thumbnailFilename"])
                # Remove from JSON
                photos = [p for p in photos if p["id"] != photo_id]
                _write_json(photos_path, photos)
                return {"ok": True}

    raise HTTPException(status_code=404, detail=f"Photo not found: {photo_id}")


@router.post("/{photo_id}/move", summary="Move photo to another album")
def move_photo(photo_id: str, body: PhotoMoveRequest):
    target_album_id = body.albumId

    # Verify target album exists
    albums = _read_json(ALBUMS_JSON)
    _find_album(albums, target_album_id)

    # Find the photo in its current album
    for album in albums:
        src_album_id = album["id"]
        photos_path = _photos_json(src_album_id)
        photos = _read_json(photos_path)
        for photo in photos:
            if photo.get("id") == photo_id:
                if src_album_id == target_album_id:
                    return {"ok": True, "photo": photo}

                src_dir = _album_dir(src_album_id)
                dst_dir = _album_dir(target_album_id)
                _ensure_dir(dst_dir)

                # Move files on disk
                for fname_key in ("filename", "thumbnailFilename"):
                    src_file = src_dir / photo[fname_key]
                    dst_file = dst_dir / photo[fname_key]
                    if src_file.exists():
                        shutil.move(str(src_file), str(dst_file))

                # Remove from source album
                photos = [p for p in photos if p["id"] != photo_id]
                _write_json(photos_path, photos)

                # Add to target album
                photo["albumId"] = target_album_id
                target_photos = _read_json(_photos_json(target_album_id))
                target_photos.append(photo)
                _write_json(_photos_json(target_album_id), target_photos)

                return {"ok": True, "photo": photo}

    raise HTTPException(status_code=404, detail=f"Photo not found: {photo_id}")


def _safe_unlink(path: Path) -> None:
    """Delete a file if it exists, ignoring errors."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Theme endpoints
# ---------------------------------------------------------------------------

@router.get("/themes", summary="List photo themes", response_model=List[PhotoTheme])
def list_themes():
    return _read_json(THEMES_JSON)


@router.post(
    "/themes",
    summary="Create photo theme",
    response_model=PhotoTheme,
    status_code=201,
)
def create_theme(body: PhotoThemeCreate):
    themes = _read_json(THEMES_JSON)
    theme = {
        "id": str(uuid4()),
        "name": body.name,
        "compositionId": body.compositionId,
        "albumId": body.albumId,
        "baseThemeId": body.baseThemeId,
        "rotationIntervalS": body.rotationIntervalS,
    }
    themes.append(theme)
    _write_json(THEMES_JSON, themes)
    return theme


@router.put("/themes/{theme_id}", summary="Update photo theme", response_model=PhotoTheme)
def update_theme(theme_id: str, body: PhotoThemeUpdate):
    themes = _read_json(THEMES_JSON)
    for theme in themes:
        if theme.get("id") == theme_id:
            if body.name is not None:
                theme["name"] = body.name
            if body.compositionId is not None:
                theme["compositionId"] = body.compositionId
            if body.albumId is not None:
                theme["albumId"] = body.albumId
            if body.baseThemeId is not None:
                theme["baseThemeId"] = body.baseThemeId
            if body.rotationIntervalS is not None:
                theme["rotationIntervalS"] = body.rotationIntervalS
            _write_json(THEMES_JSON, themes)
            return theme
    raise HTTPException(status_code=404, detail=f"Theme not found: {theme_id}")


@router.delete("/themes/{theme_id}", summary="Delete photo theme")
def delete_theme(theme_id: str):
    themes = _read_json(THEMES_JSON)
    original_len = len(themes)
    themes = [t for t in themes if t.get("id") != theme_id]
    if len(themes) == original_len:
        raise HTTPException(status_code=404, detail=f"Theme not found: {theme_id}")
    _write_json(THEMES_JSON, themes)
    return {"ok": True}
