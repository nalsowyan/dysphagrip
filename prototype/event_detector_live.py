
import csv
import time
import threading
from pathlib import Path
from datetime import datetime
from collections import deque

import numpy as np


class SwallowEventDetector:
    """
    Experimental audio + IMU swallow-event detector.

    This is NOT a medical diagnostic device.
    It does not detect aspiration or determine swallow safety.
    """

    def __init__(
        self,
        calibration_seconds=5.0,
        coincidence_seconds=0.65,
        cooldown_seconds=1.5,
        audio_multiplier=2.5,
        imu_multiplier=3.0,
        csv_path="dysphagrip_events.csv",
    ):
        self.calibration_seconds = calibration_seconds
        self.coincidence_seconds = coincidence_seconds
        self.cooldown_seconds = cooldown_seconds
        self.audio_multiplier = audio_multiplier
        self.imu_multiplier = imu_multiplier

        self.lock = threading.Lock()
        self.start_time = time.monotonic()
        self.last_event_time = -float("inf")

        self.audio_calibration = []
        self.tilt_calibration = []
        self.turn_calibration = []

        self.audio_threshold = None
        self.tilt_threshold = None
        self.turn_threshold = None

        self.previous_tilt = None
        self.last_audio_hit = None
        self.last_imu_hit = None

        self.ready = False
        self.event_count = 0
        self.last_calibration_warning = 0.0

        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        with self.csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "elapsed_seconds",
                "event_id",
                "event_type",
                "audio_rms",
                "audio_threshold",
                "tilt_delta",
                "turn_magnitude",
            ])

        print("[DysphaGrip] Detector initialized")
        print("[Calibration] Remain still and silent.")

    @staticmethod
    def calculate_threshold(values, multiplier, floor):
        data = np.asarray(values, dtype=float)

        median = float(np.median(data))
        mad = float(np.median(np.abs(data - median)))

        return max(
            median * multiplier,
            median + 6.0 * mad,
            floor,
        )

    def try_finish_calibration(self, now):
        if self.ready:
            return

        elapsed = now - self.start_time

        if elapsed < self.calibration_seconds:
            return

        if (
            len(self.audio_calibration) < 20
            or len(self.tilt_calibration) < 20
        ):
            if now - self.last_calibration_warning > 3.0:
                print(
                    "[Calibration] Waiting for audio "
                    "and IMU samples..."
                )
                self.last_calibration_warning = now
            return

        self.audio_threshold = self.calculate_threshold(
            self.audio_calibration,
            self.audio_multiplier,
            floor=0.0001,
        )

        self.tilt_threshold = self.calculate_threshold(
            self.tilt_calibration,
            self.imu_multiplier,
            floor=1e-6,
        )

        self.turn_threshold = self.calculate_threshold(
            self.turn_calibration,
            self.imu_multiplier,
            floor=1e-6,
        )

        self.ready = True

        print("\n[Calibration] Complete!")
        print(
            f"Audio threshold: {self.audio_threshold:.6f}"
        )
        print(
            f"Tilt threshold: {self.tilt_threshold:.6f}"
        )
        print(
            f"Turn threshold: {self.turn_threshold:.6f}"
        )
        print("[DysphaGrip] Detection active.\n")

    def on_audio(self, audio_samples):
        """
        Call with each audio chunk from Step 9.
        Accepts mono or multichannel NumPy audio.
        """

        raw = np.asarray(audio_samples)

        if raw.size == 0:
            return

        if np.issubdtype(raw.dtype, np.integer):
            scale = max(
                abs(np.iinfo(raw.dtype).min),
                np.iinfo(raw.dtype).max,
            )
            samples = raw.astype(np.float64) / scale
        else:
            samples = raw.astype(np.float64)

        if not np.all(np.isfinite(samples)):
            return

        if samples.ndim == 2:
            # Use the first channel. Set Step 9 to
            # select the channel with the contact pickup.
            samples = samples[:, 0]

        rms = float(
            np.sqrt(np.mean(np.square(samples)))
        )
        peak = float(np.max(np.abs(samples)))

        now = time.monotonic()

        with self.lock:
            if not self.ready:
                self.audio_calibration.append(rms)
                self.try_finish_calibration(now)
                return

            if rms >= self.audio_threshold:
                self.last_audio_hit = {
                    "time": now,
                    "rms": rms,
                    "peak": peak,
                }
                self.try_detect(now)

    def on_imu(self, tilt_xyz, turn_xyz):
        """
        Call with two triples from Step 9.

        tilt_xyz: three acceleration/orientation values
        turn_xyz: three gyroscope/rate values

        Keep the same units and data meaning during
        calibration and detection.
        """

        tilt = np.asarray(tilt_xyz, dtype=float)
        turn = np.asarray(turn_xyz, dtype=float)

        if tilt.shape != (3,) or turn.shape != (3,):
            raise ValueError(
                "IMU inputs must each contain 3 values."
            )

        if not (
            np.all(np.isfinite(tilt))
            and np.all(np.isfinite(turn))
        ):
            return

        now = time.monotonic()

        with self.lock:
            if self.previous_tilt is None:
                self.previous_tilt = tilt.copy()
                return

            tilt_delta = float(
                np.linalg.norm(
                    tilt - self.previous_tilt
                )
            )

            turn_magnitude = float(
                np.linalg.norm(turn)
            )

            self.previous_tilt = tilt.copy()

            if not self.ready:
                self.tilt_calibration.append(tilt_delta)
                self.turn_calibration.append(turn_magnitude)
                self.try_finish_calibration(now)
                return

            movement_detected = (
                tilt_delta >= self.tilt_threshold
                or turn_magnitude >= self.turn_threshold
            )

            if movement_detected:
                self.last_imu_hit = {
                    "time": now,
                    "tilt_delta": tilt_delta,
                    "turn_magnitude": turn_magnitude,
                }
                self.try_detect(now)

    def try_detect(self, now):
        if (
            self.last_audio_hit is None
            or self.last_imu_hit is None
        ):
            return

        audio = self.last_audio_hit
        imu = self.last_imu_hit

        time_difference = abs(
            audio["time"] - imu["time"]
        )

        if time_difference > self.coincidence_seconds:
            return

        if (
            now - min(audio["time"], imu["time"])
            > self.coincidence_seconds
        ):
            return

        if (
            now - self.last_event_time
            < self.cooldown_seconds
        ):
            return

        self.last_event_time = now
        self.event_count += 1

        timestamp = datetime.now().astimezone().isoformat(
            timespec="milliseconds"
        )

        elapsed = now - self.start_time

        with self.csv_path.open(
            "a", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                timestamp,
                round(elapsed, 3),
                self.event_count,
                "possible_swallow",
                round(audio["rms"], 6),
                round(self.audio_threshold, 6),
                round(imu["tilt_delta"], 6),
                round(imu["turn_magnitude"], 6),
            ])

        print(
            f"\n[EVENT {self.event_count}] "
            "Possible swallow detected"
        )
        print(
            f" Audio RMS: {audio['rms']:.6f}"
        )
        print(
            f" IMU delta: {imu['tilt_delta']:.6f}"
        )
        print(
            f" Time difference: {time_difference:.3f}s"
        )
        print(
            f" Total events: {self.event_count}\n"
        )

        # Prevent reusing the same sensor peaks.
        self.last_audio_hit = None
        self.last_imu_hit = None

