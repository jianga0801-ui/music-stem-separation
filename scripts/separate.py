#!/usr/bin/env python3
"""
Cross-platform high-fidelity vocal stem separation pipeline.

Wraps `audio-separator` (ensemble models) + `ffmpeg` into a 4-step pipeline
that extracts a clean, dropout-free *dry* vocal from mixed audio. Runs
identically on Windows, macOS, and Linux — every OS-specific bit (paths,
directory creation, file moves, cleanup) is handled here in Python via
pathlib / subprocess / shutil instead of shell-specific commands.

GPU acceleration is auto-detected by `audio-separator` itself (CUDA on
NVIDIA Win/Linux, CoreML/MPS on Apple Silicon, CPU fallback elsewhere), so
no device flags are passed here. See SKILL.md for prerequisites and the
per-OS install of ffmpeg + audio-separator.

Usage:
    python separate.py --input /path/to/song.flac --song "歌名"
    python separate.py --input C:\\path\\to\\song.mp3 --song "歌名" --keep-temp
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODELS = Path.home() / "models" / "audio-separator-models"

# Ensemble model pairs per stage. Identical on every OS — do not change these
# without re-validating the pipeline; demucs is intentionally avoided because
# it is prone to aggressive vocal dropouts.
VOCAL_MAIN = "model_bs_roformer_ep_368_sdr_12.9628.ckpt"
VOCAL_EXTRA = "MDX23C-8KFFT-InstVoc_HQ.ckpt"
KARAOKE_MAIN = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
KARAOKE_EXTRA = "UVR_MDXNET_KARA_2.onnx"
DEREVERB_MAIN = "UVR-DeEcho-DeReverb.pth"
DEREVERB_EXTRA = "Reverb_HQ_By_FoxJoy.onnx"


def run(cmd: list) -> None:
    """Run a subprocess, echoing the command. Raises on non-zero exit."""
    printable = " ".join(str(c) for c in cmd)
    print(f"» {printable}", flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def require(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(
            f"ERROR: '{tool}' is not on PATH. Install it first "
            f"(see this skill's SKILL.md > Prerequisites)."
        )


def separate(src: Path, models: Path, tmp: Path, main: str, extra: str) -> None:
    """One ensemble separation pass into a clean temp dir."""
    for stale in tmp.glob("*.wav"):          # avoid cross-stage contamination
        stale.unlink()
    run([
        "audio-separator", src,
        "--model_file_dir", models,
        "-m", main,
        "--extra_models", extra,
        "--ensemble_algorithm", "avg_fft",
        "--output_format", "WAV",
        "--output_dir", tmp,
    ])


def take(tmp: Path, patterns: list, dest: Path) -> None:
    """Move the first file in `tmp` matching any glob pattern to `dest`.

    Multiple patterns cover case differences in model output names on
    case-sensitive filesystems (Linux).
    """
    for pat in patterns:
        hits = sorted(tmp.glob(pat))
        if hits:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(hits[0]), str(dest))
            print(f"  → {dest.name}")
            return
    print(f"  ! no output matched {patterns} (expected {dest.name})", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="High-fidelity vocal stem separation (cross-platform).",
    )
    ap.add_argument("--input", required=True,
                    help="Source audio file (any format ffmpeg can read).")
    ap.add_argument("--song", required=True,
                    help="Song name — used for the output folder and temp file naming.")
    ap.add_argument("--outdir", default=None,
                    help="Output folder. Default: ~/Music/<song>/干声分离")
    ap.add_argument("--models-dir", default=str(DEFAULT_MODELS),
                    help=f"Persistent model cache. Default: {DEFAULT_MODELS}")
    ap.add_argument("--keep-temp", action="store_true",
                    help="Keep the intermediate _临时_* folders instead of deleting them.")
    args = ap.parse_args()

    require("ffmpeg")
    require("audio-separator")

    src = Path(args.input).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"ERROR: input not found: {src}")

    outdir = (Path(args.outdir).expanduser() if args.outdir
              else Path.home() / "Music" / args.song / "干声分离")
    models = Path(args.models_dir).expanduser()
    workdir = outdir / "_临时_input"
    tmp = outdir / "_临时_ensemble"
    for d in (outdir, models, workdir, tmp):
        d.mkdir(parents=True, exist_ok=True)

    # Step 0 — normalize to 44.1 kHz / 16-bit WAV
    print("\n[0/4] Ensuring WAV input …")
    input_wav = workdir / f"{args.song}.wav"
    run(["ffmpeg", "-y", "-i", src, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", input_wav])

    # Step 1 — ensemble vocal extraction (no dropouts)
    print("\n[1/4] Ensemble vocal extraction …")
    separate(input_wav, models, tmp, VOCAL_MAIN, VOCAL_EXTRA)
    full_vocals = outdir / "1_全人声_含和声混响.wav"
    take(tmp, ["*_(Vocals)_*.wav"], full_vocals)
    take(tmp, ["*_(Instrumental)_*.wav"], outdir / "1_伴奏.wav")

    # Step 2 — ensemble harmony removal (karaoke)
    print("\n[2/4] Ensemble harmony removal …")
    separate(full_vocals, models, tmp, KARAOKE_MAIN, KARAOKE_EXTRA)
    lead_wet = outdir / "2_纯主唱_含混响.wav"
    take(tmp, ["*_(Vocals)_*.wav"], lead_wet)
    take(tmp, ["*_(Instrumental)_*.wav"], outdir / "2_和声.wav")

    # Step 3 — gentle dereverb
    print("\n[3/4] Gentle dereverb …")
    separate(lead_wet, models, tmp, DEREVERB_MAIN, DEREVERB_EXTRA)
    lead_dry = outdir / "3_纯主唱_已去混响_未去刺.wav"
    take(tmp,
         ["*_(No Reverb)_*.wav", "*_(no reverb)_*.wav",
          "*_(noreverb)_*.wav", "*_(No_Reverb)_*.wav"],
         lead_dry)
    take(tmp, ["*_(Reverb)_*.wav", "*_(reverb)_*.wav"], outdir / "3_被抽离的混响.wav")

    # Step 4 — ultra-light de-essing (physical EQ)
    print("\n[4/4] Ultra-light de-essing …")
    final = outdir / "4_终极干声_全集成保真去刺版.wav"
    run(["ffmpeg", "-y", "-i", lead_dry,
         "-af", "deesser=i=0.2,treble=g=-1:f=7500:w=1", final])

    # Cleanup
    if not args.keep_temp:
        for d in (tmp, workdir):
            shutil.rmtree(d, ignore_errors=True)

    print(f"\n✅ Done. Final dry vocal: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
