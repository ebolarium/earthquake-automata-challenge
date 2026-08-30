"""S3-compatible object storage configuration and integrity probes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import uuid


SAFE_PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@dataclass(frozen=True)
class ObjectStorageConfig:
    endpoint_url: str
    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    prefix: str

    @classmethod
    def from_environment(cls) -> "ObjectStorageConfig":
        values = {
            "endpoint_url": os.environ.get("S3_ENDPOINT_URL", ""),
            "bucket": os.environ.get("S3_BUCKET", ""),
            "region": os.environ.get("S3_REGION", "us-east-1"),
            "access_key_id": os.environ.get("S3_ACCESS_KEY_ID", ""),
            "secret_access_key": os.environ.get("S3_SECRET_ACCESS_KEY", ""),
            "prefix": os.environ.get("S3_PREFIX", "prospective/v1").strip("/"),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"missing object storage settings: {', '.join(missing)}")
        if not values["endpoint_url"].startswith("https://"):
            raise ValueError("S3_ENDPOINT_URL must use https")
        if not SAFE_PREFIX.fullmatch(values["prefix"]) or ".." in values["prefix"].split("/"):
            raise ValueError("invalid S3_PREFIX")
        return cls(**values)

    def client(self):
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )


def object_key(config: ObjectStorageConfig, suffix: str) -> str:
    cleaned = suffix.strip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise ValueError("invalid object suffix")
    return f"{config.prefix}/{cleaned}"


def storage_health(config: ObjectStorageConfig, client=None) -> tuple[bool, str | None]:
    try:
        active = client or config.client()
        active.list_objects_v2(Bucket=config.bucket, Prefix=f"{config.prefix}/", MaxKeys=1)
    except Exception:
        return False, "object_storage_unavailable"
    return True, None


def put_verified_bytes(
    config: ObjectStorageConfig,
    key: str,
    payload: bytes,
    content_type: str,
    client=None,
) -> str:
    if not key.startswith(f"{config.prefix}/"):
        raise ValueError("object key is outside configured prefix")
    active = client or config.client()
    checksum = hashlib.sha256(payload).hexdigest()
    active.put_object(
        Bucket=config.bucket,
        Key=key,
        Body=payload,
        ContentType=content_type,
        Metadata={"sha256": checksum},
    )
    metadata = active.head_object(Bucket=config.bucket, Key=key)
    if int(metadata["ContentLength"]) != len(payload) or metadata.get("Metadata", {}).get("sha256") != checksum:
        raise RuntimeError("uploaded object metadata disagrees")
    return checksum


def write_read_delete_probe(config: ObjectStorageConfig, client=None) -> dict:
    active = client or config.client()
    probe_id = uuid.uuid4().hex
    key = object_key(config, f"_system/probes/{probe_id}.json")
    payload = json.dumps(
        {
            "probe_id": probe_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "prospective_object_storage_connectivity",
        },
        sort_keys=True,
    ).encode("utf-8")
    checksum = hashlib.sha256(payload).hexdigest()
    uploaded = False
    try:
        active.put_object(
            Bucket=config.bucket,
            Key=key,
            Body=payload,
            ContentType="application/json",
            Metadata={"sha256": checksum},
        )
        uploaded = True
        response = active.get_object(Bucket=config.bucket, Key=key)
        downloaded = response["Body"].read()
        if downloaded != payload or hashlib.sha256(downloaded).hexdigest() != checksum:
            raise RuntimeError("object storage probe checksum mismatch")
    finally:
        if uploaded:
            active.delete_object(Bucket=config.bucket, Key=key)
    return {"status": "ok", "bucket": config.bucket, "prefix": config.prefix, "sha256": checksum}
