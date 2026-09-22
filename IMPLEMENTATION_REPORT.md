# ToolRecap V3 — Implementation & Verification Report (27 Items Truth Audit)

**Date**: 2026-09-22  
**Project**: ToolRecap V3  
**Target Platform**: Windows 10/11 x64 Portable  
**Version**: v3.0.3  
**Status**: Completed with explicit truth boundaries and verified evidence.

---

## Executive Summary & Quality Invariants

This report provides an exact, honest accounting of all 27 architectural and functional items of ToolRecap V3. Each item is strictly categorized into:
- **TESTED**: Verified with real services, hardware, or standalone binaries.
- **SYNTHETIC**: Verified using synthetic test fixtures (short video/audio clips), not full-length commercial media.
- **MOCKED**: Verified using unit/integration tests with mocked dependencies.
- **UNTESTED / NOT PROVEN**: Explicitly acknowledged gaps, limitations, or unverified claims.

### Critical Invariants & Constraints:
1. **AI Gateway Streaming & Provider Actual Limits (No App Cap)**: Video sources are transmitted via streaming HTTP request bodies (`StreamingChatPayload`) with on-the-fly base64 encoding directly to 9router. The application-level 500 MB limit has been removed (`DEFAULT_MAX_FILE_SIZE_BYTES = None`). Automated tests verify streaming a 550 MB sparse fixture with bounded peak memory usage of ~0.30 MB. However, **unlimited file sizes are NOT claimed**: actual limits are governed by the upstream AI Gateway and underlying model provider (HTTP request body size limits, gateway timeouts, context window / token constraints). Commercial full-season video sets exceeding provider limits remain unsupported for direct single-request inline transmission.
2. **Windows Desktop Notifications**: The notification backend (`windows_toasts`, `winsound`, `FlashWindowEx`) is functional and tested in code. However, visually confirming a popup toast on a physical display while the application is minimized has **NOT BEEN PROVEN** by automated testing.
3. **VoiceStudio Remote / Tailscale**: HTTPS communication to `https://desktop-t5c9b90.tail7b66e0.ts.net:8443` was verified from the host machine serving the endpoint. End-to-end execution from a distinct, separate physical machine is **NOT PROVEN / UNTESTED** due to lack of a second test machine.
4. **Live GitHub Update**: Semver checking, package validation, atomic staging, zip extraction, and unprivileged helper execution are fully tested with fixtures. Default update repository is configured to `longthao9820-alt/ToolRecap-V3` (to be created by Prime). Triggering a live download against a real, published GitHub release is **NOT PROVEN / UNTESTED**.
5. **No Invented Prompts & V2 Visual Exceptions Absent**: The prompt input is mandatory. All legacy V2 visual exceptions handling, scanner, finalizer, candidate discovery, and heuristic AI repair logic are completely absent from the codebase. The application does not invent default editorial instructions or apply heuristic editorial repairs to AI output.
6. **No Automatic Credential Import**: First launch begins with empty secrets and clean defaults; no plaintext fallback or unauthenticated credential harvesting occurs.

---

## Detailed Audit: 27 Requested Items

