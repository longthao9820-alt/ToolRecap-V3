"""Single VoiceStudio adapter supporting Local, Remote (via Tailscale), and Auto routing.

Invariants:
- Health, voices, and speech WAV handled via the SAME adapter.
- Auto mode: checks Local, then Remote only before synthesis.
- No engine fallback under any circumstances.
- Actual WAV validation: rejects corrupt WAV or zero/invalid duration.
- Auth separated (remote bearer token isolated from local).
- Bounded retries for transient errors only; logical errors fail immediately.
- Cancellation closes request immediately and raises CancelledError.
- Credential leakage prevented in all exceptions and logs.
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List, Optional, Tuple
import wave

import httpx

from toolrecap_v3.cancellation import CancellationToken
from toolrecap_v3.errors import (
    CancelledError,
    InvalidAudioError,
    VoiceStudioError,
    VoiceStudioUnavailableError,
)

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def sanitize_message(msg: str, secrets: Optional[List[Optional[str]]] = None) -> str:
    """Redact secrets from error messages to prevent credential leakage."""
    if not secrets:
        return msg
    sanitized = msg
    for secret in secrets:
        if secret and len(secret) >= 4 and secret in sanitized:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized


def validate_wav_bytes(data: bytes) -> float:
    """Validate WAV audio bytes and return duration in seconds.
    
    Raises InvalidAudioError if:
    - Data is empty or not a valid RIFF/WAVE container
    - Channel count <= 0
    - Framerate <= 0
    - Total frames <= 0
    - Duration <= 0
    """
    if not data or len(data) < 44:
        raise InvalidAudioError(f"Audio payload too small to be a valid WAV ({len(data)} bytes).")

    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            channels = w.getnchannels()
            framerate = w.getframerate()
            nframes = w.getnframes()

            if channels <= 0:
                raise InvalidAudioError(f"WAV has invalid channel count: {channels}")
            if framerate <= 0:
                raise InvalidAudioError(f"WAV has invalid framerate: {framerate}")
            if nframes <= 0:
                raise InvalidAudioError(f"WAV has zero frames: {nframes}")

            duration = nframes / float(framerate)
            if duration <= 0.0:
                raise InvalidAudioError(f"WAV has invalid duration: {duration:.3f}s")
            return duration
    except wave.Error as e:
        raise InvalidAudioError(f"Failed to parse WAV header: {e}") from e
    except Exception as e:
        if isinstance(e, InvalidAudioError):
            raise
        raise InvalidAudioError(f"Unexpected error validating WAV: {e}") from e


class VoiceStudioAdapter:
    """Unified adapter for VoiceStudio synthesis across Local, Remote, and Auto modes."""

    def __init__(
        self,
        mode: str = "auto",
        local_url: str = "http://127.0.0.1:3900",
        remote_url: str = "https://desktop-t5c9b90.tail7b66e0.ts.net:8443",
        remote_api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Optional[httpx.Client] = None,
    ) -> None:
        mode_lower = mode.strip().lower()
        if mode_lower not in {"auto", "local", "remote"}:
            raise ValueError(f"Invalid VoiceStudio mode '{mode}'. Must be 'auto', 'local', or 'remote'.")

        self.mode = mode_lower
        self.local_url = local_url.rstrip("/")
        self.remote_url = remote_url.rstrip("/")
        self.remote_api_key = remote_api_key
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_factor = backoff_factor
        self._external_client = client

    def close(self) -> None:
        """Close external client if owned or provided."""
        if self._external_client is not None:
            self._external_client.close()

    def __enter__(self) -> "VoiceStudioAdapter":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_client(self) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client
        return httpx.Client(timeout=self.timeout)

    def _sanitize(self, msg: str) -> str:
        return sanitize_message(msg, [self.remote_api_key])

    def _headers_for_url(self, url: str) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        # Auth is separate: apply remote_api_key only to remote_url
        if self.remote_api_key and url.startswith(self.remote_url):
            headers["Authorization"] = f"Bearer {self.remote_api_key}"
        return headers

    def check_health(self, target_url: Optional[str] = None) -> Dict[str, Any]:
        """Check /health on target URL or default resolved endpoint."""
        if target_url is None:
            if self.mode == "remote":
                target_url = self.remote_url
            elif self.mode == "auto":
                target_url, _ = self._resolve_target()
            else:
                target_url = self.local_url
        url = target_url.rstrip("/") + "/health"
        headers = self._headers_for_url(url)
        owned = False
        if self._external_client is not None:
            client = self._external_client
        else:
            client = httpx.Client(timeout=min(5.0, self.timeout))
            owned = True

        try:
            resp = client.get(url, headers=headers, timeout=min(5.0, self.timeout))
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return {"status": "ok"}
            raise VoiceStudioError(
                self._sanitize(f"Health check failed at {url} with status {resp.status_code}: {resp.text[:200]}")
            )
        except Exception as e:
            if isinstance(e, VoiceStudioError):
                raise
            clean_err = self._sanitize(str(e))
            raise VoiceStudioError(f"Health check failed for {url}: {clean_err}") from e
        finally:
            if owned:
                client.close()

    def get_voices(self, target_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve available voices from /v1/audio/voices."""
        base = target_url or self._resolve_target()[0]
        url = base.rstrip("/") + "/v1/audio/voices"
        headers = self._headers_for_url(url)
        owned = False
        if self._external_client is not None:
            client = self._external_client
        else:
            client = httpx.Client(timeout=self.timeout)
            owned = True

        try:
            resp = client.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                raise VoiceStudioError(
                    self._sanitize(f"Failed to fetch voices from {url}: status {resp.status_code}")
                )
            data = resp.json()
            if isinstance(data, dict) and "voices" in data:
                return data["voices"]
            elif isinstance(data, list):
                return data
            return []
        except Exception as e:
            if isinstance(e, VoiceStudioError):
                raise
            clean_err = self._sanitize(str(e))
            raise VoiceStudioError(f"Failed to get voices from {url}: {clean_err}") from e
        finally:
            if owned:
                client.close()

    def _resolve_target(self) -> Tuple[str, bool]:
        """Resolve target base URL based on mode.
        
        Auto mode: checks Local first; if unavailable, checks Remote.
        Returns (base_url, is_remote).
        Raises VoiceStudioUnavailableError if no target is available.
        """
        if self.mode == "local":
            try:
                self.check_health(self.local_url)
                return self.local_url, False
            except Exception as e:
                raise VoiceStudioUnavailableError(
                    f"Local VoiceStudio unavailable at {self.local_url}: {e}"
                ) from e

        if self.mode == "remote":
            try:
                self.check_health(self.remote_url)
                return self.remote_url, True
            except Exception as e:
                raise VoiceStudioUnavailableError(
                    f"Remote VoiceStudio unavailable at {self.remote_url}: {self._sanitize(str(e))}"
                ) from e

        # Auto mode: try Local first, then Remote
        try:
            self.check_health(self.local_url)
            return self.local_url, False
        except Exception:
            pass

        try:
            self.check_health(self.remote_url)
            return self.remote_url, True
        except Exception as e:
            raise VoiceStudioUnavailableError(
                f"VoiceStudio unavailable: neither Local ({self.local_url}) nor Remote ({self.remote_url}) is reachable."
            ) from e

    def synthesize(
        self,
        input_text: str,
        voice: str = "alloy",
        model: str = "omnivoice",
        language: str = "en",
        response_format: str = "wav",
        style: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> bytes:
        """Synthesize text into WAV audio using the resolved VoiceStudio endpoint.
        
        Invariants:
        - Auto resolution happens ONCE before synthesis. No engine or target fallback during/after.
        - Validates returned bytes as valid WAV with non-zero duration. Rejects invalid audio.
        - Retries only transient errors with bounded count.
        - Cancellation immediately aborts request and raises CancelledError.
        - Sensitive credentials never leak into exceptions.
        """
        if not input_text or not input_text.strip():
            raise ValueError("Input text for synthesis cannot be empty.")

        if cancellation_token:
            cancellation_token.check_cancelled()

        # Step 1: Resolve endpoint strictly before synthesis
        target_url, is_remote = self._resolve_target()
        speech_url = f"{target_url}/v1/audio/speech"
        headers = self._headers_for_url(speech_url)
        payload: Dict[str, Any] = {
            "model": model,
            "input": input_text,
            "voice": voice,
            "response_format": response_format,
            "language": language,
        }
        if style:
            payload["description"] = style

        # Step 2: Bounded retry loop for transient errors
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            if cancellation_token:
                cancellation_token.check_cancelled()

            client = self._get_client()

            try:
                # Cancel-aware streaming request
                with client.stream("POST", speech_url, json=payload, headers=headers, timeout=self.timeout) as resp:
                    if resp.status_code != 200:
                        body = resp.read().decode("utf-8", errors="replace")[:300]
                        clean_body = self._sanitize(body)
                        # Distinguish transient vs logical errors
                        if resp.status_code in TRANSIENT_STATUS_CODES:
                            raise httpx.HTTPStatusError(
                                f"Transient HTTP {resp.status_code}: {clean_body}",
                                request=resp.request,
                                response=resp,
                            )
                        # Logical error: fail immediately, do not retry
                        raise VoiceStudioError(
                            f"VoiceStudio synthesis rejected (HTTP {resp.status_code}): {clean_body}"
                        )

                    # Stream bytes while checking cancellation
                    chunks: List[bytes] = []
                    for chunk in resp.iter_bytes():
                        if cancellation_token and cancellation_token.is_cancelled:
                            resp.close()
                            raise CancelledError("VoiceStudio synthesis cancelled during stream.")
                        if chunk:
                            chunks.append(chunk)

                    wav_bytes = b"".join(chunks)

                # Step 3: Validate WAV format and duration
                validate_wav_bytes(wav_bytes)
                return wav_bytes

            except CancelledError:
                raise
            except VoiceStudioError as e:
                # Logical error, do not retry
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
                # Transient error: retry if attempts remain
                last_exception = e
                clean_err = self._sanitize(str(e))
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    if cancellation_token:
                        # Sleep in small increments to remain cancel-aware
                        end_time = time.monotonic() + sleep_time
                        while time.monotonic() < end_time:
                            cancellation_token.check_cancelled()
                            time.sleep(0.05)
                    else:
                        time.sleep(sleep_time)
                    continue
                else:
                    raise VoiceStudioUnavailableError(
                        f"VoiceStudio synthesis failed after {self.max_retries + 1} attempts: {clean_err}"
                    ) from e
            except Exception as e:
                # Catch any unexpected failure, sanitize and re-raise without credential leakage
                clean_err = self._sanitize(str(e))
                raise VoiceStudioError(f"Unexpected error during synthesis: {clean_err}") from e

        if last_exception:
            raise VoiceStudioUnavailableError(
                f"VoiceStudio synthesis failed after retries: {self._sanitize(str(last_exception))}"
            )
        raise VoiceStudioUnavailableError("VoiceStudio synthesis failed: retries exhausted.")
