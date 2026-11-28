#!/usr/bin/env python3
"""Nap khoa Kaggle cho GitHub Actions tu secret, KHONG in gia tri (ADR-0016 muc 5).

Nhan mot trong ba dang:
- K_TOKEN = API token moi (chuoi, vd. KGAT_...) -> ~/.kaggle/access_token (kaggle>=2 doc tep nay);
- K_TOKEN = noi dung kaggle.json ({"username": ..., "key": ...}) -> ~/.kaggle/kaggle.json;
- K_USER + K_KEY (cap cu) -> ~/.kaggle/kaggle.json.
Tep ghi quyen 600. Gia tri bi che trong log bang ::add-mask::.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def write_creds(home: Path, token: str, user: str, key: str) -> str:
    d = home / ".kaggle"
    d.mkdir(parents=True, exist_ok=True)
    token = token.strip()
    if token.startswith("{"):
        try:
            j = json.loads(token)
            user, key = j["username"], j["key"]
        except (ValueError, KeyError) as e:
            raise SystemExit(f"secret KAGGLE co dang JSON nhung khong doc duoc username/key ({type(e).__name__})")
        token = ""
    if token:
        p = d / "access_token"; p.write_text(token, encoding="utf-8"); p.chmod(0o600)
        return "access_token"
    if user and key:
        p = d / "kaggle.json"; p.write_text(json.dumps({"username": user.strip(), "key": key.strip()}), encoding="utf-8"); p.chmod(0o600)
        return "kaggle.json"
    raise SystemExit("khong co secret KAGGLE (hoac KAGGLE_USERNAME + KAGGLE_KEY) trong GitHub Secrets")


def main() -> int:
    token, user, key = os.environ.get("K_TOKEN", ""), os.environ.get("K_USER", ""), os.environ.get("K_KEY", "")
    raw = token.strip()
    vals = [raw, key]
    if raw.startswith("{"):
        try:
            vals.append(json.loads(raw).get("key", ""))
        except ValueError:
            pass
    for v in vals:
        if v:
            print(f"::add-mask::{v}")
    kind = write_creds(Path.home(), token, user, key)
    print(f"Kaggle credentials: {kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
