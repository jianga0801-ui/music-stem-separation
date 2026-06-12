---
name: music-stem-separation
description: "Cross-platform AI music stem separation pipeline (Windows/macOS/Linux): vocal isolation, harmony splitting, and reverb removal via an ultra-high-fidelity audio-separator ensemble, with GPU acceleration where available."
tags: [audio, music, stem-separation, vocals, audio-separator, dereverb, ensemble, cross-platform, windows, macos, linux]
triggers:
  - stem separation
  - vocal isolation
  - extract vocals
  - remove vocals
  - separate instruments
  - 干声分离
  - 人声分离
  - 去混响
  - dereverb
---

# Music Stem Separation Pipeline (cross-platform)

Best-quality ensemble pipeline for extracting clean, dropout-free dry vocals from mixed audio. It avoids aggressive single models (which cause "vocal dropouts") by combining multi-model ensembles with light physical EQ. Runs identically on **Windows, macOS, and Linux** — all OS-specific logic lives in the bundled `scripts/separate.py`, so the agent only needs to install the prerequisites and run one command.

## Prerequisites

| Requirement | Windows | macOS | Linux |
|---|---|---|---|
| Python 3.10+ | `winget install -e --id Python.Python.3.12` | `brew install python` | distro package (e.g. `apt install python3`) |
| `uv` package manager | `winget install -e --id astral-sh.uv` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| ffmpeg | `winget install -e --id Gyan.FFmpeg` | `brew install ffmpeg` | `apt install ffmpeg` / `dnf install ffmpeg` / `pacman -S ffmpeg` |

### Install audio-separator (choose the right extra for your hardware)

```bash
# NVIDIA GPU (Windows / Linux with CUDA) — fastest:
uv tool install "audio-separator[gpu]"

# macOS (Apple Silicon or Intel), or any machine without an NVIDIA GPU:
uv tool install "audio-separator[cpu]"
```

`audio-separator` **auto-selects** the accelerator at runtime — CUDA on NVIDIA, CoreML/MPS on Apple Silicon, CPU otherwise — so no device flags are needed. GPU is strongly recommended; CPU works but is very slow.

### Model storage (important pitfall)

By default `audio-separator` caches models under the system temp dir, which the OS may clear. **Always** keep them in a persistent folder. The script defaults to `~/models/audio-separator-models` (works on every OS) and passes `--model_file_dir` for you. Override with `--models-dir` if you want a different location. Models download automatically on first use.

## Quick start

Run the bundled cross-platform driver (`<SKILL_DIR>` = this skill's folder):

```bash
# macOS / Linux
python "<SKILL_DIR>/scripts/separate.py" --input "/path/to/song.flac" --song "歌名"
```

```powershell
# Windows (PowerShell)
python "<SKILL_DIR>\scripts\separate.py" --input "C:\path\to\song.mp3" --song "歌名"
```

Options: `--outdir <dir>` (default `~/Music/<song>/干声分离`), `--models-dir <dir>`, `--keep-temp` (retain intermediate folders for debugging). The input may be any format ffmpeg can read; it is normalized to WAV automatically.

## What the pipeline does (4 ensemble stages)

To stop the AI from "eating" or dropping notes, this skips `demucs` entirely and relies on robust ensembles (`--ensemble_algorithm avg_fft`). The script runs these stages; the model names are identical on every OS:

| Step | Purpose | Main model | + Ensemble model |
|---|---|---|---|
| 0 | Normalize input → 44.1 kHz / 16-bit WAV | *(ffmpeg)* | — |
| 1 | Vocal extraction, no dropouts | `model_bs_roformer_ep_368_sdr_12.9628.ckpt` | `MDX23C-8KFFT-InstVoc_HQ.ckpt` |
| 2 | Remove backing harmonies (karaoke) | `mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt` | `UVR_MDXNET_KARA_2.onnx` |
| 3 | Gentle dereverb | `UVR-DeEcho-DeReverb.pth` | `Reverb_HQ_By_FoxJoy.onnx` |
| 4 | Ultra-light de-essing (physical EQ) | *(ffmpeg `deesser` + gentle high-shelf cut)* | — |

The exact `audio-separator` invocation per stage is:

```bash
audio-separator "<input>.wav" \
  --model_file_dir "<models-dir>" \
  -m "<main model>" \
  --extra_models "<ensemble model>" \
  --ensemble_algorithm avg_fft \
  --output_format WAV \
  --output_dir "<temp-dir>"
```

and the final de-essing pass:

```bash
ffmpeg -y -i "3_纯主唱_已去混响_未去刺.wav" \
  -af "deesser=i=0.2,treble=g=-1:f=7500:w=1" \
  "4_终极干声_全集成保真去刺版.wav"
```

## Output organization

```
Music/
  └── <歌名>/
        └── 干声分离/
              1_伴奏.wav
              1_全人声_含和声混响.wav
              2_和声.wav
              2_纯主唱_含混响.wav
              3_被抽离的混响.wav
              3_纯主唱_已去混响_未去刺.wav
              4_终极干声_全集成保真去刺版.wav    ← Final deliverable
```

## Rules

1. **Project folder**: outputs go to `Music/<歌名>/干声分离/` (override with `--outdir`).
2. **Format**: all inputs/outputs are strictly **WAV** (`--output_format WAV`); the script auto-converts the source input first.
3. **No Demucs**: never use demucs — it aggressively drops vocals. Stick to the `audio-separator` ensemble pipeline.
4. **Persistent models**: always use a stable `--models-dir` (default `~/models/audio-separator-models`) so models aren't re-downloaded into a temp dir and erased.
5. **Cleanup**: the script removes `_临时_*` folders on success; pass `--keep-temp` to keep them when debugging.
