import argparse
import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


SYSTEM_PROMPT = (
    "You are a professional translator. Translate Simplified Chinese UI text to natural English. "
    "Keep placeholders like %s, %1, {name}, {0} unchanged. Do not add extra punctuation. "
    "Return only the translated text."
)


def _call_kimi(base_url: str, model: str, api_key: str, text: str, timeout: int, max_retries: int) -> str:
    # 兼容传入完整端点或 base_url
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 1,
    }
    for attempt in range(max_retries + 1):
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
        if resp.status_code == 429:
            wait_s = min(10, 1 + attempt * 2)
            print(f"[kimi] 429 overloaded, retry in {wait_s}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_s)
            continue
        if resp.status_code >= 400:
            print(f"[kimi] http={resp.status_code} url={url}")
            try:
                print(f"[kimi] body={resp.text[:1000]}")
            except Exception:
                pass
            resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    raise RuntimeError("Kimi API overloaded, retries exhausted")


def translate_ts(ts_path: Path, base_url: str, model: str, api_key: str, sleep_s: float, timeout: int, max_retries: int) -> int:
    tree = ET.parse(ts_path)
    root = tree.getroot()
    changed = 0

    for msg in root.findall(".//message"):
        source = msg.find("source")
        if source is None:
            continue
        src_text = (source.text or "").strip()
        if not src_text:
            continue
        translation = msg.find("translation")
        if translation is None:
            translation = ET.SubElement(msg, "translation")
        old_text = (translation.text or "").strip()
        # 仅跳过已人工翻译（与源文不同）
        if old_text and old_text != src_text:
            continue

        translated = _call_kimi(base_url, model, api_key, src_text, timeout, max_retries)
        translation.text = translated
        if "type" in translation.attrib:
            del translation.attrib["type"]
        changed += 1

        if sleep_s > 0:
            time.sleep(sleep_s)

    tree.write(ts_path, encoding="utf-8", xml_declaration=True)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ts_path", help="Path to .ts file")
    parser.add_argument("--base-url", default=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"))
    parser.add_argument("--model", default=os.environ.get("KIMI_MODEL", "kimi-k2-5"))
    parser.add_argument("--api-key", default=os.environ.get("KIMI_API_KEY"))
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between calls")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout seconds")
    parser.add_argument("--retries", type=int, default=5, help="Max retries for 429")
    args = parser.parse_args()

    if not args.api_key:
        print("Missing API key. Set KIMI_API_KEY env or pass --api-key.")
        return 2

    ts_path = Path(args.ts_path)
    if not ts_path.exists():
        print(f"File not found: {ts_path}")
        return 1

    changed = translate_ts(ts_path, args.base_url, args.model, args.api_key, args.sleep, args.timeout, args.retries)
    print(f"translated {changed} entries in {ts_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
