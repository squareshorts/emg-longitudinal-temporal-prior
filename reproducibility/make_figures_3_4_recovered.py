"""Recovered historical plotting script for manuscript Figures 3 and 4.

This file is preserved for provenance. It retains the original local Windows
paths and expects intermediate CSV files from the historical interactive EMG
pipeline. Those intermediate CSVs are not all recoverable in this archive.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def generate_figure_3():
    in_path = Path(r"C:\work\CEMHSEY\results\final_controls_actual_time_v1\loo_day_specific_residual_audit_actual_time.csv")
    df = pd.read_csv(in_path)
    df = df[df["baseline_role"] == "primary"]
    methods = [
        (8, "fixed_kf", "Fixed 8"),
        (8, "adaptive_kf", "Adaptive 8"),
        (16, "fixed_kf", "Fixed 16"),
        (16, "adaptive_kf", "Adaptive 16"),
    ]
    labels = []
    plot_data_pearson = []
    pos_corr = []
    pos_r2 = []
    for k, meth, label in methods:
        sub = df[(df["electrodes"] == k) & (df["method"] == meth)]
        labels.append(label)
        plot_data_pearson.append(sub["loo_pearson_r"].dropna().values)
        pos_corr.append(sub["loo_correlation_positive"].sum())
        pos_r2.append(sub["loo_residual_r2_positive"].sum())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.boxplot(plot_data_pearson, tick_labels=labels, showfliers=False)
    ax1.axhline(0, color="gray", linestyle="--")
    ax1.set_ylabel("LOO residual correlation")
    ax1.set_title("A. Association after repeatable-shape removal")

    x = np.arange(len(labels))
    width = 0.35
    rects1 = ax2.bar(x - width / 2, pos_corr, width, label="r > 0")
    rects2 = ax2.bar(x + width / 2, pos_r2, width, label="residual R² > 0")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_title("B. Association versus calibrated prediction")
    ax2.set_ylim(0, 120)
    for rects in [rects1, rects2]:
        for rect in rects:
            height = rect.get_height()
            ax2.annotate(
                f"{int(height)}/100",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
            )
    ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0)
    plt.tight_layout()
    out_dir = Path(r"C:\work\CEMHSEY\figure_repairs")
    out_dir.mkdir(exist_ok=True, parents=True)
    fig.savefig(out_dir / "fig3_residual_information_fixed.pdf", bbox_inches="tight")
    fig.savefig(out_dir / "fig3_residual_information_fixed.png", bbox_inches="tight", dpi=300)
    plt.close()


def generate_figure_4():
    inf_path = Path(r"C:\work\CEMHSEY\results\reconstruction_v1\paired_inference.csv")
    diff_path = Path(r"C:\work\CEMHSEY\results\reconstruction_v1\paired_participant_differences.csv")
    df_inf = pd.read_csv(inf_path)
    df_diff = pd.read_csv(diff_path)
    df_inf = df_inf[df_inf["metric"] == "r2"]
    df_diff = df_diff[df_diff["metric"] == "r2"]

    contrasts = [
        ("stage_alignment", "Session alignment"),
        ("stage_temporal_fixed_weights", "Temporal filtering"),
        ("stage_adaptive_variance_matched_q", "Adaptive variance"),
    ]
    validations = {
        "stage_alignment": {
            8: (0.081697, 0.011109, 0.230108),
            16: (0.068871, 0.016384, 0.199991),
        },
        "stage_temporal_fixed_weights": {
            8: (0.009632, 0.007770, 0.022737),
            16: (0.011658, 0.006221, 0.019429),
        },
        "stage_adaptive_variance_matched_q": {
            8: (0.000000, 0.000000, 0.008986),
            16: (0.000000, 0.000000, 0.006460),
        },
    }
    for c_id, _ in contrasts:
        for k in [8, 16]:
            row = df_inf[(df_inf["contrast"] == c_id) & (df_inf["k"].astype(str) == str(k))].iloc[0]
            val_med, val_low, val_high = validations[c_id][k]
            assert abs(row["median_paired_delta"] - val_med) < 1e-4
            assert abs(row["ci95_low"] - val_low) < 1e-4
            assert abs(row["ci95_high"] - val_high) < 1e-4

    np.random.seed(42)
    fig, ax = plt.subplots(figsize=(10, 6))
    y_ticks = []
    y_labels = []
    y_pos = 0
    for c_id, c_name in contrasts:
        y_ticks.append(y_pos)
        y_labels.append(c_name)
        for k, offset, marker, color in [(8, 0.2, "o", "C0"), (16, -0.2, "s", "C1")]:
            inf_row = df_inf[(df_inf["contrast"] == c_id) & (df_inf["k"].astype(str) == str(k))].iloc[0]
            med = inf_row["median_paired_delta"]
            ci_l = inf_row["ci95_low"]
            ci_h = inf_row["ci95_high"]
            diffs = df_diff[(df_diff["contrast"] == c_id) & (df_diff["k"].astype(str) == str(k))]
            pts = diffs["delta"].values
            subjects = diffs["subject"].values
            ax.plot([ci_l, ci_h], [y_pos + offset, y_pos + offset], color=color, linewidth=2, zorder=1)
            ax.scatter([med], [y_pos + offset], color=color, marker=marker, s=150, edgecolor="black", zorder=3, label=f"{k} electrodes" if y_pos == 0 else "")
            for pt, subj in zip(pts, subjects):
                x_val = pt
                if x_val > 0.4:
                    ax.scatter([0.38], [y_pos + offset], color=color, marker=marker, s=50, alpha=0.6, zorder=2)
                    ax.annotate(f"S{subj} = +{x_val:.2f}", (0.395, y_pos + offset), va="center", fontsize=9)
                else:
                    jitter = np.random.uniform(-0.05, 0.05)
                    ax.scatter([x_val], [y_pos + offset + jitter], color=color, marker=marker, s=40, alpha=0.5, zorder=2)
        y_pos -= 1

    ax.axvline(0, color="gray", linestyle="--", zorder=0)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel(r"Paired $\Delta R^2$")
    ax.set_xlim(-0.15, 0.48)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="lower right")
    plt.tight_layout()
    out_dir = Path(r"C:\work\CEMHSEY\figure_repairs")
    out_dir.mkdir(exist_ok=True, parents=True)
    fig.savefig(out_dir / "fig4_emg_component_ablation_fixed.pdf", bbox_inches="tight")
    fig.savefig(out_dir / "fig4_emg_component_ablation_fixed.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Figures successfully generated!")


if __name__ == "__main__":
    generate_figure_3()
    generate_figure_4()
