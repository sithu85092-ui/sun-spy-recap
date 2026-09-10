import os
from pathlib import Path

import boto3
from botocore.config import Config


B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET = os.getenv("B2_BUCKET")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")

if not all([
    B2_KEY_ID,
    B2_APPLICATION_KEY,
    B2_BUCKET,
    B2_ENDPOINT,
]):
    raise RuntimeError(
        "B2 environment variables are not fully configured."
    )


s3 = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-005",
)


def upload_file(local_path, object_key):
    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(
            f"File not found: {local_path}"
        )

    s3.upload_file(
        str(local_path),
        B2_BUCKET,
        object_key,
    )

    print(
        f"[B2 UPLOAD] {object_key}",
        flush=True,
    )

    return object_key


def download_file(object_key, local_path):
    local_path = Path(local_path)
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    s3.download_file(
        B2_BUCKET,
        object_key,
        str(local_path),
    )

    print(
        f"[B2 DOWNLOAD] {object_key}",
        flush=True,
    )

    return local_path


def create_download_url(
    object_key,
    expires=3600,
):
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": B2_BUCKET,
            "Key": object_key,
        },
        ExpiresIn=expires,
    )
