import serial
from serial.tools import list_ports

ports = list(list_ports.comports())

if not ports:
    raise SystemExit(
        "No serial ports found. Check Arduino USB connection."
    )

print("Available serial ports:")

for i, port in enumerate(ports):
    print(f"{i}: {port.device} — {port.description}")

index = int(input("Select Arduino port number: "))
port_name = ports[index].device

print(f"Connecting to {port_name}...")

with serial.Serial(port_name, 115200, timeout=2) as arduino:
    print("Reading Arduino data...")

    for _ in range(40):
        raw = arduino.readline()
        line = raw.decode("utf-8", errors="replace").strip()

        if line:
            print(line)

print("Test finished.")
