#!/usr/bin/env python3
"""Record namespace-independent DOCX text and concealment geometry."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from lxml import etree


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "work" / "evidence" / "docx-package-evidence.json"


def local(el, name):
    return el.xpath(f".//*[local-name()='{name}']")


def main() -> None:
    rows = []
    for path in sorted(HERE.glob("*.docx")):
        with zipfile.ZipFile(path) as z:
            raw = z.read("word/document.xml")
            root = etree.fromstring(raw)
            texts = [e.text or "" for e in local(root, "t")]
            positions = [e.get(next((k for k in e.attrib if k.endswith("}val")), ""))
                         for e in local(root, "position")]
            frames = []
            for e in local(root, "framePr"):
                frames.append({etree.QName(k).localname: v for k, v in e.attrib.items()})
            floating_tables = []
            for e in local(root, "tblpPr"):
                floating_tables.append({etree.QName(k).localname: v for k, v in e.attrib.items()})
            vanishes = len(local(root, "vanish"))
            embedded = [n for n in z.namelist() if "/embeddings/" in n]
            embedded_strings = {}
            for n in embedded:
                data = z.read(n)
                embedded_strings[n] = [s.decode("utf-8", "replace") for s in re.findall(rb"[ -~]{20,}", data)]
            numbering_labels = []
            if "word/numbering.xml" in z.namelist():
                nr = etree.fromstring(z.read("word/numbering.xml"))
                for e in nr.xpath(".//*[local-name()='lvlText']"):
                    value = next((v for k, v in e.attrib.items() if k.endswith("}val")), "")
                    if value:
                        numbering_labels.append(value)
            custom_xml = {}
            for n in z.namelist():
                if n.startswith("customXml/") and n.endswith(".xml"):
                    cr = etree.fromstring(z.read(n))
                    text = " ".join(t.strip() for t in cr.itertext() if t.strip())
                    if text:
                        custom_xml[n] = text
        rows.append({
            "file": path.name,
            "document_namespace": etree.QName(root).namespace,
            "text": "".join(texts),
            "vanish_elements": vanishes,
            "position_values_half_points": positions,
            "frame_properties_twips": frames,
            "floating_table_properties_twips": floating_tables,
            "numbering_labels": numbering_labels,
            "custom_xml_text": custom_xml,
            "embedded_parts": embedded,
            "embedded_ascii": embedded_strings,
        })
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
