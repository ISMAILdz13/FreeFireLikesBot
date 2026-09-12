#!/usr/bin/env python3
"""
FreeFireLikesBot — Like Route Tester (run from Termux / your phone IP)
=======================================================================
Tests EVERY known like route from YOUR network and tells you exactly
which one (if any) delivers real likes.

Why this exists: some Garena clusters are geo-gated — they hang or drop
connections from cloud/datacenter IPs but answer normally from local
mobile/ISP IPs (like your phone). So a route that looks dead from a VPS
may work perfectly from Termux.

Usage (in the bot folder):
    pip install -r requirements.txt        # once
    python3 tools/test_like_routes.py [TARGET_UID]

Default target: 8954950459 (change it with the argument).
"""

import json
import os
import sys
import time
import base64

import requests
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src", "proto", "compiled"))

import run_likes as R                      # AES_KEY/AES_IV/HEADERS/build_login
from data_pb2 import AccountPersonalShowInfo
from MajoRLoGinrEs_pb2 import MajorLoginRes

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 8954950459
GUEST_UID = 6051811023                      # main guest giver account

LOGIN_HOSTS = [
    "loginbp.ggwhitehawk.com",             # newest cluster
    "loginbp.ggpolarbear.com",
    "loginbp.common.ggbluefox.com",        # geo-gated from cloud IPs
    "loginbp.ggbluefox.com",
    "loginbp.ggblueshark.com",             # legacy
]

CLIENTBP_HOSTS = [
    "clientbp.ggpolarbear.com",
    "clientbp.common.ggbluefox.com",       # geo-gated from cloud IPs
    "client.th.freefiremobile.com",        # official TH, geo-gated from cloud IPs
    "clientbp.ggbluefox.com",
    "clientbp.ggblueshark.com",            # DNS may be dead; kept for completeness
]

G = lambda s: "\033[32m" + s + "\033[0m"
RD = lambda s: "\033[31m" + s + "\033[0m"


def varint(n):
    out = []
    while n > 0:
        b = n & 0x7F
        n >>= 7
        if n > 0:
            b |= 0x80
        out.append(b)
    return bytes(out)


def guest_oauth(uid, password):
    r = requests.post(
        "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant",
        headers={"User-Agent": "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)",
                 "Content-Type": "application/json; charset=utf-8"},
        json={"client_id": 100067,
              "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
              "client_type": 2, "password": password,
              "response_type": "token", "uid": uid},
        timeout=20, verify=False)
    d = r.json()
    return d.get("data", d)


def major_login(host, open_id, access_token, timeout=20):
    """Returns (jwt, session_key, session_iv, url) or raises."""
    payload = R.build_login(open_id, access_token)
    r = requests.post(f"https://{host}/MajorLogin",
                      headers={**R.HEADERS, "Authorization": f"Bearer {access_token}"},
                      data=payload, timeout=timeout, verify=False)
    if r.status_code != 200 or len(r.content) < 30:
        raise RuntimeError(f"HTTP {r.status_code} ({len(r.content)}b)")
    res = MajorLoginRes()
    res.ParseFromString(r.content)
    if not res.token:
        raise RuntimeError("no token in response")
    key = res.key if isinstance(res.key, bytes) else base64.b64decode(res.key)
    iv = res.iv if isinstance(res.iv, bytes) else base64.b64decode(res.iv)
    return res.token, key, iv, res.url


def read_likes(host, jwt, timeout=15):
    msg = R.dev_generator()
    msg.saturn_ = TARGET
    msg.garena = 1
    body = AES.new(R.AES_KEY, AES.MODE_CBC, R.AES_IV).encrypt(pad(msg.SerializeToString(), 16))
    r = requests.post(f"https://{host}/GetPlayerPersonalShow",
                      headers={"User-Agent": "Dalvik/2.1.0", "Accept-Encoding": "gzip",
                               "Authorization": f"Bearer {jwt}",
                               "Content-Type": "application/x-www-form-urlencoded",
                               "X-Unity-Version": "2018.4.11f1", "X-GA": "v1 1",
                               "ReleaseVersion": "OB54"},
                      data=body, timeout=timeout, verify=False)
    if r.status_code != 200 or len(r.content) < 10:
        raise RuntimeError(f"HTTP {r.status_code} ({len(r.content)}b)")
    info = AccountPersonalShowInfo()
    info.ParseFromString(r.content)
    return info.basic_info.liked, info.basic_info.nickname


