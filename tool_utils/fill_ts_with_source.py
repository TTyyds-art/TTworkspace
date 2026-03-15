import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def fill_ts_with_source(ts_path: Path) -> int:
    tree = ET.parse(ts_path)
    root = tree.getroot()
    changed = 0

    for msg in root.findall(".//message"):
        source = msg.find("source")
        if source is None:
            continue
        src_text = source.text or ""
        translation = msg.find("translation")
        if translation is None:
            translation = ET.SubElement(msg, "translation")
        old_text = (translation.text or "").strip()
        if old_text:
            continue
        translation.text = src_text
        if "type" in translation.attrib:
            del translation.attrib["type"]
        changed += 1

    tree.write(ts_path, encoding="utf-8", xml_declaration=True)
    return changed


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: fill_ts_with_source.py <path-to-ts>")
        return 2
    ts_path = Path(sys.argv[1])
    if not ts_path.exists():
        print(f"File not found: {ts_path}")
        return 1
    changed = fill_ts_with_source(ts_path)
    print(f"filled {changed} translations in {ts_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
