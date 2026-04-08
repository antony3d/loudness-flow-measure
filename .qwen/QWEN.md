# Loudness Flow Measure (LFM) — Project Context

## 📋 Overview

Audio loudness analysis tool compliant with **ITU-R BS.1770-4** and **EBU 3342** standards. Calculates integrated loudness (LUFS), loudness range (LRA), and multi-window dynamics analysis (Loudness Flow). Generates visual reports as PNG images.

**Version:** 0.7.1 (code) / 0.8.1 (docs)  
**Location:** `D:\Python\Loudness Flow Measure\`  
**Language:** Python 3.8+  
**Standards:** ITU-R BS.1770-4, EBU 3342

---

## 📁 Project Structure

```
D:\Python\Loudness Flow Measure\
├── lfm/                              # Core application directory
│   ├── lfm.py                        # Main application script (entry point)
│   ├── lfm.ini                       # Configuration file (settings & visualization)
│   ├── loudness_flow_report.txt      # OUTPUT: Text analysis report
│   └── ffmpeg/
│       ├── ffmpeg.exe                # DEPENDENCY: Audio decoder/encoder
│       └── ffprobe.exe               # DEPENDENCY: Audio metadata analyzer
│
├── 01 - Rehab.mp3                    # INPUT: Audio file (MP3)
├── bandicam 2024-07-22 11-38-09-678.mp4.2.wav  # INPUT: Audio file (WAV)
│
├── ds 01 - Rehab.png                 # OUTPUT: Loudness density chart
├── ds bandicam 2024-07-22 11-38-09-678.mp4.2.png  # OUTPUT: Loudness density chart
├── fl 01 - Rehab.png                 # OUTPUT: Loudness Flow chart
├── fl bandicam 2024-07-22 11-38-09-678.mp4.2.png  # OUTPUT: Loudness Flow chart
├── fl 01 - Rehab_vs_bandicam 2024-07-22 11-38-09-678.mp4.2.png  # OUTPUT: Overlay comparison
│
├── loudness_flow_report.txt          # OUTPUT: Text report (root copy)
├── loudness_flow_report.txt.bak      # OUTPUT: Backup of previous report
│
├── README.md                         # Documentation (English)
├── README.ru.md                      # Documentation (Russian)
└── .qwen/                            # IDE configuration
```

---

## 🔍 File Responsibilities

### Core Application Files

| File | Type | Path | Purpose |
|------|------|------|---------|
| `lfm.py` | Core Logic | `lfm/lfm.py` | Main Python script implementing: audio loading, K-filtering (BS.1770-4), LUFS/LRA calculation, True Peak detection, Loudness Flow analysis, visualization generation |
| `lfm.ini` | Config | `lfm/lfm.ini` | Settings for computation mode (LUFS/RMS), plot dimensions, density chart parameters, flow analysis windows (0.01-16s), colors, thresholds |

### Dependencies

| File | Type | Path | Purpose |
|------|------|------|---------|
| `ffmpeg.exe` | Binary | `lfm/ffmpeg/ffmpeg.exe` | Audio codec engine for decoding MP3/WAV/FLAC |
| `ffprobe.exe` | Binary | `lfm/ffmpeg/ffprobe.exe` | Audio metadata analyzer |

---

## 📥 Input Files

### Supported Formats
- `.wav` — WAV audio files
- `.mp3` — MP3 audio files
- `.flac` — FLAC audio files

### Example Input Files (in project root)
| File | Format | Description |
|------|--------|-------------|
| `01 - Rehab.mp3` | Audio (MP3) | Music track analyzed in the report |
| `bandicam 2024-07-22 11-38-09-678.mp4.2.wav` | Audio (WAV) | Screen recording audio track |

**Input source:** Command line argument or current directory (auto-discovery)

---

## 📤 Output Files

### Generated Automatically by `lfm.py`

| File | Pattern | Description |
|------|---------|-------------|
| Text Report | `loudness_flow_report.txt` | Analysis results: P10, Integrated LUFS, P95, LRA, True Peak, Digital Peak, Flow Avg, Top-3 Dominants |
| Report Backup | `loudness_flow_report.txt.bak` | Previous report backup (auto-created before new analysis) |
| Density Chart | `ds <name>.png` | Loudness density distribution histogram with P10/P95/Integrated markers |
| Flow Chart | `fl <name>.png` | Loudness Flow chart (dynamic range across time windows 0.01s-16s) |
| Overlay Chart | `fl <name1>_vs_<name2>.png` | Comparison of two tracks on single axis (only when exactly 2 files processed with `overlay_flow = yes`) |

**Output location:** Same directory as input audio files

---

## 🔄 Data Flow & Algorithm

```
1. Audio Loading (pydub + ffmpeg)
   ↓