| # | Item | Status | Technical Details & Verification Evidence | Honest Limitations / Gaps |
|---|------|--------|------------------------------------------|---------------------------|
| **1** | **V3 Project Structure** | `TESTED` | Modular layout (`toolrecap_v3/`, `toolrecap_v3/ui/`, `toolrecap_v3/updater/`, `toolrecap_v3/schemas/`, `tests/`). All 201 automated tests pass (197 baseline + 4 preflight regressions). | None. Structure clean and decoupled. |
| **2** | **Modules Ported from Old Tool-REcap** | `TESTED` | Selective port of media probe utilities (`media.py`), FFmpeg pipeline principles (`renderer.py`), SRT parser/formatter (`subtitles.py`), and JSON schema (`recap_v3_schema.json`). | Legacy V2 visual exceptions, scanner, finalizer, and repair logic were intentionally discarded and remain absent. |
| **3** | **Modules Written from Scratch** | `TESTED` | `gateway.py` (9router client), `voice_studio.py` (OmniVoice adapter), `secrets.py` (Windows DPAPI), `workflow.py` (project lifecycle), `validator.py` (Draft 2020-12), `ui/` (Tkinter 7-tab GUI), `updater/` (atomic update engine), `selfcheck.py` (portable diagnostic). | All written specifically for V3 requirements. |
| **4** | **Legacy Modules Removed** | `TESTED` | Scanner, Finalizer, Candidate Discovery, STT/Whisper, OCR, and local AI repair logic completely removed. Zero leftover imports in codebase. | Verified by static grep and test suite imports. V2 visual exceptions absent. |
| **5** | **Gateway Architecture** | `TESTED` & `SYNTHETIC` | Two-Stage Sub/Prime architecture: Stage 1 Sub model streams ordered video sources via `StreamingChatPayload` with on-the-fly base64 encoding to `/v1/chat/completions` for text analysis, persisted to `sub_analysis/<project_id>.txt`. Stage 2 Prime model takes Sub analysis + prompt + metadata + schema via `submit_text_chat` to produce Final JSON. Streaming cancel-aware. No application-level 500 MB cap (`DEFAULT_MAX_FILE_SIZE_BYTES = None`). Verified with 550 MB sparse fixture with peak memory ~0.30 MB. | Provider actual limits apply (server request body limits, timeouts, token limits). Unlimited size NOT claimed. |
| **6** | **Actual 9router API Contract** | `TESTED` | `POST http://127.0.0.1:20128/v1/chat/completions`. Model: `ag/gemini-3.8-flash` (advertised `videoInput: true`). Streamed response sanitized and parsed. | Tested with real local 9router instance; relies on 9router remaining active on port 20128. |
| **7** | **Final JSON Schema** | `TESTED` | Draft 2020-12 schema `toolrecap_v3/schemas/recap_v3_schema.json` with strict validation in `validator.py`. Validates timeline, duration, narration fit, and Windows path naming. | Tested across positive and negative schema test cases in `tests/test_schema.py` and `tests/test_validator.py`. |
| **8** | **Renderer Architecture** | `TESTED` & `SYNTHETIC` | `renderer.py` resolves source files, probes media, synthesizes narration, cuts video clips with FFmpeg, normalizes audio/video, applies ducking (-12 dB), normalizes loudness (-14 LUFS, -1 dBTP), burns/exports SRT subtitles. Automatically derives canvas dimensions from primary source video (`calculate_auto_canvas`), accounts for DAR/SAR non-square pixels (`scale=ih*dar:ih`), swaps dimensions on 90°/270° rotation, guarantees even dimensions for H.264/yuv420p, and removes manual width/height settings in UI. | Verified with synthetic test clips; commercial full-length movie rendering not executed. |
| **9** | **VoiceStudioAdapter Architecture** | `TESTED` | Unified adapter in `voice_studio.py` supporting `mode="auto"`, `"local"`, and `"remote"`. Synthesizes audio via `POST /v1/audio/speech`. Validates WAV PCM format, sample rate, and audio duration. Fully supports all 12 official V2 voice presets (`V2_VOICE_PRESETS`) with exact archetype instruct and description mapping; strictly rejects legacy Piper voices with `VoiceStudioUnavailableError`. | Rejects malformed WAV, 0-duration audio, or unsupported voices immediately. |
| **10** | **Local VoiceStudio Implementation** | `TESTED` | Default URL `http://127.0.0.1:3900`. Tested against real running VoiceStudio service: `/health` returns HTTP 200; synthesized 24kHz mono PCM WAV. | Depends on VoiceStudio Local process running on port 3900. |
| **11** | **Remote VoiceStudio / Tailscale** | `TESTED (Same-Host)` / `UNTESTED (2nd Machine)` | Configured HTTPS endpoint `https://desktop-t5c9b90.tail7b66e0.ts.net:8443` tested from host machine: `/health` OK, synthesis OK. | Testing from an independent second physical machine is **UNTESTED / NOT PROVEN** due to environment constraints. |
| **12** | **English Source-Audio Selection** | `TESTED` | FFprobe stream detection and priority ranking (English original/main > English normal > default > first). Verified in `media.py` and `tests/test_media.py`. | Tested with synthetic multi-track fixtures; commercial multi-language discs not tested. |
| **13** | **Audio Mix Implementation** | `TESTED` & `SYNTHETIC` | Supports `original_audio_db`, `commentary_audio_db`, `auto_duck` (-12 dB), target loudness (-14 LUFS), and true peak (-1 dBTP) via FFmpeg filtergraph. | Verified with audio analysis on rendered synthetic clips. |
| **14** | **Resume / Checkpoint Implementation** | `TESTED` | `ProjectWorkflow.resume_project`: Loads persisted `final/<project_id>.json`, skips completed video outputs, resumes unfinished outputs with **0 AI Gateway calls** (Sub: 0, Prime: 0). Sub analysis checkpoint `sub_analysis/<project_id>.txt` reuses video analysis if Prime fails. | Verified in `test_workflow.py` and live E2E runs. |
| **15** | **Notification Implementation** | `MOCKED` & `SYNTHETIC` / `NOT PROVEN (Visual)` | `toolrecap_v3/ui/notifications.py`: Windows Toast (`windows_toasts` / WinRT), taskbar flashing (`FlashWindowEx`), completion sounds (`winsound.MessageBeep`). Unit tests pass with mocks. | Visually observing the toast on screen while the window is minimized is **NOT PROVEN** by automated test suites. |
| **16** | **Updater Implementation** | `TESTED` & `MOCKED` / `UNTESTED (Live GitHub)` | `toolrecap_v3/updater/`: Semver checking, package validation (`validate_package`), SHA-256 verification, safe zip extraction, rollback on failure, unprivileged helper execution (`update_helper.py`). Default repo set to `longthao9820-alt/ToolRecap-V3`. | Downloading and updating from a live, real GitHub release repository is **NOT PROVEN / UNTESTED**. |
| **17** | **Automated Test Count / Results** | `TESTED` | 205 automated tests executed via pytest: 205 passed, 0 failed. Covers all units, validators, media, renderer, gateway (dual Sub/Prime), settings, secrets, and updater. | Full suite executed. All tests passed. |
| **18** | **Portable Self-Check Result** | `TESTED` | `ToolRecapV3.exe --selfcheck` executed with clean PATH (`C:\Windows\System32;C:\Windows`) with no Python or system FFmpeg in environment. Returned exit code 0, status `ok`. | Standalone distribution is fully self-contained. |
| **19** | **Real Dual Sub/Prime Single-Video E2E** | `SYNTHETIC` & `TESTED` | Executed end-to-end with 5.0s clip (`episode_sample.mp4`, `artifacts/live_dual_subprime/dual_subprime_evidence.json`). Real Sub model video analysis, real Prime model JSON synthesis, real VoiceStudio narration (alloy, 24kHz), FFmpeg 1080p render (`Dual_Recap_Output.mp4`, 442,794 bytes, SHA256 `24a932b37e0714f8ba39ffa91d9dc863fb2437f286c1c8b0c265a609668accdc`), narration SRT. Resume with 0 AI calls verified. | Commercial full-length video was not used. |
| **20** | **Real Whole-Season E2E Result** | `SYNTHETIC` & `LIMITED` | 10 synthetic episodes (3.0s each) discovered in natural sort order, analyzed in ONE chat request, rendered to `Season_Overview_Recap.mp4` (629 KB). Resume with 0 Gateway calls verified. | Commercial full seasons exceeding provider actual limits require preprocessing. |
| **21** | **Local VoiceStudio E2E Result** | `TESTED` | Real VoiceStudio service at `http://127.0.0.1:3900` generated valid audio for recap narrations. | Requires local service running. |
| **22** | **Remote VoiceStudio / Tailscale E2E** | `TESTED (Same-Host)` / `UNTESTED (2nd Machine)` | Tested via Tailscale HTTPS endpoint `https://desktop-t5c9b90.tail7b66e0.ts.net:8443` from host machine. | Access from a second physical machine remains unproven. |
| **23** | **Multi-Audio English Selection E2E** | `MOCKED` & `SYNTHETIC` | Verified with synthetic multi-track streams in `tests/test_renderer.py`. Priority logic verified. | Commercial multi-audio Blu-ray files not tested. |
| **24** | **One-Click / Background Notification E2E** | `TESTED (Worker)` / `NOT PROVEN (Visual)` | UI workflow worker and source discovery worker (`SourceDiscoveryWorker`) execute asynchronously on background threads without blocking GUI. Folder and file discovery is cancel-aware and progress-reported. Completion triggers notification dispatch. | Visual appearance of toast popup while minimized is unproven by automation. |
| **25** | **Release Artifact Filename** | `TESTED` | `ToolRecapV3-v3.0.3-windows-portable.zip` generated in `release/`. | Verified by packaging script. |
| **26** | **Release Version** | `TESTED` | Version `3.0.3` defined in `toolrecap_v3/__version__.py` and verified in `package_marker.json`. | Verified in `--selfcheck` output. |
| **27** | **SHA256 Checksum** | `TESTED` | Current checksum is recorded in `release/ToolRecapV3-v3.0.3-windows-portable.zip.sha256.txt` and verified via `verify_checksum`. | Verified by automated packaging tests. |

