
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt

# Mostrar dispositivos de audio disponibles
print(sd.query_devices())

# Selecciona el índice de entrada de tu M-Audio
device_id = int(input("M-Audio input device ID: "))

sample_rate = 44100
duration = 5

print("Grabando 5 segundos...")

audio = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=2,
    dtype="float32",
    device=device_id,
)

sd.wait()

# El Cherub está conectado a Instrument Input 1.
signal = audio[:, 0]

time = np.arange(len(signal)) / sample_rate

plt.figure(figsize=(12, 4))
plt.plot(time, signal)
plt.xlabel("Time (seconds)")
plt.ylabel("Amplitude")
plt.title("DysphaGrip - Contact Microphone Signal")
plt.grid(True)
plt.tight_layout()
plt.show()
