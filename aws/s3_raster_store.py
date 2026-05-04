"""Stockage et gestion des rasters COG (Cloud Optimized GeoTIFF) sur AWS S3.

Usage:
    python aws/s3_raster_store.py --input data/vent_140m.tif --bucket mon-bucket-eolien
    python aws/s3_raster_store.py --list --bucket mon-bucket-eolien
"""
import argparse
import os
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

BUCKET = os.getenv("S3_BUCKET", "eolien-pipeline-data")
PREFIX = os.getenv("S3_PREFIX", "rasters/")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")


def to_cog(input_path: str, output_path: str | None = None) -> str:
    """Convertit un raster en COG avec GDAL."""
    inp = Path(input_path)
    out = output_path or str(inp.with_suffix(".cog.tif"))
    cmd = [
        "gdal_translate",
        "-of", "COG",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "OVERVIEWS=AUTO",
        "-co", "RESAMPLING=LANCZOS",
        "-a_srs", "EPSG:2154",
        input_path, out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gdal_translate COG failed: {result.stderr}")
    print(f"COG généré : {out}")
    return out


def upload_to_s3(local_path: str, s3_key: str | None = None, bucket: str = BUCKET) -> str:
    client = boto3.client("s3", region_name=AWS_REGION)
    key = s3_key or PREFIX + Path(local_path).name
    client.upload_file(
        local_path, bucket, key,
        ExtraArgs={"ContentType": "image/tiff", "ServerSideEncryption": "AES256"},
    )
    url = f"s3://{bucket}/{key}"
    print(f"Uploadé : {url}")
    return url


def list_rasters(bucket: str = BUCKET, prefix: str = PREFIX) -> list[dict]:
    client = boto3.client("s3", region_name=AWS_REGION)
    resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = resp.get("Contents", [])
    for obj in objects:
        size_mb = obj["Size"] / 1e6
        print(f"  {obj['Key']}  ({size_mb:.1f} MB)  {obj['LastModified']:%Y-%m-%d}")
    return objects


def download_from_s3(s3_key: str, dest_dir: str = "data/rasters", bucket: str = BUCKET) -> str:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    local_path = os.path.join(dest_dir, Path(s3_key).name)
    client = boto3.client("s3", region_name=AWS_REGION)
    client.download_file(bucket, s3_key, local_path)
    print(f"Téléchargé : {local_path}")
    return local_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestion rasters COG sur S3")
    parser.add_argument("--input", help="Fichier raster à convertir et uploader")
    parser.add_argument("--bucket", default=BUCKET)
    parser.add_argument("--list", action="store_true", help="Lister les rasters sur S3")
    parser.add_argument("--download", help="Clé S3 à télécharger")
    parser.add_argument("--no-cog", action="store_true", help="Upload sans conversion COG")
    args = parser.parse_args()

    if args.list:
        list_rasters(bucket=args.bucket)
    elif args.download:
        download_from_s3(args.download, bucket=args.bucket)
    elif args.input:
        local = args.input if args.no_cog else to_cog(args.input)
        upload_to_s3(local, bucket=args.bucket)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
