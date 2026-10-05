"""
listener.py - Low-Latency Speech Recognition Listener for Maggie
"""
import speech_recognition as sr
from config import STT_LANGUAGE
import applog
import language

recognizer = sr.Recognizer()

# Follow changing microphone level and room noise instead of relying on one
# fixed threshold. This helps with quiet speakers and background noise changes.
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.5
recognizer.dynamic_energy_threshold = True
recognizer.dynamic_energy_adjustment_damping = 0.15
recognizer.dynamic_energy_ratio = 1.4
recognizer.energy_threshold = 300

TAMIL_LANG_CODE = "ta-IN"

def calibrate(mic: sr.Microphone):
    with mic as source:
        applog.log("Calibrating audio sensors for ambient noise...", style="dim")
        recognizer.adjust_for_ambient_noise(source, duration=0.6)
        # Keep a modest floor against electronic noise, while allowing
        # dynamic adaptation during normal listening.
        recognizer.energy_threshold = max(recognizer.energy_threshold, 180)

def listen_for_query(mic: sr.Microphone) -> str:
    with mic as source:
        try:
            # Poll often for quick pickup and allow longer utterances through.
            audio = recognizer.listen(source, timeout=1.5, phrase_time_limit=20)
        except sr.WaitTimeoutError:
            return ""
        except Exception as exc:
            applog.log(f"Microphone capture error: {exc}", style="yellow")
            return ""

    try:
        import voice_identity

        owner_match = voice_identity.matches_owner(audio)
        from status import set_flag

        set_flag("owner_voice_match", owner_match)
    except Exception as exc:
        applog.log(f"Local voice matching unavailable: {exc}", style="yellow")

    mode = language.get_mode()
    lang_code = TAMIL_LANG_CODE if mode == "ta" else STT_LANGUAGE

    try:
        query = recognizer.recognize_google(audio, language=lang_code)
        applog.log(f"You ({mode}): {query}", style="bold magenta")
        return query.strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        applog.log(f"Speech recognition service error: {exc}", style="yellow")
        return ""


def enroll_owner(mic: sr.Microphone) -> bool:
    import voice_identity

    if voice_identity.is_enrolled():
        applog.log("Replacing the existing local voice profile.", style="yellow")

    samples = []
    prompts = (
        "Maggie, listen to me.",
        "I am enrolling my voice.",
        "Please remember how I sound.",
        "This is my voice profile.",
        "Maggie, recognize my voice.",
    )
    with mic as source:
        for index, prompt in enumerate(prompts, start=1):
            applog.log(f"Voice sample {index} of {len(prompts)}: {prompt}", style="cyan")
            try:
                samples.append(
                    recognizer.listen(source, timeout=20, phrase_time_limit=8)
                )
            except sr.WaitTimeoutError as exc:
                applog.log(f"No speech detected for sample {index}: {exc}", style="yellow")
                return False

    voice_identity.enroll(samples)
    applog.log(
        "Local voice profile saved. Only derived voice features are stored; "
        "recorded audio is discarded.",
        style="green",
    )
    return True
