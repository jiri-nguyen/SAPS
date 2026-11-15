"""SAPS-34 spike: SeaweedFS S3 API — put/get/delete, presigned GET, persistence across restart and recreate."""
import hashlib
import os
import subprocess
import sys
import time
import urllib.request

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

HERE = os.path.dirname(os.path.abspath(__file__))
s3 = boto3.client("s3", endpoint_url="http://localhost:58333", aws_access_key_id="local-test-access",
                  aws_secret_access_key="local-test-secret", region_name="us-east-1",
                  config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
BUCKET = "invoices"
results = []


def record(name, ok, detail):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def wait_s3(timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s3.list_buckets()
            return True
        except Exception:
            time.sleep(1)
    return False


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=HERE, check=True, capture_output=True)


def get(key) -> bytes:
    return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()


wait_s3()
try:
    s3.create_bucket(Bucket=BUCKET)
except ClientError as e:
    if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        raise

pdf = b"%PDF-1.7\n" + os.urandom(300_000)   # 300 KB fake invoice
key = f"invoices/{'0' * 8}-spike/{sha(pdf)}"

# 3a put / get / delete
s3.put_object(Bucket=BUCKET, Key=key, Body=pdf, ContentType="application/pdf")
body = get(key)
head = s3.head_object(Bucket=BUCKET, Key=key)
s3.delete_object(Bucket=BUCKET, Key=key)
try:
    get(key)
    gone = False
except ClientError as e:
    gone = e.response["Error"]["Code"] in ("NoSuchKey", "404")
record("3a put / get / delete", sha(body) == sha(pdf) and gone and head["ContentType"] == "application/pdf",
       f"300 KB object round-trip hash equal={sha(body) == sha(pdf)}, content-type kept={head['ContentType']}, "
       f"after delete -> NoSuchKey={gone}")

# 3b presigned GET used like a browser (plain HTTP, no credentials)
s3.put_object(Bucket=BUCKET, Key=key, Body=pdf, ContentType="application/pdf")
url = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=60)
with urllib.request.urlopen(url) as r:
    via_url = r.read()
    ctype = r.headers.get("Content-Type")
tampered = url.replace("X-Amz-Signature=", "X-Amz-Signature=0")
try:
    urllib.request.urlopen(tampered)
    rejected = False
except urllib.error.HTTPError as e:
    rejected = e.code == 403
short = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=2)
time.sleep(4)
try:
    urllib.request.urlopen(short)
    expired = False
except urllib.error.HTTPError as e:
    expired = e.code == 403
record("3b presigned GET URL", sha(via_url) == sha(pdf) and rejected and expired,
       f"download without credentials OK={sha(via_url) == sha(pdf)} (Content-Type {ctype}); "
       f"tampered signature -> 403={rejected}; expired URL (2 s) -> 403={expired}")

# 3c persistence: container restart, then down/up (named volume kept)
compose("restart", "seaweedfs")
ok_restart = wait_s3() and sha(get(key)) == sha(pdf)
compose("down")
compose("up", "-d")
ok_recreate = wait_s3(90) and sha(get(key)) == sha(pdf)
record("3c files survive restart and container re-creation", ok_restart and ok_recreate,
       f"after 'docker compose restart'={ok_restart}; after 'down' + 'up' (volume kept)={ok_recreate}")

sys.exit(0 if all(ok for _, ok in results) else 1)