2. K-filtering (Pre-filter 1500Hz + RLB 38.1Hz) [if LUFS mode]
   ↓
3. Peak Detection (True Peak with 2× oversampling + Digital Peak)
   ↓
4. LUFS Calculation (400ms windows, 100ms step, double gating per BS.1770-4)
   ↓
5. LRA Calculation (3s windows, P10/P95 with gating per EBU 3342)
   ↓
6. Top-3 Dominants (histogram of loudness levels by duration)
   ↓
7. Loudness Flow (geometric windows 0.01-16s, 12 logarithmic steps, P95-P10 spread)
   ↓
8. Visualization Generation (matplotlib → PNG charts with settings from lfm.ini)
   ↓
9. Delta Comparison (optional, name-based track comparison)
   ↓
10. Overlay Flow (optional, comparison chart for exactly 2 files)
   ↓
OUTPUT: report.txt + ds/*.png + fl/*.png
```

---

## 🛠 Key Code Components

### Classes

- **`ProgressBar`** — Terminal progress bar with percentage, visual indicator, and optional time remaining
  - Location: `lfm.py` lines ~77-125
  - Parameters: `desc`, `total`, `bar_len`, `fill_char`, `show_time`

### Core Functions

| Function | Purpose |
|----------|---------|
| `clean_name(filename)` | Filename normalization for delta comparison (removes prefixes/suffixes) |
| `k_filter(samples, sr)` | ITU-R BS.1770-4 K-weighting filter (Pre-filter High Shelf 1500Hz + RLB High Pass 38.1Hz) |
| `get_momentary_powers(channels, sr, window_sec, step_sec, show_progress)` | Windowed power calculation with overlap |
| `detect_peaks(channels, sr, oversample_factor=2)` | True Peak (2× oversampling via `resample_poly`) + Digital Peak detection |
| `calculate_integrated_lufs(powers)` | Double gating algorithm per BS.1770-4 (absolute threshold → relative threshold) |
| `process_audio(input_path)` | Main orchestration function: loads config, processes files, generates reports & visualizations |

### Constants

- `NAME = "Loudness Flow Measure"`
- `VERSION = "0.7.1"` (code version)
- `CURRENT_DIR` — Script directory path
- `FFMPEG_DIR` — Path to `ffmpeg/` folder
- `FFMPEG_PATH`, `FFPROBE_PATH` — Full paths to binaries

---

## 📊 Configuration (`lfm.ini`)

### [Main] Section
| Setting | Default | Description |
|---------|---------|-------------|
| `LoudnessMode` | `LUFS` | Computation mode: `LUFS` (weighted) or `RMS` |
| `show_time` | `no` | Show execution time |
| `verbose` | `no` | Extended logging |
| `delta_comparison` | `yes` | Compare tracks by name similarity |
| `overlay_flow` | `yes` | Enable overlay chart for 2 files |
| `plot_height_px` | `920` | Chart height in pixels (width auto-calculated as 16:9) |

### [LoudnessDensity] Section
| Setting | Default | Description |
|---------|---------|-------------|
| `y_max_sec` | `30` | Max Y-axis value (seconds) |
| `x_min_db` | `-40` | Left X-axis boundary (LUFS) |
| `x_max_db` | `0` | Right X-axis boundary (LUFS) |
| `bins` | `160` | Number of histogram bars |
| `HLineColor` | `#10AA10` | Bar color |
| `HOverColor` | `#30FF20` | Bar color when exceeding `y_max_sec` |
| `HLabelColor` | `#003000` | Axis label color |

### [LoudnessFlow] Section
| Setting | Default | Description |
|---------|---------|-------------|
| `Enabled` | `yes` | Enable Loudness Flow chart |
| `WindowMin` | `0.01` | Min window size (micro-dynamics), seconds |
| `WindowMax` | `16` | Max window size (macro-dynamics), seconds |
| `Steps` | `12` | Number of calculation points (logarithmic scale) |
| `Cut5` | `yes` | Trim 5% peaks and 10% silence (EBU method) |
| `YMaxDB` | `24` | Max Y-axis value (dB), auto-scales to 48 if exceeded |
| `VLineColor` | `#10AA10` | Flow line color |
| `VLabelColor` | `#002000` | Axis label color |

---

## 🚀 Usage

### Command Line
```bash
# Process single file
python lfm/lfm.py "01 - Rehab.mp3"

# Process folder
python lfm/lfm.py "D:\Python\Loudness Flow Measure"

# Process current directory (no args)
python lfm/lfm.py
```

### Dependencies (Python packages)
```bash
pip install pydub numpy scipy matplotlib
```

---

## 📈 Output Metrics Explained

| Metric | Description | Standard |
|--------|-------------|----------|
| **P10** | 10th percentile loudness | EBU 3342 |
| **Integrated** | Overall integrated loudness (double gating) | BS.1770-4 |
| **P95** | 95th percentile loudness | EBU 3342 |
| **LRA** | Loudness Range (P95 - P10) | EBU 3342 |
| **True Peak** | Inter-sample peak (2× oversampling) | — |
| **Digital Peak** | Max sample level (no oversampling) | — |
| **Flow Avg** | Average Loudness Flow across all windows | — |
| **Top-3 Dominants** | Most common loudness levels by duration | — |

---

## ⚠️ Known Limitations

1. **Channel Support:** Only mono (1ch) and stereo (2ch) audio processed
2. **Version Mismatch:** Code reports v0.7.1, docs mention v0.8.1
3. **Windows Only:** Hardcoded `.exe` paths for ffmpeg/ffprobe
4. **Hardcoded Paths:** Script expects `ffmpeg/` folder in same directory as `lfm.py`

---

## 📝 Development Conventions

### Code Style
- Python 3.8+ compatibility
- Type hints in function signatures
- Docstrings for classes and public functions
- Progress bars for long-running operations
- Verbose mode optional via config

### File Naming for Outputs
- Density: `ds <original_filename_without_ext>.png`
- Flow: `fl <original_filename_without_ext>.png`
- Overlay: `fl <name1>_vs_<name2>.png` (only 2 files)

### Backup Behavior
- Existing `loudness_flow_report.txt` renamed to `.bak` before new analysis
- Old `.bak` deleted if exists

---

## 🔧 Pydub Integration Notes

- ffmpeg/ffprobe paths explicitly set via environment PATH and pydub attributes
- Compatibility layer for different pydub versions:
  - `pydub.utils.get_encoder`
  - `pydub.utils.get_decoder`
  - `pydub.utils.get_ffprobe`
  - `AudioSegment.converter`
  - `AudioSegment.ffprobe`
- Warning suppression at import time

---

## 📐 Visualization Details

### Chart Dimensions
- Height: `plot_height_px` (default 920px)
- Width: Auto-calculated as 16:9 ratio
- DPI: 100
- Background: White

### Density Chart (`ds`)
- Histogram: Loudness distribution (bins from config)
- Vertical lines: P10 (orange, dashed), P95 (red, dashed), Integrated (blue, dash-dot), LRA (blue, solid)
- Legend: Upper left

### Flow Chart (`fl`)
- X-axis: Window sizes (logarithmic, 0.01s-16s)
- Y-axis: Dynamic range (dB, 0-24 or 0-48 auto-scaled)
- Line: Markers + smooth curve
- Horizontal lines: LRA, Flow Avg, |Integrated|
- Legend: Upper left

### Overlay Chart (`fl ..._vs_...`)
- Two flow curves on same axes
- Colors: Green (#10AA10) for file 1, Red (#FF4444) for file 2
- Horizontal lines for each: LRA, Average
- Legend: Upper left, fontsize 8

---

*Generated for Qwen Code context — April 2026*
