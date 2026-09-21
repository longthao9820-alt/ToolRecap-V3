"""Settings configuration and defaults for ToolRecap V3.

Defaults match the specified requirements:
- Audio: original 0.0 dB, commentary 0.0 dB, duck OFF, ducking amount -12.0 dB,
  target loudness -14.0 LUFS, true peak -1.0 dBTP.
- GPU: True (GPU on).
- Voice: alloy, language en-US, style configurable.
- VoiceStudio: mode auto, local http://127.0.0.1:3900, remote https://desktop-t5c9b90.tail7b66e0.ts.net:8443.
- AI Gateway: endpoint http://127.0.0.1:20128, model ag/gemini-3.8-flash.
- Notifications: all defaults ON.
- Secrets: strictly separated; never stored in settings JSON.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from toolrecap_v3.persistence import ProjectPersistence, get_storage_root


@dataclass
class AppSettings:
    # Audio mix
    original_audio_db: float = 0.0
    commentary_audio_db: float = 0.0
    auto_duck: bool = False
    ducking_amount_db: float = -12.0
    target_loudness_lufs: float = -14.0
    true_peak_db: float = -1.0

    # Hardware & render
    use_gpu: bool = True
    quality: str = "high"
    video_codec: str = "h264"
    canvas_width: int = 1920
    canvas_height: int = 1080
    canvas_fps: float = 30.0
    burn_subtitles: bool = False
    output_format: str = "mp4"
    output_dir: str = ""

    # Voice & VoiceStudio
    voice_mode: str = "auto"  # "auto", "local", "remote"
    voice_local_url: str = "http://127.0.0.1:3900"
    voice_remote_url: str = ""
    voice_id: str = "alloy"
    voice_language: str = "en-US"
    voice_style: str = ""
    voice_model: str = "omnivoice"

    # AI Gateway
    gateway_endpoint: str = "http://127.0.0.1:20128"
    gateway_model: str = "ag/gemini-3.8-flash"
    gateway_thinking: bool = False

    # Notifications (all defaults ON)
    notify_complete: bool = True
    notify_error: bool = True
    play_completion_sound: bool = True
    flash_taskbar: bool = True
    notify_update: bool = True

    # Updater
    update_repo: str = "longthao9820-alt/ToolRecap-V3"

    # Prompt
    prompt: str = ""

    # Recap metadata (V2 compatible)
    recap_language: str = "en-US"
    recap_mode: str = "MAIN_STORIES"
    content_type: str = "US_TV_SHOW"
    source_rights_status: str = "UNVERIFIED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppSettings:
        """Create AppSettings from dict, ignoring unknown or secret fields."""
        allowed = cls.__dataclass_fields__
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)


class SettingsManager:
    """Manages reading and writing application settings in LOCALAPPDATA."""

    def __init__(self, persistence: Optional[ProjectPersistence] = None, storage_root: Optional[Path | str] = None) -> None:
        if persistence is not None:
            self.persistence = persistence
        else:
            self.persistence = ProjectPersistence(storage_root=storage_root)

    def load(self) -> AppSettings:
        """Load settings from persistence; returns default AppSettings if absent or corrupted."""
        try:
            raw = self.persistence.load_settings()
            return AppSettings.from_dict(raw)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> Path:
        """Persist settings to LOCALAPPDATA atomically."""
        return self.persistence.save_settings(settings.to_dict())
