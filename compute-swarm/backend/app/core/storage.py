from __future__ import annotations

from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import settings

_s3_client = None


class StorageError(Exception):
    """Raised when a storage operation fails."""

    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


def _get_s3_client() -> boto3.client:
    global _s3_client
    if _s3_client is None:
        protocol = "https" if settings.minio_use_ssl else "http"
        endpoint_url = f"{protocol}://{settings.minio_endpoint}"
        try:
            _s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
        except Exception as exc:
            raise StorageError(
                "Failed to initialize MinIO/S3 client. Check storage configuration.",
                original=exc,
            ) from exc
    return _s3_client


def get_presigned_upload_url(object_name: str, expiry: int = 900) -> str:
    """Generate a presigned URL for uploading an object to MinIO."""
    try:
        client = _get_s3_client()
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.minio_bucket, "Key": object_name},
            ExpiresIn=expiry,
        )
        return url
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(
            f"Failed to generate presigned upload URL: {exc}", original=exc
        ) from exc
    except Exception as exc:
        raise StorageError(
            "Storage service is unavailable. Please try again later.", original=exc
        ) from exc


def get_presigned_download_url(object_name: str, expiry: int = 900) -> str:
    """Generate a presigned URL for downloading an object from MinIO."""
    try:
        client = _get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": object_name},
            ExpiresIn=expiry,
        )
        return url
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(
            f"Failed to generate presigned download URL: {exc}", original=exc
        ) from exc
    except Exception as exc:
        raise StorageError(
            "Storage service is unavailable. Please try again later.", original=exc
        ) from exc


def check_minio_health() -> bool:
    """Check if MinIO is reachable by listing buckets."""
    try:
        client = _get_s3_client()
        client.list_buckets()
        return True
    except Exception:
        return False


def upload_fileobj(key: str, fileobj: BinaryIO) -> None:
    """Upload a file-like object to MinIO."""
    try:
        client = _get_s3_client()
        client.upload_fileobj(fileobj, settings.minio_bucket, key)
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(
            f"Failed to upload file to MinIO: {exc}", original=exc
        ) from exc
    except Exception as exc:
        raise StorageError(
            "Storage service is unavailable. Please try again later.", original=exc
        ) from exc


def download_fileobj(key: str) -> bytes:
    """Download an object from MinIO and return its contents as bytes."""
    import io

    try:
        client = _get_s3_client()
        buffer = io.BytesIO()
        client.download_fileobj(settings.minio_bucket, key, buffer)
        buffer.seek(0)
        return buffer.read()
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(
            f"Failed to download file from MinIO: {exc}", original=exc
        ) from exc
    except Exception as exc:
        raise StorageError(
            "Storage service is unavailable. Please try again later.", original=exc
        ) from exc
