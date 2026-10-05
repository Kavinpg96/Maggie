"""
player_state.py - Tiny shared "now playing" state for the GUI's embedded
YouTube panel. Kept separate from status.py so this doesn't need to touch
status.py's existing internals -- gui.py's Api.get_status() just reads
get_embed_url() directly and adds it to the dict it already returns.
"""
_current_video_id = None


def set_video(video_id: str):
    global _current_video_id
    _current_video_id = video_id


def clear_video():
    global _current_video_id
    _current_video_id = None


def get_embed_url() -> str:
    if not _current_video_id:
        return ""
    return f"https://www.youtube.com/embed/{_current_video_id}?autoplay=1"
