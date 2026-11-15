
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from threading import Lock

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


DEVICE_ID, _audio_dev = find_contact_mic()
SAMPLE_RATE = int(_audio_dev["default_samplerate"])
AUDIO_CHANNELS = int(_audio_dev["max_input_channels"])
CHANNEL = 0
WINDOW_SECONDS = 3
print(
    f"Audio: {_audio_dev['name']} "
    f"(device {DEVICE_ID}, {AUDIO_CHANNELS} ch @ {SAMPLE_RATE} Hz)"
)

BUFFER_SIZE = SAMPLE_RATE * WINDOW_SECONDS
buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
lock = Lock()

# Receive real audio data from the Cherub
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)

    with lock:
        if frames >= BUFFER_SIZE:
            buffer[:] = indata[-BUFFER_SIZE:, CHANNEL]
        else:
            buffer[:-frames] = buffer[frames:]
            buffer[-frames:] = indata[:, CHANNEL]

# Set up live graph
STEP = 20
x = np.arange(0, BUFFER_SIZE, STEP) / SAMPLE_RATE

fig, ax = plt.subplots(figsize=(12, 5))
line, = ax.plot(x, np.zeros(len(x)), color="#00a8a8")

ax.set_title("DysphaGrip - Live Contact Sensor")
ax.set_xlabel("Time (seconds)")
ax.set_ylabel("Amplitude")
ax.set_xlim(0, WINDOW_SECONDS)
ax.set_ylim(-0.05, 0.05)
ax.grid(True, alpha=0.3)

info = ax.text(
    0.02, 0.95, "",
    transform=ax.transAxes,
    verticalalignment="top"
)

def update(frame):
    with lock:
        data = buffer.copy()

    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(data ** 2)))

    line.set_ydata(data[::STEP])

    # Automatically adjust graph scale
    limit = max(0.005, peak * 1.3)
    ax.set_ylim(-limit, limit)

    info.set_text(
        f"Peak: {peak:.5f} | RMS: {rms:.5f}"
    )

    return line, info

animation = FuncAnimation(
    fig,
    update,
    interval=100,
    blit=False,
    cache_frame_data=False
)

print("DysphaGrip live sensor started.")

with sd.InputStream(
    device=DEVICE_ID,
    channels=AUDIO_CHANNELS,
    samplerate=SAMPLE_RATE,
    blocksize=1024,
    dtype="float32",
    callback=audio_callback
):
    plt.show()

print("Sensor stopped.")
