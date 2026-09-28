#!/usr/bin/env python3
"""Render PDF fixtures to PNG and OCR the rendered pixels for audit evidence."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import fitz


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "work" / "evidence" / "pdf-render"
OUT.mkdir(parents=True, exist_ok=True)


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def main() -> None:
    rows = []
    for src in sorted(HERE.rglob("*.pdf")):
        doc = fitz.open(src)
        extracted = []
        ocr = []
        for pno, page in enumerate(doc):
            extracted.append(page.get_text("text", clip=fitz.INFINITE_RECT()))
            png = OUT / f"{safe(src.relative_to(HERE).as_posix())}.p{pno + 1}.png"
            page.get_pixmap(dpi=200, alpha=False, colorspace=fitz.csRGB).save(png)
            r = subprocess.run(["tesseract", str(png), "stdout", "-l", "eng+ron+pol"],
                               capture_output=True, text=True, timeout=120)
            ocr.append(r.stdout)
        doc.close()
        base = OUT / safe(src.relative_to(HERE).as_posix())
        base.with_suffix(base.suffix + ".extracted.txt").write_text("\n\n".join(extracted), encoding="utf-8")
        base.with_suffix(base.suffix + ".ocr.txt").write_text("\n\n".join(ocr), encoding="utf-8")
        rows.append({"file": str(src.relative_to(HERE)), "pages": len(extracted),
                     "extracted_chars": sum(map(len, extracted)), "ocr_chars": sum(map(len, ocr))})
    (OUT / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    for row in rows:
        print(f"{row['file']:70} pages={row['pages']} extracted={row['extracted_chars']} ocr={row['ocr_chars']}")


if __name__ == "__main__":
    main()
