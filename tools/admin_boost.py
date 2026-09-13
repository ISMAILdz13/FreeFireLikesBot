#!/usr/bin/env python3
"""
admin_boost.py — one-shot booster for YOUR OWN ff-like.noobs-api.top account.

Run this on your laptop after logging in to the site once with Google.
It will:
  1. upgrade your account to ADMIN (needs the admin password)
  2. set your credits to 100,000
  3. create + redeem a 15,000 coupon -> totalTopupBdt 15,000 -> PRIME 15 (max)

HOW TO GET YOUR JWT (one time):
  - open https://ff-like.noobs-api.top and log in with Google
  - press F12 -> Console tab -> type:  localStorage.getItem('ff_jwt_token')
  - copy the eyJ... string (with quotes is fine, it gets stripped)

Usage:
  python3 tools/admin_boost.py --jwt "eyJ..." [--credits 100000] [--prime 15000]

NOTE: never commit your JWT or the admin password anywhere public.
"""
import argparse
import json
import requests

SITE = "https://ff-like.noobs-api.top"


def api(method, path, jwt, body=None, params=None):
    r = requests.request(method, f"{SITE}{path}",
                         headers={"Authorization": f"Bearer {jwt}",
                                  "Content-Type": "application/json"},
                         json=body, params=params, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"error": r.text[:200]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jwt", required=True, help="your ff_jwt_token from localStorage")
    p.add_argument("--credits", type=int, default=100000)
    p.add_argument("--prime", type=int, default=15000, help="coupon amount = totalTopupBdt (15000 = Prime 15)")
    a = p.parse_args()

    jwt = a.jwt.strip().strip('"').strip("'")

    # current state
    _, me = api("GET", "/api/user/profile", jwt)
    print(f"[1] logged in as: {me.get('profile', {}).get('email', '?')} "
          f"credits={me.get('profile', {}).get('credits')} "
          f"prime={me.get('profile', {}).get('primeLevel')}")

    # become admin
    pw = input("[2] admin password: ").strip()
    code, res = api("POST", "/api/user/admin-login", jwt, {"password": pw})
    if code != 200:
        print("    admin login failed:", res); return
    print("    admin access granted ✓")

    # find my own user record (need googleId)
    email = me.get("profile", {}).get("email", "")
    code, found = api("GET", "/api/user/all", jwt, params={"page": 1, "limit": 20, "search": email})
    users = found.get("users", [])
    mine = next((u for u in users if u.get("email") == email), None)
    if not mine:
        print("    could not find my user record:", found.get("error")); return
    gid = mine.get("googleId")
    print(f"[3] my googleId: {gid}")

    # set credits
    code, res = api("PUT", f"/api/user/admin/{gid}", jwt,
                    {"displayName": mine.get("displayName") or "Me",
                     "credits": a.credits, "role": "admin"})
    if code != 200:
        print("    credits update failed:", res); return
    print(f"    credits set to {a.credits} ✓")

    # prime coupon: create + redeem
    code, res = api("POST", "/api/topup/admin/coupons", jwt,
                    {"code": f"PRIME{a.prime}", "amount": a.prime})
    if code not in (200, 201):
        # maybe it already exists from a previous run - try redeeming anyway
        print("    coupon create said:", res.get("message") or res.get("error"), "- trying redeem anyway")
    else:
        print(f"    coupon PRIME{a.prime} created ✓")

    code, res = api("POST", "/api/topup/redeem-coupon", jwt, {"couponCode": f"PRIME{a.prime}"})
    if code == 200:
        print(f"    redeemed ✓  credits={res.get('credits')}  "
              f"totalTopupBdt={res.get('totalTopupBdt')}  primeLevel={res.get('primeLevel')}  "
              f"active={res.get('isActive')}")
    else:
        print("    redeem failed:", res.get("message") or res)

    # final state
    _, me = api("GET", "/api/user/profile", jwt)
    me = me.get("profile", {})
    print(f"[4] FINAL: credits={me.get('credits')}  primeLevel={me.get('primeLevel')}  "
          f"totalTopupBdt={me.get('totalTopupBdt')}")
    print("done. slots & api keys & likes are all unlocked now 🔥")


if __name__ == "__main__":
    main()
