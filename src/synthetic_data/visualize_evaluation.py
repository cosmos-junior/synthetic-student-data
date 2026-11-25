"""Generate evaluation and distribution comparison charts for synthetic student data."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DATASETS = {
    "Real (Training)": Path("data/processed/student_training_data.csv"),
    "Gaussian Copula": Path("outputs/gaussian_copula_synthetic.csv"),
    "CTGAN": Path("outputs/ctgan_synthetic.csv"),
    "TVAE": Path("outputs/tvae_synthetic.csv"),
}


def _plot_metric_panel(ax, df: pd.DataFrame, metrics: list[tuple[str, str]], title: str, ylim=(0, 1.08)):
    melted = df.melt(id_vars="model", value_vars=[m[0] for m in metrics], var_name="metric", value_name="score")
    label_map = dict(metrics)
    melted["metric"] = melted["metric"].map(label_map)
    sns.barplot(data=melted, x="metric", y="score", hue="model", ax=ax)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Score")
    ax.set_ylim(*ylim)
    ax.tick_params(axis="x", rotation=15)
    ax.legend(title="", fontsize=8)


def generate_evaluation_charts() -> list[Path]:
    """Generate comparison charts from evaluation_summary.csv and model outputs."""

    project_root = Path(__file__).resolve().parents[2]
    outputs_dir = project_root / "outputs"
    charts_dir = outputs_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid")
    saved_paths: list[Path] = []

    # 1. Multi-panel evaluation metrics chart
    eval_df = pd.read_csv(outputs_dir / "evaluation_summary.csv")
    synth_eval_df = eval_df[eval_df["model"] != "Real Baseline (TRTR)"].copy()

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    _plot_metric_panel(
        axes[0],
        synth_eval_df,
        [
            ("quality_overall", "Overall Quality"),
            ("column_shapes", "Column Shapes"),
            ("column_pair_trends", "Pair Trends"),
        ],
        "Statistical Fidelity (Higher = Better)",
    )
    _plot_metric_panel(
        axes[1],
        synth_eval_df,
        [
            ("new_row_synthesis", "New Row Synth"),
            ("dcr_baseline_protection", "DCR Protection"),
            ("disclosure_protection", "Disclosure Prot."),
        ],
        "Privacy Protection (Higher = Better)",
    )
    _plot_metric_panel(
        axes[2],
        eval_df,
        [
            ("status_accuracy", "Status Acc."),
            ("status_macro_f1", "Status Macro-F1"),
            ("final_score_r2", "Final Score R²"),
        ],
        "Downstream ML Utility (TRTR vs TSTR)",
        ylim=(-0.35, 1.05),
    )
    axes[2].axhline(0, color="gray", linestyle="--", linewidth=0.8)

    plt.tight_layout()
    metrics_chart = charts_dir / "model_comparison_metrics.png"
    fig.savefig(metrics_chart, dpi=150)
    plt.close(fig)
    saved_paths.append(metrics_chart)

    # 2. Final score distribution comparison
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, rel_path in DATASETS.items():
        df = pd.read_csv(project_root / rel_path)
        sns.kdeplot(df["final_score"], label=label, ax=ax, linewidth=2)
    ax.set_title("Final Score Distribution: Real vs. Synthetic Models", fontsize=12, fontweight="bold")
    ax.set_xlabel("Final Score")
    ax.set_ylabel("Density")
    ax.legend()
    plt.tight_layout()
    score_chart = charts_dir / "final_score_distributions.png"
    fig.savefig(score_chart, dpi=150)
    plt.close(fig)
    saved_paths.append(score_chart)

    # 3. Categorical distributions (programme and grade)
    frames = []
    for label, rel_path in DATASETS.items():
        df = pd.read_csv(project_root / rel_path)
        frames.append(df.assign(dataset=label))
    combined = pd.concat(frames, ignore_index=True)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, col, order, title in [
        (axes[0], "programme", ["BIT", "BCS", "BSE", "BBIT"], "Programme Distribution (%)"),
        (axes[1], "grade", ["A", "B", "C", "D", "E"], "Grade Distribution (%)"),
    ]:
        pct_df = (
            combined.groupby("dataset")[col]
            .value_counts(normalize=True)
            .mul(100)
            .rename("percentage")
            .reset_index()
        )
        sns.barplot(data=pct_df, x=col, y="percentage", hue="dataset", order=order, ax=ax)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel(col.replace("_", " ").title())
        ax.set_ylabel("Percentage (%)")
        ax.legend(title="", fontsize=8)

    plt.tight_layout()
    cat_chart = charts_dir / "categorical_distributions.png"
    fig.savefig(cat_chart, dpi=150)
    plt.close(fig)
    saved_paths.append(cat_chart)

    for path in saved_paths:
        print(f"Saved chart: {path}")
    return saved_paths


if __name__ == "__main__":
    generate_evaluation_charts()
