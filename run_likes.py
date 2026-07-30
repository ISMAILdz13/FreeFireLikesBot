#!/usr/bin/env python3
"""
Free Fire Like Bot — Termux Edition
====================================
Sends likes to any Free Fire UID using guest accounts.

Usage:
  python3 run_likes.py --target <UID> [--count 15] [--region ME]

Requirements:
  pip install pycryptodome pyyaml requests
"""

import sys, os, json, argparse, time, random
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "proto", "compiled"))

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from MajoRLoGinrEq_pb2 import MajorLogin
from MajoRLoGinrEs_pb2 import MajorLoginRes

# ======================== CONFIG ========================
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV  = b'6oyZDr22E3ychjM%'

REGION_CODES = {
    "ME": 7, "IND": 1, "BR": 2, "SG": 3, "TH": 4, "PH": 5,
    "VN": 6, "RU": 8, "US": 9, "PK": 10, "BD": 11, "ID": 1, "TW": 12,
}

HEADERS = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/octet-stream",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': "OB54",
}

GUESTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "guests.json")

# ======================== HELPERS ========================

def encode_varint(n):
    result = []
    while n > 0:
        b = n & 0x7F
        n >>= 7
        if n > 0: b |= 0x80
        result.append(b)
    return bytes(result)

def build_login(open_id, access_token):
    ml = MajorLogin()
    ml.event_time = str(datetime.now())[:-7]
    ml.game_name = "free fire"
    ml.platform_id = 2
    ml.client_version = "1.126.2"
    ml.client_version_code = "2024010012"
    ml.system_software = "Android OS 11 / API-30 (RQ3A.210805.001)"
    ml.system_hardware = "Handheld"
    ml.device_type = "Handheld"
    ml.telecom_operator = "Verizon"
    ml.network_operator_a = "Verizon"
    ml.network_type = "WIFI"
    ml.network_type_a = "WIFI"
    ml.screen_width = 1080
    ml.screen_height = 2400
    ml.screen_dpi = "440"
    ml.processor_details = "ARMv8"
    ml.cpu_type = 2
    ml.cpu_architecture = "64"
    ml.memory = 6144
    ml.gpu_renderer = "Adreno (TM) 650"
    ml.gpu_version = "OpenGL ES 3.2 V@1.50"
    ml.graphics_api = "OpenGLES3"
    ml.unique_device_id = f"Google|{random.randint(10**30, 10**31):x}"
    ml.client_ip = ""
    ml.language = "en"
    ml.open_id = open_id
    ml.open_id_type = "4"
    ml.login_open_id_type = 4
    ml.access_token = access_token
    ml.login_by = 3
    ml.platform_sdk_id = 2
    ml.origin_platform_type = "4"
    ml.primary_platform_type = "4"
    ml.memory_available.version = 55
    ml.memory_available.hidden_value = 81
    ml.external_storage_total = 128512
    ml.external_storage_available = random.randint(38000, 52000)
    ml.internal_storage_total = 110731
    ml.internal_storage_available = random.randint(18000, 32000)
    ml.game_disk_storage_total = 26628
    ml.game_disk_storage_available = random.randint(18000, 25000)
    ml.external_sdcard_total_storage = 119234
    ml.external_sdcard_avail_storage = random.randint(25000, 60000)
    ml.library_path = "/data/app/~~random/base.apk"
    ml.library_token = "hash|base.apk"
    ml.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    ml.supported_astc_bitset = 16383
    ml.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    ml.loading_time = random.randint(9000, 18000)
    ml.release_channel = "android"
    ml.channel_type = 3
    ml.reg_avatar = 1
    ml.if_push = 1
    ml.is_vpn = 0
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(ml.SerializeToString(), 16))

def send_like(jwt, target_uid, region="ME"):
    region_code = REGION_CODES.get(region.upper(), 7)
    uid_varint = encode_varint(target_uid)
    raw = bytes([0x08]) + uid_varint + bytes([0x10, region_code])
    enc = AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(raw, 16))
    resp = requests.post("https://clientbp.ggpolarbear.com/LikeProfile",
        headers={**HEADERS, "Authorization": f"Bearer {jwt}"},
        data=enc, timeout=15)
    return resp.status_code

# ======================== MAIN ========================

def main():
    p = argparse.ArgumentParser(description="Free Fire Like Bot")
    p.add_argument("--target", type=int, required=True, help="Target UID to send likes to")
    p.add_argument("--count", type=int, default=15, help="Total likes to send (default: 15)")
    p.add_argument("--region", type=str, default="ME", help="Region (default: ME)")
    p.add_argument("--per-guest", type=int, default=1, help="Max likes per guest (default: 1 — FF limits 1 like/account/24h)")
    args = p.parse_args()

    with open(GUESTS_FILE) as f:
        guests = json.load(f)

    print("=" * 50)
    print("  FREE FIRE LIKE BOT")
    print(f"  Target: {args.target}")
    print(f"  Likes: {args.count}")
    print(f"  Region: {args.region}")
    print(f"  Guests: {len(guests)}")
    print("=" * 50)

    likes_sent = 0
    likes_needed = args.count

    for i, guest in enumerate(guests):
        if likes_sent >= likes_needed:
            break

        uid = guest["uid"]
        print(f"\n[Guest {i+1}] UID: {uid}")

        # Refresh OAuth token (tokens expire)
        try:
            resp = requests.post(
                "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant",
                headers={"User-Agent": "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)",
                         "Content-Type": "application/json; charset=utf-8"},
                json={"client_id": 100067,
                      "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                      "client_type": 2, "password": guest["password"],
                      "response_type": "token", "uid": int(uid)},
                timeout=15, verify=False)
            odata = resp.json().get("data", resp.json())
            access_token = odata["access_token"]
            open_id = odata["open_id"]
            guest["access_token"] = access_token
            guest["open_id"] = open_id
            print(f"  OAuth refreshed ✓")
        except Exception as e:
            print(f"  OAuth FAIL: {e} — trying stored token")
            access_token = guest["access_token"]
            open_id = guest["open_id"]

        # MajorLogin
        payload = build_login(open_id, access_token)
        try:
            resp = requests.post("https://loginbp.ggpolarbear.com/MajorLogin",
                headers={**HEADERS, "Authorization": f"Bearer {guest['access_token']}"},
                data=payload, timeout=20)
            if resp.status_code != 200:
                print(f"  MajorLogin FAIL: HTTP {resp.status_code}")
                continue
            res = MajorLoginRes()
            res.ParseFromString(resp.content)
            jwt = res.token
            print(f"  JWT OK")
        except Exception as e:
            print(f"  MajorLogin error: {e}")
            continue

        # Send likes
        likes_this_guest = 0
        for j in range(args.per_guest):
            if likes_sent >= likes_needed:
                break
            try:
                status = send_like(jwt, args.target, args.region)
                if status == 200:
                    likes_sent += 1
                    likes_this_guest += 1
                    print(f"  [{likes_this_guest}/{args.per_guest}] Like sent! ({likes_sent}/{args.count} total)")
                else:
                    print(f"  [{j+1}/{args.per_guest}] FAIL: HTTP {status}")
                time.sleep(3)
            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(2)

    print(f"\n{'='*50}")
    print(f"  RESULT: {likes_sent}/{args.count} likes sent")
    print(f"  Target: UID {args.target}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
