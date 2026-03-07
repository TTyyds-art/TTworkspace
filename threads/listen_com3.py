import serial, time

s = serial.Serial("COM3", 9600, timeout=1)
print("Listening on COM3...")

while True:
    n = s.in_waiting
    if n:
        data = s.read(n)
        print("RX bytes:", data)
        print("RX text :", data.decode("utf-8", errors="ignore"))
    time.sleep(0.05)
