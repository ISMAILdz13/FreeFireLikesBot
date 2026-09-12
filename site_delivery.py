#!/usr/bin/env python3
"""
Site delivery — sends likes through your own ff-like.noobs-api.top API.
The direct Garena HTTP method is dead (anti-bot sink, verified from
multiple IPs). Your site's delivery pipeline is the working route.

Setup (one time):
  1. In your site dashboard: API Keys -> create a key (starts with noobs_)
  2. Save it:   echo -n "noobs_XXXX" > data/site_api_key.txt
     (or)       export NOOBS_API_KEY=noobs_XXXX

Usage:
  python3 run_likes.py --site --target <UID> --count 100

Packages: 100 likes = 5 API credits, 120 = 6, 220 = 10.
The API response includes before/after like counts (real verification).
"""

import os
import sys
import json
import time
import requests

SITE = "https://ff-like.noobs-api.top"
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "site_api_key.txt")
PACKAGES = [100, 120, 220]          # likes per package
PICK = lambda n: max([p for p in PACKAGES if p <= max(n, 100)] or [100])


def load_api_key():
    key = os.environ.get("NOOBS_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        with open(KEY_FILE) as f:
            key = f.read().strip()
    if not key:
        print("=" * 60)
        print("  NO API KEY FOUND")
        print("  1. Create one in your site dashboard (API Keys section)")
        print(f"  2. Save it:  echo -n \"noobs_XXXX\" > {KEY_FILE}")
        print("=" * 60)
        sys.exit(1)
    return key


def ffinfo(uid, api_key):
    r = requests.post(f"{SITE}/api/ffinfo",
                      headers={"Authorization": f"Bearer {api_key}",
                               "Content-Type": "application/json"},
                      json={"uid": str(uid)}, timeout=60)
    return r.json()


def send_likes_via_site(uid, count=100, api_key=None):
    api_key = api_key or load_api_key()
    package = PICK(count)
    print(f"[site] target {uid} | package {package}")
    r = requests.post(f"{SITE}/api/fflike",
                      headers={"Authorization": f"Bearer {api_key}",
                               "Content-Type": "application/json"},
                      json={"uid": str(uid), "package": package}, timeout=300)
    try:
        data = r.json()
    except Exception:
        print(f"[site] HTTP {r.status_code}: {r.text[:200]}")
        return None
    return data


def site_flow(target, count):
    api_key = load_api_key()
    print("=" * 60)
    print("  SITE DELIVERY MODE (ff-like.noobs-api.top)")
    print(f"  target: {target}  count: {count}")
    print("=" * 60)

    info = ffinfo(target, api_key)
    if info.get("ok"):
        print(f"[site] player: {info.get('name', '?')} | likes now: {info.get('likes', info.get('before', '?'))}")

    print("[site] sending... (delivery takes up to a few minutes)")
    t0 = time.time()
    res = send_likes_via_site(target, count, api_key)
    if not res:
        return
    if res.get("ok"):
        print(f"[site] OK: {res.get('likesAddedFinal', '?')} likes added  "
              f"({res.get('before', '?')} -> {res.get('after', '?')}) in {time.time()-t0:.0f}s")
        print(f"[site] API credits left: {res.get('apiCreditsRemaining', '?')}")
    else:
        print(f"[site] FAILED: {res.get('message', json.dumps(res)[:200])}")
