import xml.etree.ElementTree as ET
from opencc import OpenCC

TS_PATH = "zh_TW.ts"
OUT_PATH = "zh_TW.ts"

cc = OpenCC("s2t")

parser = ET.XMLParser(encoding="utf-8")
tree = ET.parse(TS_PATH, parser=parser)
root = tree.getroot()

for context in root.findall("context"):
    for message in context.findall("message"):
        source = message.find("source")
        translation = message.find("translation")

        if source is None:
            continue

        src_text = source.text or ""

        if translation is None:
            translation = ET.SubElement(message, "translation")

        old_text = translation.text or ""
        if old_text.strip():
            continue

        translation.text = cc.convert(src_text)

        if "type" in translation.attrib:
            del translation.attrib["type"]

tree.write(OUT_PATH, encoding="utf-8", xml_declaration=True)
print("已完成：OpenCC 批量填充 zh_TW.ts")