def send_like(host, jwt, key, iv, timeout=15):
    raw = bytes([0x08]) + varint(TARGET) + bytes([0x10, 0x07])
    body = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(raw, 16))
    r = requests.post(f"https://{host}/LikeProfile",
                      headers={**R.HEADERS, "Authorization": f"Bearer {jwt}"},
                      data=body, timeout=timeout, verify=False)
    return r.status_code, len(r.content)


def main():
    print("=" * 64)
    print("  LIKE ROUTE TESTER - running from YOUR network")
    print(f"  target UID: {TARGET}")
    print("=" * 64)

    guests_path = os.path.join(ROOT, "data", "guests.json")
    with open(guests_path) as f:
        guests = json.load(f)
    guest = next((g for g in guests if int(g.get("uid", 0)) == GUEST_UID), guests[0])
    print(f"\n[1] giver guest: {guest.get('uid')}")

    print("[2] OAuth token...", end=" ", flush=True)
    odata = guest_oauth(guest["uid"], guest["password"])
    if not odata.get("access_token"):
        print(RD("FAILED - guest account dead?"))
        return
    print(G("OK"))

    print("[3] MajorLogin - trying every login cluster:")
    jwt = skey = siv = None
    for host in LOGIN_HOSTS:
        try:
            t0 = time.time()
            jwt, skey, siv, url = major_login(host, odata["open_id"], odata["access_token"])
            print(f"    {G(host + ' OK')}  ({time.time()-t0:.1f}s, url={url})")
            break
        except Exception as e:
            print(f"    {RD(host + ' FAIL')}  ({e})")
    if not jwt:
        print(RD("\nNo login cluster reachable - nothing else can be tested."))
        return

    print("[4] reading target likes (before)...", end=" ", flush=True)
    before = nick = None
    for host in CLIENTBP_HOSTS:
        try:
            before, nick = read_likes(host, jwt)
            print(f"{G('OK')} via {host} - {nick!r} has {before} likes")
            break
        except Exception as e:
            print(f"{RD('fail')} ({host}: {str(e)[:40]})")
            print("      trying next...", end=" ", flush=True)
    if before is None:
        print(RD("\nCould not read target - check UID / connection."))
        return

    print("\n[5] sending 1 like via every route (static key + session key):")
    results = []
    for host in CLIENTBP_HOSTS:
        for kname, key, iv in (("static", R.AES_KEY, R.AES_IV), ("session", skey, siv)):
            try:
                code, size = send_like(host, jwt, key, iv)
                results.append((host, kname, code, size))
                print(f"    {host:36} {kname:7} -> HTTP {code} ({size}b)")
            except Exception as e:
                results.append((host, kname, "ERR", str(e)[:40]))
                print(f"    {host:36} {kname:7} -> {RD('UNREACHABLE/HANG')} ({str(e)[:40]})")

    print("\n[6] re-reading likes after (waiting 10s)...", end=" ", flush=True)
    time.sleep(10)
    after = None
    for host in CLIENTBP_HOSTS:
        try:
            after, _ = read_likes(host, jwt)
            print(f"{after} {G('(read via ' + host + ')')}")
            break
        except Exception:
            continue
    if after is None:
        print(RD("could not re-read"))
        return

    print("\n" + "=" * 64)
    if after > before:
        print(G(f"  VERDICT: LIKES ARE COUNTING FROM YOUR NETWORK!  {before} -> {after}"))
        print("    Send this whole output back to the agent - the bot will be")
        print("    pointed at the working route permanently.")
    else:
        print(RD(f"  VERDICT: still not counting ({before} -> {after})."))
        print("    Direct like delivery is blocked by Garena even from your IP.")
        print("    Send this whole output back to the agent.")
    print("=" * 64)


if __name__ == "__main__":
    main()
