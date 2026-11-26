"""Background alarm siren played with macOS afplay. Moved from detector.py unchanged."""

import math
import os
import subprocess
import struct
import tempfile
import threading
import time
import wave


# Alarm
ALARM_FREQUENCY_LOW = 650
ALARM_FREQUENCY_HIGH = 1100
ALARM_DURATION = 1.2
ALARM_VOLUME = 0.65


# ==========================================
# 4. CONTINUOUS ALARM
# ==========================================

ALARM_SOUND = os.path.join(
    tempfile.gettempdir(),
    "fleet_safety_alarm.wav"
)

alarm_active = threading.Event()
alarm_shutdown = threading.Event()


def create_alarm_sound():
    """Generate a repeating two-tone siren."""

    sample_rate = 44100
    total_samples = int(sample_rate * ALARM_DURATION)

    with wave.open(ALARM_SOUND, "wb") as sound_file:

        sound_file.setnchannels(1)
        sound_file.setsampwidth(2)
        sound_file.setframerate(sample_rate)

        audio_data = []

        for i in range(total_samples):

            progress = i / total_samples

            frequency = (
                ALARM_FREQUENCY_LOW
                + (ALARM_FREQUENCY_HIGH - ALARM_FREQUENCY_LOW)
                * (0.5 - 0.5 * math.cos(2 * math.pi * progress))
            )

            current_time = i / sample_rate
            pulse_position = current_time % 0.4

            if pulse_position < 0.28:
                amplitude = ALARM_VOLUME
            else:
                amplitude = 0.0

            sample = int(
                32767
                * amplitude
                * math.sin(2 * math.pi * frequency * current_time)
            )

            audio_data.append(
                struct.pack("<h", sample)
            )

        sound_file.writeframes(b"".join(audio_data))

    print("Emergency alarm sound generated.")


def play_alarm_continuously():
    """Keep playing the alarm while an unsafe behavior is detected."""

    while not alarm_shutdown.is_set():

        if not alarm_active.wait(timeout=0.1):
            continue

        while alarm_active.is_set() and not alarm_shutdown.is_set():

            try:

                if not os.path.exists(ALARM_SOUND):

                    print("ERROR: Alarm sound file is missing.")
                    alarm_active.wait(timeout=0.5)
                    continue

                process = subprocess.Popen(
                    ["afplay", ALARM_SOUND],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                while (
                    process.poll() is None
                    and alarm_active.is_set()
                    and not alarm_shutdown.is_set()
                ):
                    time.sleep(0.05)

                if process.poll() is None:

                    process.terminate()

                    try:
                        process.wait(timeout=0.5)

                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

            except Exception as error:

                print(f"Alarm playback error: {error}")
                alarm_active.wait(timeout=0.5)

    print("Alarm thread stopped.")


def start_alarm_worker():
    """Start one background thread for the alarm."""

    thread = threading.Thread(
        target=play_alarm_continuously,
        daemon=True
    )

    thread.start()

    return thread


def stop_alarm_worker(thread):
    """Stop the alarm and shut down its background thread."""

    alarm_active.clear()
    alarm_shutdown.set()

    if thread is not None:
        thread.join(timeout=2.0)



def play_chime():
    """One soft chime (not the siren), without waiting for it to finish."""

    try:

        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except Exception as error:

        print(f"Could not play chime: {error}")
