
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
import wave

print(sd.query_devices())

device_id = int(input("M-Audio device ID: "))
sample_rate = 44100
duration = 5

print("Recording...")

audio = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=2,
    dtype="float32",
    device=device_id,
)

sd.wait()

# Cherub connected to Instrument Input 1
signal = audio[:, 0]

peak = np.max(np.abs(signal))
rms = np.sqrt(np.mean(signal ** 2))
clipping = np.mean(np.abs(signal) >= 0.999) * 100

print(f"Peak amplitude: {peak:.4f}")
print(f"RMS: {rms:.4f}")
print(f"Clipping: {clipping:.3f}%")

# Save recording
pcm = (np.clip(signal, -1, 1) * 32767).astype(np.int16)

with wave.open("dysphagrip_test.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(pcm.tobytes())

# Display waveform
t = np.arange(len(signal)) / sample_rate

plt.plot(t, signal)
plt.xlabel("Time (seconds)")
plt.ylabel("Amplitude")
plt.title("DysphaGrip - Sensor Validation")
plt.grid(True)
plt.show()

print("Saved: dysphagrip_test.wav")
