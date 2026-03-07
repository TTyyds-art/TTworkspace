# tea_save_server.py
# 功能：接收前端 POST 的 JSON 文本 + images.xlsx 的base64，写入指定路径
# 启动：python tea_save_server.py
# 访问：前端 fetch http://127.0.0.1:3210/save

from flask import Flask, request, jsonify
import os
import base64

app = Flask(__name__)

JSON_PATH = r"F:\Lyq\miketee4(1080)_4.0.10\menu_xlsx\tea_drinks_menu.json"
IMAGE_XLSX_PATH = r"F:\Lyq\miketee4(1080)_4.0.10\tee_image_xlsx\images.xlsx"

def ensure_dir(file_path: str):
    folder = os.path.dirname(file_path)
    os.makedirs(folder, exist_ok=True)

@app.after_request
def add_cors_headers(resp):
    # 允许本地HTML跨域调用
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/save", methods=["POST", "OPTIONS"])
def save():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    json_text = data.get("jsonText", "")
    images_xlsx_base64 = data.get("imagesXlsxBase64", "")

    if not isinstance(json_text, str) or not json_text.strip():
        return jsonify({"ok": False, "error": "jsonText is empty"}), 400

    if not isinstance(images_xlsx_base64, str) or not images_xlsx_base64.strip():
        return jsonify({"ok": False, "error": "imagesXlsxBase64 is empty"}), 400

    try:
        ensure_dir(JSON_PATH)
        ensure_dir(IMAGE_XLSX_PATH)

        # 写 JSON（UTF-8）
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            f.write(json_text)

        # 写 images.xlsx（base64 -> bytes）
        xlsx_bytes = base64.b64decode(images_xlsx_base64)
        with open(IMAGE_XLSX_PATH, "wb") as f:
            f.write(xlsx_bytes)

        return jsonify({
            "ok": True,
            "jsonPath": JSON_PATH,
            "imagesXlsxPath": IMAGE_XLSX_PATH
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # 只监听本机
    app.run(host="127.0.0.1", port=3210, debug=False)
