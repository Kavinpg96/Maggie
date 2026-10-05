"""Opt-in, local voice-similarity matching for Maggie."""
import json
import math
import os
import tempfile
from pathlib import Path


_PROFILE_PATH = (
    Path.home() / ".local" / "share" / "maggie_ai" / "owner_voice.json"
)
_PROFILE_VERSION = 1
_MATCH_THRESHOLD = 0.92
_MIN_ENROLLMENT_SAMPLES = 5


def is_enrolled() -> bool:
    return _PROFILE_PATH.is_file()


def _embedding_from_pcm(pcm: bytes, sample_rate: int) -> list[float]:
    import numpy as np
    from scipy.fft import dct

    signal = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    if signal.size < sample_rate:
        raise ValueError("Voice sample must contain at least one second of audio.")

    signal /= 32768.0
    signal -= signal.mean()
    if np.sqrt(np.mean(signal**2)) < 0.008:
        raise ValueError("Voice sample is too quiet; please speak closer to the microphone.")

    frame_length = int(sample_rate * 0.025)
    hop_length = int(sample_rate * 0.010)
    if signal.size < frame_length:
        raise ValueError("Voice sample is too short.")
    frame_count = 1 + (signal.size - frame_length) // hop_length
    frames = np.lib.stride_tricks.sliding_window_view(signal, frame_length)[
        ::hop_length
    ][:frame_count].copy()
    frames *= np.hanning(frame_length)

    n_fft = 1 << (frame_length - 1).bit_length()
    power = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2
    mel_min = 2595.0 * math.log10(1 + 80.0 / 700.0)
    mel_max = 2595.0 * math.log10(1 + min(7600.0, sample_rate / 2) / 700.0)
    mel_points = np.linspace(mel_min, mel_max, 28)
    hz_points = 700.0 * (10 ** (mel_points / 2595.0) - 1)
    bins = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    filters = np.zeros((26, n_fft // 2 + 1))
    for index in range(1, 27):
        left, center, right = bins[index - 1:index + 2]
        if center <= left or right <= center:
            continue
        filters[index - 1, left:center] = np.arange(left, center) - left
        filters[index - 1, left:center] /= center - left
        filters[index - 1, center:right] = right - np.arange(center, right)
        filters[index - 1, center:right] /= right - center

    mel_energy = np.maximum(power @ filters.T, 1e-10)
    coefficients = dct(np.log(mel_energy), type=2, axis=1, norm="ortho")[:, 1:13]
    embedding = np.concatenate((coefficients.mean(axis=0), coefficients.std(axis=0)))
    magnitude = np.linalg.norm(embedding)
    if not np.isfinite(magnitude) or magnitude == 0:
        raise ValueError("Could not extract a usable voice sample.")
    return (embedding / magnitude).tolist()


def _embedding(audio) -> list[float]:
    pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
    return _embedding_from_pcm(pcm, 16000)


def enroll(audio_samples) -> None:
    if len(audio_samples) < _MIN_ENROLLMENT_SAMPLES:
        raise ValueError(f"Record {_MIN_ENROLLMENT_SAMPLES} voice samples to enroll.")

    embeddings = [_embedding(audio) for audio in audio_samples]
    profile = {"version": _PROFILE_VERSION, "embeddings": embeddings}
    _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(_PROFILE_PATH.parent, 0o700)
    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=".owner_voice-", dir=_PROFILE_PATH.parent
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as profile_file:
            json.dump(profile, profile_file)
            profile_file.flush()
            os.fsync(profile_file.fileno())
        os.replace(temporary_path, _PROFILE_PATH)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def matches_owner(audio) -> bool:
    if not is_enrolled():
        return False

    with _PROFILE_PATH.open(encoding="utf-8") as profile_file:
        profile = json.load(profile_file)
    if profile.get("version") != _PROFILE_VERSION:
        raise ValueError("The saved voice profile version is not supported.")

    embeddings = profile.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) < _MIN_ENROLLMENT_SAMPLES:
        raise ValueError("The saved voice profile is incomplete.")

    current = _embedding(audio)
    import numpy as np

    similarities = [
        float(np.dot(current, reference))
        for reference in embeddings
        if isinstance(reference, list) and len(reference) == len(current)
    ]
    if not similarities:
        raise ValueError("The saved voice profile contains invalid samples.")
    return max(similarities) >= _MATCH_THRESHOLD
