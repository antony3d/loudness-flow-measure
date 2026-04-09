import configparser
import os
import re
import sys
import time
import warnings
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import lfilter, resample_poly

# Suppress pydub warning about ffmpeg/avconv not being found at import time
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pydub
    import pydub.utils
    from pydub import AudioSegment

# --- VERSION INFORMATION ---
NAME = "Loudness Flow Measure"
VERSION = "0.8.2"

# Paths for the working directory (script's directory)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(CURRENT_DIR, "ffmpeg")
FFMPEG_PATH = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(FFMPEG_DIR, "ffprobe.exe")

# FIXME: Найти легковесную версию ffprobe.exe заменить на неё, или скомпилировать свою с минимальным функционалом. 

# Check if required files exist
if not os.path.isfile(FFMPEG_PATH):
    raise FileNotFoundError(f"ffmpeg.exe not found at: {FFMPEG_PATH}")
if not os.path.isfile(FFPROBE_PATH):
    raise FileNotFoundError(f"ffprobe.exe not found at: {FFPROBE_PATH}")

# Add ffmpeg folder to PATH so subprocess and pydub can find dependencies
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")


# For compatibility with different pydub versions, assign required attributes
def get_ffmpeg_path():
    """Helper to return the ffmpeg path for pydub."""
    return FFMPEG_PATH


def get_ffprobe_path():
    """Helper to return the ffprobe path for pydub."""
    return FFPROBE_PATH


pydub.utils.get_encoder = get_ffmpeg_path
pydub.utils.get_decoder = get_ffmpeg_path
pydub.utils.get_ffprobe = get_ffprobe_path

# Also specify directly in AudioSegment
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

class ProgressBar:
    """Lightweight terminal progress bar.
    Parameters:
        desc (str): Label displayed before the bar.
        total (int): Expected number of iterations.
        bar_len (int): Visual width of the progress track.
        fill_char (str): Symbol used for the filled portion.
        show_time (bool): Toggle remaining time display in seconds.
    """
    def __init__(self, desc: str, total: int, bar_len: int = 25,
                 fill_char: str = "▒", show_time: bool = True):
        self.desc = desc
        self.total = total
        self.bar_len = bar_len
        self.fill_char = fill_char
        self.show_time = show_time
        self.current = 0
        self.start_time = time.perf_counter()

    def update(self, n: int = 1) -> None:
        """Increment counter and redraw the line."""
        self.current += n
        self._render()

    def _render(self) -> None:
        # Вычисляем процент и количество заполненных ячеек
        pct = (self.current / self.total * 100) if self.total > 0 else 100.0
        filled = int(self.bar_len * self.current / self.total) if self.total > 0 else self.bar_len
        bar = self.fill_char * filled + " " * (self.bar_len - filled)

        # Считаем оставшееся время в секундах на основе текущей средней скорости
        elapsed = time.perf_counter() - self.start_time
        if self.current > 0:
            remaining = (self.total - self.current) * (elapsed / self.current)
        else:
            remaining = 0.0

        # Формируем итоговую строку, время добавляется только по флагу
        time_str = f" {remaining:.1f} sec" if self.show_time else ""
        line = f"{self.desc} {pct:3.0f}% |{bar}| {self.current}/{self.total}{time_str}"

        # Перезаписываем строку в терминале, ljust убирает хвосты от предыдущих рендеров
        sys.stdout.write(f"\r{line.ljust(20)}")
        sys.stdout.flush()

    def close(self) -> None:
        """Finalize bar output and move cursor to next line."""
        self._render()
        sys.stdout.write("\n")
        sys.stdout.flush()


def clean_name(filename):
    """Cleans the filename by removing common prefixes and suffixes."""
    name_only = os.path.splitext(filename)[0]
    match = re.search(r'\d{1,3}[\s\.\-\_]+\s*(.+)', name_only)
    if match:
        name_cleaned = match.group(1)
    else:
        name_cleaned = name_only
    # Remove common suffixes: orig, original, remaster, remix, extended, etc.
    name_cleaned = re.sub(
        r'\s*(orig|original|remaster|remastered|remix|extended|radio edit|album version|original mix|remix.*|version.*)\s*$',
        '',
        name_cleaned,
        flags=re.IGNORECASE
    )
    return name_cleaned.strip(' .-_').lower()


