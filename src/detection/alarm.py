"""Background alarm: chime, then siren + spoken warning (macOS afplay / say)."""

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

# Escalation: chime first, then siren + speech
CHIME_SOUND = "/System/Library/Sounds/Glass.aiff"
CHIME_SECONDS = 2.0
SPEECH_COOLDOWN = 5.0
SPEECH_MESSAGES = {
    "EYES_CLOSED": "Wake up. Eyes on the road.",
    "LOOK_AWAY": "Eyes on the road.",
    "PHONE": "Put the phone down.",
}


# ==========================================
# 4. CONTINUOUS ALARM
# ==========================================

ALARM_SOUND = os.path.join(
    tempfile.gettempdir(),
    "fleet_safety_alarm.wav"
)

alarm_active = threading.Event()
alarm_shutdown = threading.Event()
alarm_reason = None  # set by set_alarm(), read by the alarm thread


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


def set_alarm(reason):
    """Turn the alarm on with a reason (EYES_CLOSED, LOOK_AWAY, PHONE), or off with None."""

    global alarm_reason

    if reason is None:
        alarm_active.clear()

    else:
        alarm_reason = reason
        alarm_active.set()


def stop_process(process):
    """Stop a sound or speech process if it is still running."""

    if process is not None and process.poll() is None:

        process.terminate()

        try:
            process.wait(timeout=0.5)

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def play_while_active(sound_file, until=None):
    """Play one sound, cut it off when the alarm stops (or at time `until`)."""

    process = subprocess.Popen(
        ["afplay", sound_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    while (
        process.poll() is None
        and alarm_active.is_set()
        and not alarm_shutdown.is_set()
        and (until is None or time.time() < until)
    ):
        time.sleep(0.05)

    stop_process(process)


def play_alarm_continuously():
    """Keep playing the alarm while an unsafe behavior is detected.

    First CHIME_SECONDS: one soft chime. After that: the siren, plus a spoken
    message at most once every SPEECH_COOLDOWN seconds.
    """

    while not alarm_shutdown.is_set():

        if not alarm_active.wait(timeout=0.1):
            continue

        alarm_start = time.time()
        last_speech = None
        speech = None

        try:

            # Short chime first, then wait quietly until the 2 s are up.
            play_while_active(CHIME_SOUND, until=alarm_start + CHIME_SECONDS)

            while (
                alarm_active.is_set()
                and not alarm_shutdown.is_set()
                and time.time() < alarm_start + CHIME_SECONDS
            ):
                time.sleep(0.05)

            while alarm_active.is_set() and not alarm_shutdown.is_set():

                if not os.path.exists(ALARM_SOUND):

                    print("ERROR: Alarm sound file is missing.")
                    time.sleep(0.5)  # wait() returns at once while the alarm is on
                    continue

                # say runs on its own, so the siren keeps going while it talks.
                if last_speech is None or time.time() - last_speech >= SPEECH_COOLDOWN:

                    speech = subprocess.Popen(
                        ["say", SPEECH_MESSAGES.get(alarm_reason, "Eyes on the road.")],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    last_speech = time.time()

                play_while_active(ALARM_SOUND)

        except Exception as error:

            print(f"Alarm playback error: {error}")
            time.sleep(0.5)  # wait() returns at once while the alarm is on

        stop_process(speech)

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
            ["afplay", CHIME_SOUND],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except Exception as error:

        print(f"Could not play chime: {error}")
