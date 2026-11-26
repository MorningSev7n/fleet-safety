"""Check the sound and speech commands for macOS and Windows (nothing is played)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detection import alarm


# macOS
alarm.ON_WINDOWS = False
assert alarm.sound_command("/tmp/a.wav") == ["afplay", "/tmp/a.wav"]
assert alarm.speech_command("Eyes on the road.") == ["say", "Eyes on the road."]

# Windows
alarm.ON_WINDOWS = True
sound = alarm.sound_command(r"C:\Users\o'neil\a.wav")
assert sound[0] == "powershell"
assert r"'C:\Users\o''neil\a.wav'" in sound[-1]  # the ' is escaped
assert "PlaySync" in sound[-1]

speech = alarm.speech_command("Put the phone down.")
assert speech[0] == "powershell"
assert "Speak('Put the phone down.')" in speech[-1]

print("ok: alarm commands")