def k_filter(samples, sr):
    """Applies K-filtering (Pre-filter + RLB) to a mono signal."""
    # Stage 1: Pre-filter (High Shelf)
    f0 = 1500
    db = 4.0
    q = 0.707
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * q)
    a_val = 10**(db / 40)

    b0 = a_val * ((a_val + 1) + (a_val - 1) * np.cos(w0) + 2 * np.sqrt(a_val) * alpha)
    b1 = -2 * a_val * ((a_val - 1) + (a_val + 1) * np.cos(w0))
    b2 = a_val * ((a_val + 1) + (a_val - 1) * np.cos(w0) - 2 * np.sqrt(a_val) * alpha)
    a0 = (a_val + 1) - (a_val - 1) * np.cos(w0) + 2 * np.sqrt(a_val) * alpha
    a1 = 2 * ((a_val - 1) - (a_val + 1) * np.cos(w0))
    a2 = (a_val + 1) - (a_val - 1) * np.cos(w0) - 2 * np.sqrt(a_val) * alpha
    samples = lfilter([b0 / a0, b1 / a0, b2 / a0], [1, a1 / a0, a2 / a0], samples)

    # Stage 2: RLB filter (High Pass)
    f0_hp = 38.1
    q_hp = 0.5
    w0_hp = 2 * np.pi * f0_hp / sr
    alpha_hp = np.sin(w0_hp) / (2 * q_hp)
    b0_hp = (1 + np.cos(w0_hp)) / 2
    b1_hp = -(1 + np.cos(w0_hp))
    b2_hp = (1 + np.cos(w0_hp)) / 2
    a0_hp = 1 + alpha_hp
    a1_hp = -2 * np.cos(w0_hp)
    a2_hp = 1 - alpha_hp
    samples = lfilter(
        [b0_hp / a0_hp, b1_hp / a0_hp, b2_hp / a0_hp],
        [1, a1_hp / a0_hp, a2_hp / a0_hp],
        samples
    )
    return samples


def get_momentary_powers(channels, sr, window_sec, step_sec, show_progress=False):
    """Calculates total power (Mean Square) of channels with overlap."""
    win = int(window_sec * sr)
    step = int(step_sec * sr)
    n_samples = len(channels[0])
    powers = []

    if show_progress:
        pbar2 = ProgressBar("  [Power Calc]:\t\t", int((n_samples - win) / step) + 1, bar_len=30, fill_char="#", show_time=False)

    for start in range(0, n_samples - win, step):
        end = start + win
        total_ms = 0
        for ch_data in channels:
            segment = ch_data[start:end]
            ms = np.mean(np.square(segment))
            total_ms = total_ms + ms
        powers.append(total_ms)
        if show_progress: pbar2.update()
    if show_progress: pbar2.close()
    return np.array(powers)


def detect_peaks(channels, sr, oversample_factor=2):
    """Estimates True Peak (with oversampling) and Digital Peak (raw samples)."""
    pbar3 = ProgressBar("  [Peak Calc]:\t\t", len(channels), bar_len=30, fill_char="#", show_time=False)
    true_peak = 0.0
    digital_peak = 0.0
    for ch_data in channels:
        # Digital Peak
        pbar3.update()
        ch_digital = np.max(np.abs(ch_data))
        if ch_digital > digital_peak:
            digital_peak = ch_digital
        # True Peak
        upsampled = resample_poly(ch_data, oversample_factor, 1)
        ch_true = np.max(np.abs(upsampled))
        if ch_true > true_peak:
            true_peak = ch_true
    pbar3.close()
    return 20 * np.log10(true_peak + 1e-12), 20 * np.log10(digital_peak + 1e-12)


def calculate_integrated_lufs(powers):
    """Integrated Loudness algorithm per BS.1770-4 (double gating)."""
    if len(powers) == 0:
        return -70.0

    m_loudness = -0.691 + 10 * np.log10(powers + 1e-12)

    abs_indices = np.where(m_loudness > -70.0)[0]
    if len(abs_indices) == 0:
        return -70.0

    abs_gated_powers = powers[abs_indices]
    mean_power_abs = np.mean(abs_gated_powers)
    loudness_abs = -0.691 + 10 * np.log10(mean_power_abs + 1e-12)
    gamma = loudness_abs - 10.0

    final_indices = np.where((m_loudness > gamma) & (m_loudness > -70.0))[0]
    if len(final_indices) == 0:
        return loudness_abs

    final_mean_power = np.mean(powers[final_indices])
    integrated = -0.691 + 10 * np.log10(final_mean_power + 1e-12)
    return integrated


