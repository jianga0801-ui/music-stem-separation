# 🎙️ music-stem-separation

<p align="right"><a href="README.md">English</a> · <b>简体中文</b></p>

一套高音质、**全平台**（Windows / macOS / Linux）的人声分离管线，从混音中提取干净、**无吞音的纯干声** —— 同时还会顺带产出伴奏、和声、以及被抽离出来的混响。

它通过**多模型 ensemble（集成）** 加轻量物理 EQ，避免了激进单模型常见的「吞音」问题（音符被吃掉）。所有平台差异都收进了同一个 Python 驱动脚本，因此同一条命令在各系统通用。

本项目同时以**独立脚本**和 **AI agent 技能**（`SKILL.md`）两种形态提供，可直接放进 Claude Code 等 agent 使用。

---

## ✅ 前置条件

> **请先看这里。** 管线需要三样东西在你的 `PATH` 上：**Python**、**ffmpeg**、**`audio-separator`**。模型会在首次运行时自动下载。

| 依赖 | 用途 | Windows | macOS | Linux |
|---|---|---|---|---|
| **Python ≥ 3.10** | 运行驱动脚本 | `winget install -e --id Python.Python.3.12` | `brew install python` | `apt install python3`（或对应发行版包） |
| **[uv](https://github.com/astral-sh/uv)** | 干净地安装 `audio-separator` | `winget install -e --id astral-sh.uv` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **ffmpeg** | 格式转换 + 去齿音 | `winget install -e --id Gyan.FFmpeg` | `brew install ffmpeg` | `apt install ffmpeg` / `dnf install ffmpeg` / `pacman -S ffmpeg` |
| **audio-separator** | 分离引擎 | 见下方 | 见下方 | 见下方 |

### 安装 `audio-separator`（按你的硬件选对应的 extra）

```bash
# NVIDIA 显卡（Windows / Linux + CUDA）—— 最快：
uv tool install "audio-separator[gpu]"

# macOS（Apple Silicon 或 Intel），或任何没有 NVIDIA 显卡的机器：
uv tool install "audio-separator[cpu]"
```

- **GPU 可选但强烈推荐。** `audio-separator` 运行时会**自动选择**加速后端 —— NVIDIA 用 **CUDA**，Apple Silicon 用 **CoreML/MPS**，其余回退 **CPU**，无需手动指定。
- **CPU 也能跑，但很慢**（长曲目每个阶段需数分钟）。

### 硬件 / 磁盘提示

- **磁盘：** ensemble 模型合计约 **5–6 GB**，首次使用时下载到持久缓存目录（默认 `~/models/audio-separator-models`），只下一次。
- **内存/显存：** 系统内存 8 GB 较为宽裕；GPU 上 6 GB+ 显存更佳，但非必需。
- **网络：** 首次运行会下载模型，请预留时间和带宽。

---

## 🚀 使用方法

### 作为独立脚本

```bash
# macOS / Linux
python scripts/separate.py --input "/path/to/song.flac" --song "歌名"
```

```powershell
# Windows（PowerShell）
python scripts\separate.py --input "C:\path\to\song.mp3" --song "歌名"
```

| 参数 | 默认值 | 含义 |
|---|---|---|
| `--input` | *（必填）* | 源音频 —— 任意 ffmpeg 能读的格式（mp3、flac、m4a、wav…）。 |
| `--song` | *（必填）* | 用于输出文件夹和临时文件命名。 |
| `--outdir` | `~/Music/<歌名>/干声分离` | 结果输出位置。 |
| `--models-dir` | `~/models/audio-separator-models` | 持久化模型缓存目录。 |
| `--keep-temp` | 关闭 | 保留中间文件夹以便调试。 |

### 作为 AI agent 技能

把本文件夹复制到 agent 的 skills 目录，agent 即可按需调用：

- **Claude Code：** `~/.claude/skills/music-stem-separation/`
- **其他 agent（`.agents` 约定）：** `~/.agents/skills/music-stem-separation/`

`SKILL.md` 中带有触发词（如 `stem separation`、`vocal isolation`、`干声分离`、`去混响`）。

---

## 🧪 工作原理（4 个 ensemble 阶段）

刻意**不使用** `demucs` —— 它容易激进地吞掉人声。每个阶段都用两个模型做 `avg_fft` 集成：

| 步骤 | 目的 | 主模型 | + 集成模型 |
|---|---|---|---|
| 0 | 输入归一化 → 44.1 kHz / 16-bit WAV | *(ffmpeg)* | — |
| 1 | 人声提取，无吞音 | `model_bs_roformer_ep_368_sdr_12.9628` | `MDX23C-8KFFT-InstVoc_HQ` |
| 2 | 去除背景和声（伴唱分离） | `mel_band_roformer_karaoke_aufr33_viperx` | `UVR_MDXNET_KARA_2` |
| 3 | 温和去混响 | `UVR-DeEcho-DeReverb` | `Reverb_HQ_By_FoxJoy` |
| 4 | 极轻度去齿音（物理 EQ） | *(ffmpeg `deesser` + 轻微高频搁架衰减)* | — |

### 输出

```
~/Music/<歌名>/干声分离/
├── 1_伴奏.wav                          # 伴奏
├── 1_全人声_含和声混响.wav             # 全部人声（含和声+混响）
├── 2_和声.wav                          # 背景和声
├── 2_纯主唱_含混响.wav                 # 主唱（仍带混响）
├── 3_被抽离的混响.wav                  # 抽离出的混响
├── 3_纯主唱_已去混响_未去刺.wav        # 主唱，已去混响
└── 4_终极干声_全集成保真去刺版.wav     # ← 最终成品（干声、已去齿音）
```

> 输出文件名为中文设计；用 `--outdir` 可控制输出位置。文件名为 UTF-8，全平台通用。

---

## 🙏 致谢与模型许可

本工具只是一层轻量编排，核心工作由以下项目完成：

- **[python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator)** —— 分离引擎与模型下载器。
- 分离**模型**（BS-Roformer、MDX23C、由 **aufr33 / viperx** 制作的 Mel-Band-Roformer 伴唱分离模型、UVR-DeEcho-DeReverb、**FoxJoy** 的 Reverb_HQ 等）由 **[UVR / MVSEP](https://github.com/Anjok07/ultimatevocalremovergui) 社区**创作，**各自带有独立许可证**。它们在运行时下载，**不随本仓库分发**。商用前请先查阅各模型条款。

下方的 MIT 许可证**仅覆盖本仓库的代码**（驱动脚本与文档），不包括模型。

---

## 📄 许可证

[MIT](LICENSE) © 2026 jianga0801-ui
