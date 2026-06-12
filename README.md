# 🎙️ music-stem-separation

A best-quality, **cross-platform** (Windows / macOS / Linux) pipeline for pulling a clean, **dropout-free dry vocal** out of mixed music — plus the instrumental, harmonies, and extracted reverb along the way.

It avoids aggressive single models (which cause "vocal dropouts" where notes get eaten) by combining multi-model **ensembles** with light physical EQ. All OS-specific logic lives in one Python driver, so the same command works everywhere.

It ships both as a standalone script and as an **AI-agent skill** (`SKILL.md`) you can drop into Claude Code / other agents.

---

## ✅ Prerequisites

> **Read this first.** The pipeline needs three things on your `PATH`: **Python**, **ffmpeg**, and **`audio-separator`**. Models download automatically on first run.

| Requirement | Why | Windows | macOS | Linux |
|---|---|---|---|---|
| **Python ≥ 3.10** | runs the driver | `winget install -e --id Python.Python.3.12` | `brew install python` | `apt install python3` (or distro pkg) |
| **[uv](https://github.com/astral-sh/uv)** | installs `audio-separator` cleanly | `winget install -e --id astral-sh.uv` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **ffmpeg** | format conversion + de-essing | `winget install -e --id Gyan.FFmpeg` | `brew install ffmpeg` | `apt install ffmpeg` / `dnf install ffmpeg` / `pacman -S ffmpeg` |
| **audio-separator** | the separation engine | see below | see below | see below |

### Install `audio-separator` (pick the right extra for your hardware)

```bash
# NVIDIA GPU (Windows / Linux with CUDA) — fastest:
uv tool install "audio-separator[gpu]"

# macOS (Apple Silicon or Intel), or any machine without an NVIDIA GPU:
uv tool install "audio-separator[cpu]"
```

- **GPU is optional but strongly recommended.** `audio-separator` auto-selects the accelerator at runtime — **CUDA** on NVIDIA, **CoreML/MPS** on Apple Silicon, **CPU** fallback otherwise. No device flags needed.
- **CPU works but is slow** (minutes per stage on long tracks).

### Hardware / disk notes

- **Disk:** the ensemble models total **~5–6 GB**. They download on first use into a persistent cache (default `~/models/audio-separator-models`) so they're fetched only once.
- **RAM/VRAM:** 8 GB system RAM is comfortable; 6 GB+ VRAM helps on GPU but is not required.
- **Network:** first run downloads the models — allow time / bandwidth.

---

## 🚀 Usage

### As a standalone script

```bash
# macOS / Linux
python scripts/separate.py --input "/path/to/song.flac" --song "My Song"
```

```powershell
# Windows (PowerShell)
python scripts\separate.py --input "C:\path\to\song.mp3" --song "My Song"
```

| Flag | Default | Meaning |
|---|---|---|
| `--input` | *(required)* | Source audio — any format ffmpeg can read (mp3, flac, m4a, wav…). |
| `--song` | *(required)* | Used for the output folder and temp file names. |
| `--outdir` | `~/Music/<song>/干声分离` | Where results go. |
| `--models-dir` | `~/models/audio-separator-models` | Persistent model cache. |
| `--keep-temp` | off | Keep intermediate folders for debugging. |

### As an AI-agent skill

Copy this folder into your agent's skills directory and the agent can run it on request:

- **Claude Code:** `~/.claude/skills/music-stem-separation/`
- **Other agents (`.agents` convention):** `~/.agents/skills/music-stem-separation/`

`SKILL.md` carries the trigger phrases (e.g. `stem separation`, `vocal isolation`, `干声分离`, `去混响`).

---

## 🧪 How it works (4 ensemble stages)

`demucs` is intentionally **not** used — it tends to drop vocals aggressively. Each stage runs an `avg_fft` ensemble of two models:

| Step | Purpose | Main model | + Ensemble model |
|---|---|---|---|
| 0 | Normalize input → 44.1 kHz / 16-bit WAV | *(ffmpeg)* | — |
| 1 | Vocal extraction, no dropouts | `model_bs_roformer_ep_368_sdr_12.9628` | `MDX23C-8KFFT-InstVoc_HQ` |
| 2 | Remove backing harmonies (karaoke) | `mel_band_roformer_karaoke_aufr33_viperx` | `UVR_MDXNET_KARA_2` |
| 3 | Gentle dereverb | `UVR-DeEcho-DeReverb` | `Reverb_HQ_By_FoxJoy` |
| 4 | Ultra-light de-essing (physical EQ) | *(ffmpeg `deesser` + gentle high-shelf cut)* | — |

### Output

```
~/Music/<song>/干声分离/
├── 1_伴奏.wav                          # instrumental
├── 1_全人声_含和声混响.wav             # all vocals (harmonies + reverb)
├── 2_和声.wav                          # backing harmonies
├── 2_纯主唱_含混响.wav                 # lead vocal (still wet)
├── 3_被抽离的混响.wav                  # extracted reverb
├── 3_纯主唱_已去混响_未去刺.wav        # lead vocal, dereverbed
└── 4_终极干声_全集成保真去刺版.wav     # ← final deliverable (dry, de-essed)
```

> Output names are in Chinese by design; pass `--outdir` to control the location. Filenames are UTF-8 and work on all platforms.

---

## 🙏 Credits & licensing of models

This tool is a thin orchestration layer. The heavy lifting is done by:

- **[python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator)** — the separation engine and model downloader.
- The separation **models** (BS-Roformer, MDX23C, Mel-Band-Roformer karaoke by **aufr33 / viperx**, UVR-DeEcho-DeReverb, Reverb_HQ by **FoxJoy**, etc.) are created by the **[UVR / MVSEP](https://github.com/Anjok07/ultimatevocalremovergui) community** and carry **their own licenses**. They are downloaded at runtime and are **not** redistributed in this repository. Review each model's terms before commercial use.

The MIT license below covers **only the code in this repo** (the driver script and docs), not the models.

---

## 📄 License

[MIT](LICENSE) © 2026 jianga0801-ui