def process_audio(input_path, force_verbose=False):
    """Main processing function for audio files or directories."""
    config = configparser.ConfigParser()
    config_path = os.path.join(CURRENT_DIR, "lfm.ini")
    config.read(config_path, encoding='utf-8')

    main_cfg = config['Main']
    dens_cfg = config['LoudnessDensity']
    flow_cfg = config['LoudnessFlow']
    
    # CLI flag overrides config file
    verbose = force_verbose or main_cfg.getboolean('verbose')
    delta_comparison = main_cfg.getboolean('delta_comparison')
    overlay_flow = main_cfg.getboolean('overlay_flow')

    if os.path.isfile(input_path):
        root_dir = os.path.dirname(os.path.abspath(input_path))
        files = [os.path.basename(input_path)]
    else:
        root_dir = os.path.abspath(input_path)
        files = [f for f in os.listdir(root_dir) if f.lower().endswith(('.wav', '.mp3', '.flac'))]

    results_db = {}
    all_flow_data = []
    report_path = os.path.join(root_dir, "loudness_flow_report.txt")
    start_dt = None


    # Backup existing report file
    if os.path.isfile(report_path):
        backup_path = report_path + ".bak"
        if os.path.isfile(backup_path):
            os.remove(backup_path)
        os.rename(report_path, backup_path)
        if verbose:
            print(f"  [Backup] Previous report backed up to: loudness_flow_report.txt.bak\n")

    with open(report_path, "w", encoding="utf-8") as report:
        report.write(f"{NAME} v{VERSION}\n" + "=" * 45 + "\n")

        start_dt = datetime.now()
        if verbose:
            print(f"  [Time] start in {start_dt.strftime('%H:%M:%S.%f')[:-3]}")

        total_files = len(files)
        for file_idx, filename in enumerate(files, 1):
            t_file_start = time.perf_counter()
            print(f"> [{file_idx}/{total_files}] Processing: {filename}")
            report.write(f"\n> File: {filename}\n")

            try:
                # 1. Loading
                t_load = time.perf_counter()
                audio = AudioSegment.from_file(os.path.join(root_dir, filename))
                sr = audio.frame_rate
                denom = 2**(audio.sample_width * 8 - 1)

                samples_raw = np.array(audio.get_array_of_samples()).astype(np.float32)
                samples_norm = samples_raw / denom

                channels = []
                if audio.channels == 2:
                    reshaped = samples_norm.reshape((-1, 2))
                    channels.append(reshaped[:, 0])
                    channels.append(reshaped[:, 1])
                else:
                    channels.append(samples_norm)
                if verbose:
                    print(f"  [Time] Audio loading & Norm done in {time.perf_counter() - t_load:.3f} sec")

                # 2. Filtering
                t_filt = time.perf_counter()
                filtered_channels = []
                for ch_data in channels:
                    if main_cfg.get('LoudnessMode') == 'LUFS':
                        ch_data = k_filter(ch_data, sr)
                    filtered_channels.append(ch_data)
                if verbose:
                    print(f"  [Time] K-Filtering done in {time.perf_counter() - t_filt:.3f} sec")

                # 3. Peak Detection
                t_tp = time.perf_counter()
                true_peak, digital_peak = detect_peaks(channels, sr)
                if verbose:
                    print(f"  [Time] Peak detection done in {time.perf_counter() - t_tp:.3f} sec")

                # 4. Integrated LUFS
                t_int = time.perf_counter()
                m_powers = get_momentary_powers(filtered_channels, sr, 0.4, 0.1, True)
                int_l = calculate_integrated_lufs(m_powers)
                if verbose:
                    print(f"  [Time] Integrated LUFS done in {time.perf_counter() - t_int:.3f} sec")

                # 5. LRA & Percentiles
                t_lra_start = time.perf_counter()

                pb = ProgressBar("  [LRA Calc]:\t\t", total=100, bar_len=30, fill_char="#", show_time=False)
                pb.update(5)
                lra_powers = get_momentary_powers(filtered_channels, sr, 3.0, 0.1)

                pb.update(65)

                lra_loudness = -0.691 + 10 * np.log10(lra_powers + 1e-12)

                lra_abs_idx = np.where(lra_loudness > -70.0)[0]
                time.sleep(0.2)
                pb.update(15)

                if len(lra_abs_idx) > 0:
                    z_lra_abs = np.mean(lra_powers[lra_abs_idx])
                    l_lra_abs = -0.691 + 10 * np.log10(z_lra_abs + 1e-12)
                    gamma_lra = l_lra_abs - 20.0

                    mask = (lra_loudness > gamma_lra) & (lra_loudness > -70.0)
                    final_lra_vals = lra_loudness[mask]
                    p10 = np.percentile(final_lra_vals, 10) if len(final_lra_vals) > 0 else -70
                    p95 = np.percentile(final_lra_vals, 95) if len(final_lra_vals) > 0 else -70
                    time.sleep(0.2)
                    pb.update(15)
                    lra = p95 - p10
                else:
                    p10 = -70
                    p95 = -70
                    lra = 0
                time.sleep(0.2)
                pb.close()
                if verbose:
                    print(f"  [Time] LRA calculation done in {time.perf_counter() - t_lra_start:.3f} sec")

                # 6. Top-3 Dominants
                h_counts, h_bins = np.histogram(
                    lra_loudness[lra_loudness > -70],
                    bins=dens_cfg.getint('bins'),
                    range=(dens_cfg.getfloat('x_min_db'), dens_cfg.getfloat('x_max_db'))
                )
                durations = h_counts * 0.1
                top_idx = np.argsort(durations)[-3:][::-1]
                top_3_list = []
                for i in top_idx:
                    center = (h_bins[i] + h_bins[i + 1]) / 2
                    top_3_list.append(f"   Level   {center:.2f} LUFS: {durations[i]:.2f} sec")
                top_3_str = "\n".join(top_3_list)

                # 7. Loudness Flow
                flow_pts = []
                if flow_cfg.getboolean('Enabled'):
                    t_flow = time.perf_counter()
                    win_min = flow_cfg.getfloat('WindowMin')
                    win_max = flow_cfg.getfloat('WindowMax')
                    steps = flow_cfg.getint('Steps')
                    windows = np.geomspace(win_min, win_max, steps)

