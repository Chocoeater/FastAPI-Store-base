from pathlib import Path
import uuid

from fastapi import UploadFile, HTTPException, status


BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024


async def save_product_image(file: UploadFile) -> str:
    """Сохраняет изображение товара и возвращает относительный url"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Только JPG, PNG или WebP")
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Слишком большой размер изображения")

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f"/media/products/{file_name}"

def remove_product_image(url: str | None) -> None:
    """Удаляет файл изображения, если он существует."""
    if not url:
        return
    relative_path = url.lstrip('/')
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()