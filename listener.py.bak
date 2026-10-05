"""
listener.py - Speech Recognition Listener for Maggie
"""
import speech_recognition as sr
from rich.console import Console
from config import STT_LANGUAGE

console = Console()
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.4
recognizer.dynamic_energy_threshold = True

def listen_for_query(mic: sr.Microphone) -> str:
    with mic as source:
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return ""
    try:
        query = recognizer.recognize_google(audio, language=STT_LANGUAGE)
        console.print(f"[bold magenta]You:[/bold magenta] {query}")
        return query
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        console.print(f"[red]Speech recognition error: {e}[/red]")
        return ""

def calibrate(mic: sr.Microphone):
    with mic as source:
        console.print("[dim]Calibrating audio sensors for ambient noise...[/dim]")
        recognizer.adjust_for_ambient_noise(source, duration=1.2)
