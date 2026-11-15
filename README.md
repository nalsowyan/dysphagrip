# DysphaGrip

**A low-cost wearable that listens to swallowing.**
A contact microphone and a 6-axis motion sensor at the neck, synced on one clock and shown live on a dashboard.

Built at **SanD Hacks 2026**.

| | |
|---|---|
| 🌐 **Live demo** | https://66-42-64-41.sslip.io/ |
| 🧠 **Main app (original repo)** | https://github.com/XxPosedd/dysphagrip |
| 🔬 **Python prototype (original repo)** | https://github.com/maxhrdz/test2 → now in [`prototype/`](prototype/) |

---

## The problem

- **Every 40 seconds**, someone in the U.S. has a stroke ([CDC](https://www.cdc.gov/stroke/data-research/facts-stats/index.html)).
- **42%** of acute stroke patients develop **dysphagia**, meaning they can't swallow safely ([BMC Geriatrics meta-analysis, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9103417)).
- Those patients face roughly **4× the risk of pneumonia** and **4× the risk of death** (same study).
- Aspiration can be **silent**: liquid enters the airway with no cough to warn anyone.
- The gold-standard check is an **X-ray swallow study**. It means a hospital visit, radiation and a trained specialist, and it captures a single snapshot rather than everyday monitoring.

**Our question:** can low-cost, off-the-shelf sensors capture swallowing signals in sync and with clear signal quality, anywhere?

## What it does

- 🎙️ **Contact microphone** picks up vibration at the throat surface
- 📐 **MPU-6050** (accelerometer + gyroscope) on an **Arduino UNO Q** tracks neck motion on 6 axes
- ⏱️ A **Python service** puts both signals on **one shared clock**
- 📊 A **React dashboard** shows the live waveform, spectrogram, motion traces, signal-quality checks (clipping, mains hum, movement) and an event log
- 🔊 **ElevenLabs** voice status cues, 🗄️ **Neon Postgres** session storage (no raw audio, no names), 🌍 **Bright Data** sourced swallowing-health resources

## How it works

```text
Contact mic ──► audio interface ──┐
                                  ├──► Python service (shared clock, DSP, quality checks)
MPU-6050 ──► Arduino UNO Q ───────┘            │  WebSocket
                                               ▼
                              React + Vite dashboard ◄──► Express API ──► Neon Postgres
                                                                   ├──► ElevenLabs TTS
                                                                   └──► Bright Data
```

### Grounded in clinical data

We built on a public clinical dataset: **248 patients with dysphagia, 3,144 swallows**, recorded at **4 kHz** with a neck microphone and a 3-axis accelerometer. Swallow timing was annotated from synchronized X-ray video ([Khalifa, Donohue, Coyle & Sejdić, Zenodo 2021](https://doi.org/10.5281/zenodo.4539695)). It is their data, not ours, and it shows these neck signals can capture swallows. Our offline experiments with it are in [`services/audio/research/`](services/audio/research/).

## Hardware

| MPU-6050 pin | Arduino UNO Q pin |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SCL | SCL |
| SDA | SDA |

The contact microphone (KORG CM-300 or similar) goes into a USB audio interface (Behringer UM2). Firmware and bring-up guide: [`hardware/unoq_mpu6050/`](hardware/unoq_mpu6050/).

## Run it

Requirements: Node.js 20+, Python 3.10+.

```bash
git clone https://github.com/nalsowyan/dysphagrip.git && cd dysphagrip
npm install && npm run install:all
npm run build        # production build
npm run dev          # API + dashboard at http://localhost:5173
```

You can try the dashboard **without any hardware**: open the **Práctica** (practice) tab, which runs in the browser.

For live sensors, start the Python audio and motion service:

```bash
cd services/audio
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m dysphagrip_audio serve --device um2 --channel 1 --autostart
```

Integrations are optional. Copy `.env.example` to `.env` and add keys for Neon, ElevenLabs and Bright Data. Full setup, API and deployment details are in [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) and [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Repository map

```text
apps/web/          React + Vite dashboard (TypeScript)
server/            Express API: sessions, voice, resources
services/audio/    Python audio + motion service, DSP, tests, research
hardware/          UNO Q + MPU-6050 firmware, audio wiring
prototype/         Original Python prototype (from maxhrdz/test2): live mic, sensor fusion, event detector
docs/              Developer guide, deploy, decisions, demo script, safety
```

## Built with

Arduino UNO Q · MPU-6050 · contact microphone · Python (NumPy, SciPy, FastAPI) · TypeScript · React · Vite · Node.js / Express · Neon Postgres · ElevenLabs · Bright Data · Vultr

## What's next

1. Train ML to tell swallows apart from speech, coughs and movement
2. Test with more people and swallowing conditions
3. Partner with speech-language pathologists

**Built in one hackathon, with the parts we had.** Purpose-built hardware (a smaller board, a wireless link and a soft neck band) would make DysphaGrip far more practical to wear every day.

## Team

- **Maximiliano Hernandez:** architecture, core system, integrations, deployment
- **Shaheer Ali:** AI anomaly research
- **Ali I**
- **Nasser Alsowyan**

---

DysphaGrip is a research prototype, not a diagnostic device. See [`docs/SAFETY_AND_CLAIMS.md`](docs/SAFETY_AND_CLAIMS.md).
