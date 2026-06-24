#!/bin/python3
import argparse
import json
import os
import sys
import zoneinfo
from datetime import datetime
from urllib.request import urlopen, Request

def main():
    parser = argparse.ArgumentParser(
        prog='uploader.py',
        description='Upload SBOMs to PRISMA',
    )
    parser.add_argument("filename")
    parser.add_argument("--server", required=True)
    args = parser.parse_args()
    tz = zoneinfo.ZoneInfo("Europe/Berlin")

    with open(args.filename, "r") as f:
        sbom = json.load(f)

    if "GITHUB_ACTION" in os.environ:
        is_rolling = os.environ.get("GITHUB_REF_TYPE") != "tag"
        if is_rolling:
            version_name = os.environ.get("GITHUB_REF", "").removesuffix("refs/heads/")
        else:
            version_name = os.environ.get("GITHUB_REF", "").removesuffix("refs/tags/")
    elif "CI_JOB_ID" in os.environ:
        is_rolling = not os.environ.get("CI_COMMIT_TAG")
        if is_rolling:
            version_name = os.environ.get("CI_COMMIT_BRANCH")
        else:
            version_name = os.environ.get("CI_COMMIT_TAG")
    else:
        raise Exception("No CI variables detected")

    payload = {
        "version_name": version_name,
        "version_code": None,  # TODO support for android
        "release_date": datetime.now(tz).strftime("%Y-%m-%d"),
        "is_current": False,  # TODO figure this out
        "is_public": not is_rolling and not any(s in version_name for s in ("beta", "alpha", "experimental", "rc")),
        "is_rolling": is_rolling,
        "sbom": sbom,
    }

    httprequest = Request(
        args.server + "/api/products/v1/submit-release",
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Token " + os.environ["PRISMA_UPLOAD_TOKEN"],
        },
    )

    with urlopen(httprequest) as response:
        print(response.read().decode())
        if response.status not in (200, 201, 204):
            sys.exit(1)

