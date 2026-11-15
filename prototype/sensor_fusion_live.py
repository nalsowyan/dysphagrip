
import re
import time
import threading
from collections import deque

import numpy as np
import sounddevice as sd
import serial
from serial.tools import list_ports
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def find_contact_mic():
    """El índice de PortAudio cambia al conectar monitores u otros dispositivos."""
    for index, dev in enumerate(sd.query_devices()):
        name = str(dev["name"]).lower()
        if int(dev["max_input_channels"]) < 1:
            continue
        if "air 192" in name or "m-audio" in name:
            return index, dev
    raise SystemExit(
        "No se encontró el M-Audio AIR 192|6. Conéctalo por USB y vuelve a correr el script."
    )


AUDIO_DEVICE, _audio_dev = find_contact_mic()
SAMPLE_RATE = int(_audio_dev["default_samplerate"])
AUDIO_CHANNELS = int(_audio_dev["max_input_channels"])
WINDOW_SECONDS = 5
print(
    f"Audio: {_audio_dev['name']} "
    f"(device {AUDIO_DEVICE}, {AUDIO_CHANNELS} ch @ {SAMPLE_RATE} Hz)"
)

audio_buffer = np.zeros(
    SAMPLE_RATE * WINDOW_SECONDS,
    dtype=np.float32
)

imu_data = deque(maxlen=1000)

audio_lock = threading.Lock()
imu_lock = threading.Lock()
stop_event = threading.Event()

# Parse your existing Arduino output
pattern = re.compile(
    r"Tilt X:\s*([-\d.]+)\s+"
    r"Y:\s*([-\d.]+)\s+"
    r"Z:\s*([-\d.]+)\s*\|\s*"
    r"Turn X:\s*([-\d.]+)\s+"
    r"Y:\s*([-\d.]+)\s+"
    r"Z:\s*([-\d.]+)"
)

# Select the real Arduino serial port
ports = list(list_ports.comports())

for i, port in enumerate(ports):
    print(f"{i}: {port.device} - {port.description}")

port_index = int(input("Arduino port index: "))
port_name = ports[port_index].device

# Audio callback
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)

    with audio_lock:
        if frames >= len(audio_buffer):
            audio_buffer[:] = indata[-len(audio_buffer):, 0]
        else:
            audio_buffer[:-frames] = audio_buffer[frames:]
            audio_buffer[-frames:] = indata[:, 0]

# Arduino serial reader
def read_arduino():
    try:
        with serial.Serial(
            port_name, 115200, timeout=0.2
        ) as arduino:

            print("Arduino connected.")

            while not stop_event.is_set():
                line = arduino.readline().decode(
                    "utf-8", errors="ignore"
                ).strip()

                match = pattern.search(line)

                if match:
                    values = [
                        float(v) for v in match.groups()
                    ]

                    with imu_lock:
                        imu_data.append(
                            (time.monotonic(), *values)
                        )

    except Exception as error:
        print("Arduino error:", error)

# Start serial reader
reader = threading.Thread(
    target=read_arduino,
    daemon=True
)
reader.start()

# Build the dashboard
fig, axes = plt.subplots(
    3, 1, figsize=(12, 8)
)

fig.suptitle(
    "DysphaGrip - Live Sensor Fusion",
    fontsize=16
)

audio_line, = axes[0].plot([], [])
tilt_lines = [
    axes[1].plot([], [], label=axis)[0]
    for axis in ["X", "Y", "Z"]
]
turn_lines = [
    axes[2].plot([], [], label=axis)[0]
    for axis in ["X", "Y", "Z"]
]

axes[0].set_title("Contact Microphone - Cherub")
axes[1].set_title("MPU6050 - Tilt")
axes[2].set_title("MPU6050 - Turn")

for ax in axes:
    ax.set_xlim(-WINDOW_SECONDS, 0)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel("Signal")

axes[1].legend(loc="upper right")
axes[2].legend(loc="upper right")
axes[2].set_xlabel("Time relative to now (s)")

def update(frame):
    # Update audio signal
    with audio_lock:
        audio = audio_buffer.copy()

    step = 40
    audio_plot = audio[::step]

    x_audio = np.linspace(
        -WINDOW_SECONDS, 0, len(audio_plot)
    )

    audio_line.set_data(x_audio, audio_plot)

    peak = max(0.005, np.max(np.abs(audio)) * 1.2)
    axes[0].set_ylim(-peak, peak)

    # Update MPU6050
    with imu_lock:
        data = list(imu_data)

    if data:
        now = time.monotonic()

        recent = [
            row for row in data
            if now - row[0] <= WINDOW_SECONDS
        ]

        if recent:
            arr = np.asarray(recent)
            t = arr[:, 0] - now

            for i in range(3):
                tilt_lines[i].set_data(
                    t, arr[:, i + 1]
                )
                turn_lines[i].set_data(
                    t, arr[:, i + 4]
                )

            for ax, cols in [
                (axes[1], arr[:, 1:4]),
                (axes[2], arr[:, 4:7])
            ]:
                low = np.min(cols)
                high = np.max(cols)
                margin = max(0.1, (high - low) * 0.2)
                ax.set_ylim(
                    low - margin, high + margin
                )

    return [audio_line, *tilt_lines, *turn_lines]

animation = FuncAnimation(
    fig,
    update,
    interval=100,
    cache_frame_data=False
)

try:
    with sd.InputStream(
        device=AUDIO_DEVICE,
        channels=AUDIO_CHANNELS,
        samplerate=SAMPLE_RATE,
        blocksize=1024,
        dtype="float32",
        callback=audio_callback
    ):
        plt.tight_layout()
        plt.show()

finally:
    stop_event.set()
    reader.join(timeout=1)

print("DysphaGrip stopped.")