# TODO: detach ProgressBat to deparate module

                    pbar1 = ProgressBar("  [Loudness Flow]:\t", len(windows), bar_len=30, fill_char="#", show_time=True)

                    for w in windows:
                        pbar1.update()
                        f_v = get_momentary_powers(filtered_channels, sr, w, w / 4)
                        f_db = -0.691 + 10 * np.log10(f_v + 1e-12)
                        f_db = f_db[f_db > -70]
                        if len(f_db) > 0:
                            if flow_cfg.getboolean('Cut5'):
                                spread = np.percentile(f_db, 95) - np.percentile(f_db, 10)
                            else:
                                spread = np.max(f_db) - np.min(f_db)
                            flow_pts.append((w, spread))
                    pbar1.close()
                    if verbose:
                        print(f"  [Time] Loudness Flow done in {time.perf_counter() - t_flow:.3f} sec")

                flow_y_vals = [p[1] for p in flow_pts]
                flow_avg = np.mean(flow_y_vals) if flow_y_vals else 0

                # Save flow data for overlay comparison
                all_flow_data.append((filename, flow_pts, flow_avg, lra, int_l))

                # 8. Output Results
                output = [
                    f"   P10:        {p10:.2f} LUFS",
                    f"   Integrated: {int_l:.2f} LUFS",
                    f"   P95:        {p95:.2f} LUFS",
                    f"   LRA:         {lra:.2f} LU",
                    f"   True Peak:  {true_peak:.2f} dBTP",
                    f"   Dig. Peak:  {digital_peak:.2f} dBTP",
                    f"   Flow Avg:    {flow_avg:.2f} dB",
                     "  TOP-3 Dominants",
                    top_3_str,
                    ""
                ]

                text_block = "\n".join(output)
                print(text_block)
                report.write(text_block)

                # 9. Delta Comparison
                if delta_comparison:
                    clean_curr = clean_name(filename)
                    for prev_name, prev_val in results_db.items():
                        if clean_name(prev_name) in clean_curr or clean_curr in clean_name(prev_name):
                            d_int = int_l - prev_val['int']
                            d_lra = lra - prev_val['lra']
                            d_flow = flow_avg - prev_val['flow']
                            d_dp = digital_peak - prev_val['dp']
                            delta_msg = (
                                f"  [DELTA COMPARISON] with {prev_name}:\n"
                                f"   dInt:   {d_int:+.2f} LU\n"
                                f"   dLRA:   {d_lra:+.2f} LU\n"
                                f"   dFlow:  {d_flow:+.2f} dB\n"
                                f"   dDPeak: {d_dp:+.2f} dB\n"
                            )
                            print(delta_msg)
                            report.write(delta_msg)

                results_db[filename] = {'int': int_l, 'lra': lra, 'flow': flow_avg, 'tp': true_peak, 'dp': digital_peak}

                # 10. Line Style Settings
                lines = {
                    "p10": {"color": "orange", "ls": "--", "lw": 0.8, "label": f'P10 ({p10:.2f}) LUFS'},
                    "p95": {"color": "red", "ls": "--", "lw": 0.8, "label": f'P95 ({p95:.2f}) LUFS'},
                    "int_l": {"color": "blue", "ls": "-.", "lw": 0.8, "label": f'Integrated ({int_l:.2f}) LUFS'},
                    "lra": {"color": "#2060dd", "ls": "-", "lw": 1.5, "label": f'LRA ({lra:.2f}) LU', "alpha": 0.75},
                    "flow_avg": {"color": "#cdcd00", "ls": "-", "lw": 1.5, "label": f'Flow avg ({flow_avg:.2f}) dB', "alpha": 0.75}
                }

                # 11. Plotting
                dpi_v = 100
                h_px = main_cfg.getint('plot_height_px')
                w_px = int(h_px * (16 / 9))
                f_w = w_px / dpi_v
                f_h = h_px / dpi_v

                # Density Plot
                plt.figure(figsize=(f_w, f_h), facecolor='white')
                y_max_s = dens_cfg.getfloat('y_max_sec')
                colors = [
                    dens_cfg.get('HOverColor') if d > y_max_s else dens_cfg.get('HLineColor')
                    for d in durations
                ]
                plt.bar(
                    (h_bins[:-1] + h_bins[1:]) / 2, durations,
                    width=np.diff(h_bins), color=colors, edgecolor='white'
                )

                # Vertical Lines
                plt.axvline(p10, **lines["p10"])
                plt.axvline(p95, **lines["p95"])
                plt.axvline(int_l, **lines["int_l"])
                plt.axvline((lra * -1), **{**lines["lra"], "ls": " "})

                plt.xlim(dens_cfg.getfloat('x_min_db'), dens_cfg.getfloat('x_max_db'))
                plt.ylim(0, y_max_s * 1.05)
                plt.legend(loc='upper left')
                plt.title(f"Density: {filename}")
                plt.savefig(
                    os.path.join(root_dir, f"ds {os.path.splitext(filename)[0]}.png"),
                    dpi=dpi_v
                )
                plt.close()

                # Loudness Flow Plot
                if flow_pts:
                    plt.figure(figsize=(f_w, f_h), facecolor='white')
                    xv = [p[0] for p in flow_pts]
                    yv = [p[1] for p in flow_pts]

                    # Adaptive Y limit
                    y_limit = flow_cfg.getfloat('YMaxDB', 24.0)
                    check_points = yv[:2] if len(yv) >= 2 else yv
                    max_start = max(check_points) if check_points else 0

                    if max_start > y_limit:
                        y_limit = 48.0
                        msg = f"  [Notice] Big DR, set Y scale to 48 dB (VF Peak: {max_start:.2f} dB)"
                        if verbose:
                            print(msg)
                            report.write(msg + "\n")

                    plt.semilogx(xv, yv, color=flow_cfg.get('VLineColor'), marker='o', lw=2)

                    # Horizontal Lines
                    plt.axhline(lra, **lines["lra"])
                    plt.axhline(flow_avg, **lines["flow_avg"])
                    plt.axhline(abs(int_l), **lines["int_l"])

                    # X-axis labels
                    labels = [f"{x:.2f}" if x < 1 else f"{x:.1f}" for x in xv]
                    plt.xticks(xv, labels, rotation=45)

                    # Axis labels
                    plt.xlabel("Window size, sec", fontsize=10, color=lines["lra"]["color"])
                    plt.ylabel("Dynamic Range, dB", fontsize=10, color=lines["lra"]["color"])

                    plt.ylim(0, y_limit)
                    plt.grid(True, which="both", alpha=0.0)
                    plt.legend(loc='upper left')
                    plt.title(f"Loudness Flow: {filename}")
                    plt.savefig(
                        os.path.join(root_dir, f"fl {os.path.splitext(filename)[0]}.png"),
                        dpi=dpi_v
                    )
                    plt.close()

                if verbose:
                    print(f"  [Time] Total for {filename}: {time.perf_counter() - t_file_start:.3f} sec")
                report.write("-" * 20 + "\n")

            except FileNotFoundError as e:
                print(f"File not found: {e}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    # --- Overlay Flow Plot (only for exactly 2 files) ---
    if overlay_flow and len(all_flow_data) == 2:
        fname1, pts1, avg1, lra1, int1 = all_flow_data[0]
        fname2, pts2, avg2, lra2, int2 = all_flow_data[1]
        name1_short = os.path.splitext(fname1)[0]
        name2_short = os.path.splitext(fname2)[0]
        print(f"> Building Overlay Flow: 'fl {name1_short}_vs_{name2_short}.png'")

        # Plot dimensions
        dpi_v = 100
        h_px = main_cfg.getint('plot_height_px')
        w_px = int(h_px * (16 / 9))
        f_w = w_px / dpi_v
        f_h = h_px / dpi_v

        colors = ["#10AA10", "#FF4444"]

        # Determine Y limit
        all_y = [p[1] for p in pts1] + [p[1] for p in pts2]
        y_limit = flow_cfg.getfloat('YMaxDB', 24.0)
        check_pts = all_y[:4] if len(all_y) >= 4 else all_y
        if check_pts and max(check_pts) > y_limit:
            y_limit = 48.0

        plt.figure(figsize=(f_w, f_h), facecolor='white')

        for i, (fname, pts, avg, lra, int_l) in enumerate(all_flow_data):
            xv = [p[0] for p in pts]
            yv = [p[1] for p in pts]
            c = colors[i]

            # Flow curve
            plt.semilogx(xv, yv, color=c, marker='o', lw=2, label=fname)

            # Horizontal lines
            plt.axhline(lra, color=c, ls="--", lw=1.0, alpha=0.5, label=f'LRA {fname[:8]} ({lra:.1f})')
            plt.axhline(avg, color=c, ls=":", lw=1.0, alpha=0.5, label=f'Avg {fname[:8]} ({avg:.1f})')

        labels_x = [f"{entry[0]:.2f}" if entry[0] < 1 else f"{entry[0]:.1f}" for entry in all_flow_data[0][1]]
        plt.xticks([entry[0] for entry in all_flow_data[0][1]], labels_x, rotation=45)
        plt.xlabel("Window size, sec", fontsize=10)
        plt.ylabel("Dynamic Range, dB", fontsize=10)
        plt.ylim(0, y_limit)
        plt.grid(True, which="both", alpha=0.0)
        plt.legend(loc='upper left', fontsize=8)
        plt.title(f"Loudness Flow Overlay: {name1_short} vs {name2_short}")
        plt.savefig(
            os.path.join(root_dir, f"fl {name1_short}_vs_{name2_short}.png"),
            dpi=dpi_v
        )
        plt.close()
        print(f"  [Overlay] Saved... ")

#    if verbose and start_dt:
    end_dt = datetime.now()
    duration = end_dt - start_dt
    if verbose: print(f"  [Time] end in {end_dt.strftime('%H:%M:%S.%f')[:-3]}")
    total_seconds = int(duration.total_seconds())
    milliseconds = duration.microseconds // 1000
    print(f"  [Time] Overall completion in {total_seconds}.{milliseconds:03d} sec")


if __name__ == "__main__":

#   TODO: Сделать нормальный парсер командной строки и хелп по параметрам     

    print(f"{NAME} v{VERSION}")

    # Parse command-line arguments
    target_path = None
    force_verbose = False
    
    for arg in sys.argv[1:]:
        if arg in ('-v', '--verbose'):
            force_verbose = True
        elif not arg.startswith('-'):
            target_path = arg
    
    if target_path:
        process_audio(target_path, force_verbose)
    else:
        print("\nUsage: lfm.py <path_to_audio_file_or_folder> [-v|--verbose]\n")
        process_audio(CURRENT_DIR, force_verbose)
