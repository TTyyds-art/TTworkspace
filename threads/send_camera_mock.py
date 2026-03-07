import json
import time
import serial

PORT = "COM4"      # 改成你要写入的那个口：虚拟对的“发送端”
BAUD = 9600       # 先用 115200；如果你 SerialThread 用的是别的波特率，再改
TIMEOUT = 1

payload = {
    "product_name": "柠檬红茶",
    "product_sugar": "五分糖",
    "product_quantity": "中杯",
    "product_ice": "正常冰",
    "product_simp": "无",
    "unit_price": "18.0",
    "recipe": "A100E100H100W100"
}

def main():
    s = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    time.sleep(0.2)

    msg = json.dumps(payload, ensure_ascii=False)
    # 关键点：
    # 1) 必须是一整段 JSON 对象（{...}）
    # 2) 建议追加 \n 作为结束符（虽然后端不是 readline，但对调试友好）
    s.write((msg + "\n").encode("utf-8"))
    s.flush()

    print("Sent:", msg)
    s.close()

if __name__ == "__main__":
    main()