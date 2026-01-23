import base64
import uuid
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import serializers


def is_base64_image(value: str) -> bool:
    return value.startswith("data:image/")


def is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def upload_base64_to_default_storage(base64_data: str) -> str:
    """
    Returns the public URL of the uploaded file
    """
    header, data = base64_data.split(";base64,")
    file_ext = header.split("/")[-1]

    if file_ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        raise serializers.ValidationError("Unsupported image format.")

    file_name = f"profile_pictures/{uuid.uuid4()}.{file_ext}"

    decoded_file = base64.b64decode(data)
    content = ContentFile(decoded_file, name=file_name)

    file_path = default_storage.save(file_name, content)

    return default_storage.url(file_path)
