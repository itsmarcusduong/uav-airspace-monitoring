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
import re
import sys
from pathlib import Path


TOKEN_RE = re.compile(r"KGAT_[A-Za-z0-9_\-]+")


def shape(s: str) -> str:
    """Mo ta hinh dang secret de chan doan, KHONG lo gia tri: do dai, so dong, co KGAT_/JSON/'=' hay khong."""
    yn = {True: "co", False: "khong"}
    ws = bool(re.search(r"\s", s.strip()))
    return (f"dai {len(s)}, {len(s.splitlines())} dong, KGAT_ {yn['KGAT_' in s]}, JSON {yn['{' in s]}, "
            f"dau = {yn['=' in s]}, khoang trang {yn[ws]}")


def normalize_token(raw: str) -> str:
    """Lay dung token tu chuoi da dan (vd. 'KAGGLE_API_TOKEN=KGAT_...', co ngoac kep hay xuong dong). Rong neu la JSON."""
    s = raw.strip().strip('"\'')
    if s.startswith("{"):
        return s
    m = TOKEN_RE.search(s)
    if m:
        return m.group(0)
    s = s.split("=", 1)[-1].strip().strip('"\'')
    if re.search(r"\s", s):
        raise SystemExit(f"secret KAGGLE khong phai token hop le ({shape(raw)})")
    return s


def write_creds(home: Path, token: str, user: str, key: str) -> str:
    d = home / ".kaggle"
    d.mkdir(parents=True, exist_ok=True)
    token = normalize_token(token) if token.strip() else ""
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
    if raw:
        print(f"secret KAGGLE: {shape(token)}")
    kind = write_creds(Path.home(), token, user, key)
    print(f"Kaggle credentials: {kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