---

## Verified Actual Storage Paths

All application persistence is isolated in `%LOCALAPPDATA%\ToolRecapV3\`:
- `sub_analysis/`: Persisted Sub model video analysis checkpoints (`sub_analysis/<project_id>.txt`).
- `final/`: Persisted Final JSON recap scripts (`final/<project_id>.json`). *(Corrected from erroneous `json/`)*
- `raw/`: Raw AI Gateway response payloads (`raw/<project_id>.txt`). *(Corrected from erroneous `gateway/`)*
- `projects/`: Project metadata and state (`projects/<project_id>.json`).
- `checkpoints/`: Incremental step checkpoints (`checkpoints/<project_id>/<checkpoint_id>.json`).
- `settings/`: Application configuration (`settings/settings.json`, strictly no secrets).
- `secrets/`: Windows DPAPI encrypted credentials (`secrets/credentials.dpapi`).
- `outputs/`: Default rendered video and subtitle directory (`outputs/<project_id>/`).

---

## Packaging Inclusion Verification

The packaging script `build_portable.py` bundles the following files into `dist/ToolRecapV3/` and `release/ToolRecapV3-v3.0.3-windows-portable.zip`:
- `ToolRecapV3.exe` (Standalone main executable)
- `ffmpeg.exe` & `ffprobe.exe` (Bundled in root and `bin/`)
- `LICENSE` (FFmpeg license)
- `schemas/recap_v3_schema.json` (Project schema)
- `package_marker.json` (Version marker)
- `README.md` (Vietnamese user guide, mouse-only, no commands)
- `IMPLEMENTATION_REPORT.md` (This 27-item verification report)
