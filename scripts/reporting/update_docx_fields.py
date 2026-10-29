#!/usr/bin/env python3
"""Cap nhat muc luc, danh sach hinh/bang va truong SEQ cua mot tep .docx bang LibreOffice (UNO), roi luu .docx va .pdf.

    python scripts/reporting/update_docx_fields.py <vao.docx> <ra.docx> <ra.pdf> [--port 2002]

Can LibreOffice (soffice) va module Python `uno` (python3-uno). Chay headless, khong can giao dien.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("docx_out", type=Path)
    ap.add_argument("pdf_out", type=Path)
    ap.add_argument("--port", type=int, default=2002)
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()
    if not a.src.is_file():
        raise SystemExit(f"khong thay {a.src}")
    try:
        import uno
        from com.sun.star.beans import PropertyValue
    except ImportError:
        raise SystemExit("thieu module uno (cai python3-uno / LibreOffice)")

    def pv(n, v):
        p = PropertyValue(); p.Name = n; p.Value = v; return p

    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
                             f"--accept=socket,host=localhost,port={a.port};urp;"])
    ctx = None
    for _ in range(a.timeout):
        try:
            local = uno.getComponentContext()
            r = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            ctx = r.resolve(f"uno:socket,host=localhost,port={a.port};urp;StarOffice.ComponentContext"); break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    if ctx is None:
        proc.kill(); raise SystemExit("khong ket noi duoc LibreOffice")
    desk = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    try:
        doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(str(a.src.resolve())), "_blank", 0, (pv("Hidden", True),))
        doc.getTextFields().refresh()
        for _ in range(2):                       # lan 2: so trang trong muc luc on dinh sau khi muc luc dai ra
            idx = doc.getDocumentIndexes()
            for i in range(idx.getCount()):
                idx.getByIndex(i).update()
            doc.getTextFields().refresh()
        n = doc.getDocumentIndexes().getCount()
        a.docx_out.parent.mkdir(parents=True, exist_ok=True); a.pdf_out.parent.mkdir(parents=True, exist_ok=True)
        doc.storeToURL(uno.systemPathToFileUrl(str(a.docx_out.resolve())), (pv("FilterName", "MS Word 2007 XML"),))
        doc.storeToURL(uno.systemPathToFileUrl(str(a.pdf_out.resolve())), (pv("FilterName", "writer_pdf_Export"),))
        doc.close(True)
        print(f"cap nhat {n} muc luc/danh sach -> {a.docx_out}, {a.pdf_out}")
    finally:
        try:
            desk.terminate()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
