from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

import model


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
VALIDATION_DIR = OUTPUT_DIR / "validation"
REPORT_PATH = ROOT / "docs" / "egypt_synthetic_population_validation.md"

DATASET_ORDER = ["lfs", "findex", "elmps_person", "sme"]
DATASET_LABELS = {
    "lfs": "LFS 2024",
    "findex": "Global Findex Egypt",
    "elmps_person": "ELMPS 2023 persons",
    "sme": "ELMPS 2023 SMEs",
}
DATASET_COLORS = {
    "lfs": "#38598b",
    "findex": "#2a9d8f",
    "elmps_person": "#e9c46a",
    "sme": "#d62828",
}
FOCUS_WASSERSTEIN_ATTRIBUTES = {
    "lfs": ["sex", "age_band", "in_workforce", "lfs_establishment_size_band"],
    "findex": ["findex_account_fin", "findex_saved", "findex_fin11a", "findex_fin11b"],
    "elmps_person": [
        "elmps_job_formality",
        "elmps_firm_size_band",
        "elmps_has_any_savings",
        "elmps_num_enterprises_managed",
    ],
    "sme": [
        "sme_has_business_license",
        "sme_has_commercial_registration",
        "sme_hires_nonhousehold_workers",
        "sme_current_capital_band",
    ],
}
PERSON_COMBINATION_SPECS = [
    {"dataset": "lfs", "columns": ["sex", "age_band"], "label": "Gender x age band"},
    {
        "dataset": "lfs",
        "columns": ["in_workforce", "lfs_establishment_size_band"],
        "label": "Workforce x LFS firm size",
    },
    {
        "dataset": "elmps_person",
        "columns": ["sex", "elmps_job_formality"],
        "label": "Gender x job formality",
    },
    {
        "dataset": "elmps_person",
        "columns": ["in_workforce", "elmps_firm_size_band"],
        "label": "Workforce x ELMPS firm size",
    },
    {
        "dataset": "findex",
        "columns": ["urban_rural", "sex", "findex_account_fin"],
        "label": "Urbanicity x gender x account",
    },
    {
        "dataset": "findex",
        "columns": ["urban_rural", "sex", "findex_saved"],
        "label": "Urbanicity x gender x savings",
    },
    {
        "dataset": "findex",
        "columns": ["urban_rural", "sex", "findex_fin11a"],
        "label": "Urbanicity x gender x barrier 11a",
    },
]
SME_COMBINATION_SPECS = [
    {
        "dataset": "sme",
        "columns": ["sex", "sme_has_business_license"],
        "label": "Manager gender x business license",
    },
    {
        "dataset": "sme",
        "columns": ["urban_rural", "sme_has_business_license"],
        "label": "Manager urbanicity x business license",
    },
    {
        "dataset": "sme",
        "columns": ["sme_hires_nonhousehold_workers", "sme_current_capital_band"],
        "label": "External workforce x capital",
    },
    {
        "dataset": "sme",
        "columns": ["sme_has_business_license", "sme_has_commercial_registration"],
        "label": "License x registration",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the Egypt synthetic population against the source datasets."
    )
    parser.add_argument(
        "--sample-sizes",
        nargs="+",
        type=int,
        default=[1000, 10000],
        help="Synthetic population sizes to validate.",
    )
    return parser.parse_args()


def dataset_attributes(frame: pd.DataFrame, prefix: str) -> List[str]:
    return [column for column in frame.columns if column in model.CORE_COLUMNS or column.startswith(prefix)]


def load_original_frames() -> Dict[str, pd.DataFrame]:
    lfs_frame, _ = model.preprocess_lfs()
    findex_frame, _, _, _ = model.preprocess_findex()
    elmps_person_frame, _ = model.preprocess_elmps()
    sme_frame, _ = model.preprocess_smes()
    return {
        "lfs": lfs_frame,
        "findex": findex_frame,
        "elmps_person": elmps_person_frame,
        "sme": sme_frame,
    }


def load_synthetic_outputs(size: int) -> Dict[str, pd.DataFrame]:
    return {
        "persons": pd.read_csv(OUTPUT_DIR / f"egypt_synthetic_persons_{size}.csv"),
        "smes": pd.read_csv(OUTPUT_DIR / f"egypt_synthetic_smes_{size}.csv"),
    }


def build_validation_frames(synthetic_outputs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    persons = synthetic_outputs["persons"]
    smes = synthetic_outputs["smes"]
    sme_validation = smes.rename(
        columns={
            "manager_sex": "sex",
            "manager_age_band": "age_band",
            "manager_education_level": "education_level",
            "manager_urban_rural": "urban_rural",
            "manager_in_workforce": "in_workforce",
        }
    )
    sme_validation = sme_validation[
        ["sex", "age_band", "education_level", "urban_rural", "in_workforce"]
        + [column for column in sme_validation.columns if column.startswith("sme_")]
    ].copy()

    return {
        "lfs": persons,
        "findex": persons,
        "elmps_person": persons,
        "sme": sme_validation,
    }


def share_of_value(series: pd.Series, value: int) -> float:
    if len(series) == 0:
        return float("nan")
    return float((series == value).mean() * 100.0)


def compute_population_profiles(
    synthetic_outputs_by_size: Dict[int, Dict[str, pd.DataFrame]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    person_rows: List[Dict[str, object]] = []
    sme_rows: List[Dict[str, object]] = []

    for size, outputs in synthetic_outputs_by_size.items():
        persons = outputs["persons"]
        smes = outputs["smes"]

        person_rows.extend(
            [
                {"size": size, "indicator": "Synthetic persons", "value": float(len(persons))},
                {"size": size, "indicator": "Women (%)", "value": share_of_value(persons["sex"], 1)},
                {"size": size, "indicator": "Urban (%)", "value": share_of_value(persons["urban_rural"], 0)},
                {"size": size, "indicator": "In workforce (%)", "value": share_of_value(persons["in_workforce"], 1)},
                {
                    "size": size,
                    "indicator": "Formal financial account (%)",
                    "value": share_of_value(persons["findex_account_fin"], 1),
                },
                {"size": size, "indicator": "Any account (%)", "value": share_of_value(persons["findex_account"], 1)},
                {"size": size, "indicator": "Saved in last 12 months (%)", "value": share_of_value(persons["findex_saved"], 1)},
                {"size": size, "indicator": "ELMPS bank account (%)", "value": share_of_value(persons["elmps_has_bank_account"], 1)},
                {"size": size, "indicator": "ELMPS any savings (%)", "value": share_of_value(persons["elmps_has_any_savings"], 1)},
                {"size": size, "indicator": "Formal job indicator (%)", "value": share_of_value(persons["elmps_job_formality"], 1)},
                {"size": size, "indicator": "Manages at least one SME (%)", "value": share_of_value(persons["elmps_manages_sme"], 1)},
            ]
        )

        sme_rows.extend(
            [
                {"size": size, "indicator": "Synthetic SMEs", "value": float(len(smes))},
                {"size": size, "indicator": "SMEs per 100 persons", "value": float((len(smes) / len(persons)) * 100.0)},
                {"size": size, "indicator": "Female-managed SMEs (%)", "value": share_of_value(smes["manager_sex"], 1)},
                {"size": size, "indicator": "Urban-managed SMEs (%)", "value": share_of_value(smes["manager_urban_rural"], 0)},
                {"size": size, "indicator": "Has business license (%)", "value": share_of_value(smes["sme_has_business_license"], 1)},
                {
                    "size": size,
                    "indicator": "Has commercial registration (%)",
                    "value": share_of_value(smes["sme_has_commercial_registration"], 1),
                },
                {"size": size, "indicator": "Keeps accounting books (%)", "value": share_of_value(smes["sme_keeps_accounting_books"], 1)},
                {
                    "size": size,
                    "indicator": "Has online page/storefront (%)",
                    "value": share_of_value(smes["sme_has_online_page_or_storefront"], 1),
                },
                {"size": size, "indicator": "Uses mobile sales app (%)", "value": share_of_value(smes["sme_has_mobile_sales_app"], 1)},
                {
                    "size": size,
                    "indicator": "Hires non-household workers (%)",
                    "value": share_of_value(smes["sme_hires_nonhousehold_workers"], 1),
                },
                {
                    "size": size,
                    "indicator": "Any workers with social insurance (%)",
                    "value": share_of_value(smes["sme_any_workers_with_social_insurance"], 1),
                },
            ]
        )

    person_profile = pd.DataFrame.from_records(person_rows).pivot(index="indicator", columns="size", values="value")
    sme_profile = pd.DataFrame.from_records(sme_rows).pivot(index="indicator", columns="size", values="value")
    return person_profile, sme_profile


def attribute_frequency(series: pd.Series) -> pd.Series:
    return series.value_counts(normalize=True, dropna=False).sort_index()


def discrete_wasserstein(original: pd.Series, synthetic: pd.Series) -> float:
    states = sorted(set(original.index.tolist()) | set(synthetic.index.tolist()))
    original_weights = np.array([float(original.get(state, 0.0)) for state in states])
    synthetic_weights = np.array([float(synthetic.get(state, 0.0)) for state in states])
    return float(
        wasserstein_distance(states, states, u_weights=original_weights, v_weights=synthetic_weights)
    )


def joint_frequency(df: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby(list(columns), dropna=False).size().div(len(df)).sort_index()


def aligned_frequency_arrays(
    original_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    columns: Sequence[str],
) -> tuple[np.ndarray, np.ndarray]:
    original_freq = joint_frequency(original_df, columns)
    synthetic_freq = joint_frequency(synthetic_df, columns)
    aligned_index = original_freq.index.union(synthetic_freq.index)
    original_aligned = original_freq.reindex(aligned_index, fill_value=0.0)
    synthetic_aligned = synthetic_freq.reindex(aligned_index, fill_value=0.0)
    return original_aligned.to_numpy(dtype=float), synthetic_aligned.to_numpy(dtype=float)


def fit_regression(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    if len(x) < 2 or np.allclose(x, x[0]):
        return {"slope": float("nan"), "intercept": float("nan"), "r2": float("nan")}

    slope, intercept = np.polyfit(x, y, 1)
    predictions = intercept + slope * x
    ss_res = float(np.sum((y - predictions) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float("nan") if ss_tot == 0 else 1.0 - (ss_res / ss_tot)
    return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2)}


def compute_wasserstein_metrics(
    original_frames: Dict[str, pd.DataFrame],
    synthetic_frames_by_size: Dict[int, Dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    records: List[Dict[str, object]] = []

    attribute_map = {
        "lfs": dataset_attributes(original_frames["lfs"], "lfs_"),
        "findex": dataset_attributes(original_frames["findex"], "findex_"),
        "elmps_person": dataset_attributes(original_frames["elmps_person"], "elmps_"),
        "sme": dataset_attributes(original_frames["sme"], "sme_"),
    }

    for size, synthetic_frames in synthetic_frames_by_size.items():
        for dataset in DATASET_ORDER:
            original = original_frames[dataset]
            synthetic = synthetic_frames[dataset]
            for attribute in attribute_map[dataset]:
                if attribute not in synthetic.columns:
                    continue
                distance = discrete_wasserstein(
                    attribute_frequency(original[attribute]),
                    attribute_frequency(synthetic[attribute]),
                )
                records.append(
                    {
                        "size": size,
                        "dataset": dataset,
                        "attribute": attribute,
                        "wasserstein": distance,
                    }
                )

    return pd.DataFrame.from_records(records)


def compute_regression_metrics(
    original_frames: Dict[str, pd.DataFrame],
    synthetic_frames_by_size: Dict[int, Dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    records: List[Dict[str, object]] = []

    for size, synthetic_frames in synthetic_frames_by_size.items():
        for spec in PERSON_COMBINATION_SPECS + SME_COMBINATION_SPECS:
            dataset = spec["dataset"]
            columns = spec["columns"]
            x, y = aligned_frequency_arrays(
                original_frames[dataset],
                synthetic_frames[dataset],
                columns,
            )
            fit = fit_regression(x, y)
            records.append(
                {
                    "size": size,
                    "dataset": dataset,
                    "label": spec["label"],
                    "columns": " x ".join(columns),
                    "slope": fit["slope"],
                    "intercept": fit["intercept"],
                    "r2": fit["r2"],
                    "num_cells": len(x),
                }
            )

    return pd.DataFrame.from_records(records)


def compute_marginal_fit_points(
    original_frames: Dict[str, pd.DataFrame],
    synthetic_frames_by_size: Dict[int, Dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    records: List[Dict[str, object]] = []
    attribute_map = {
        "lfs": dataset_attributes(original_frames["lfs"], "lfs_"),
        "findex": dataset_attributes(original_frames["findex"], "findex_"),
        "elmps_person": dataset_attributes(original_frames["elmps_person"], "elmps_"),
        "sme": dataset_attributes(original_frames["sme"], "sme_"),
    }

    for size, synthetic_frames in synthetic_frames_by_size.items():
        for dataset in DATASET_ORDER:
            original = original_frames[dataset]
            synthetic = synthetic_frames[dataset]
            for attribute in attribute_map[dataset]:
                if attribute not in synthetic.columns:
                    continue
                original_freq = attribute_frequency(original[attribute])
                synthetic_freq = attribute_frequency(synthetic[attribute])
                states = sorted(set(original_freq.index.tolist()) | set(synthetic_freq.index.tolist()))
                for state in states:
                    records.append(
                        {
                            "size": size,
                            "dataset": dataset,
                            "attribute": attribute,
                            "state": state,
                            "original_frequency": float(original_freq.get(state, 0.0)),
                            "synthetic_frequency": float(synthetic_freq.get(state, 0.0)),
                        }
                    )

    return pd.DataFrame.from_records(records)


def plot_wasserstein_summary(metrics: pd.DataFrame, output_path: Path) -> None:
    summary = (
        metrics.groupby(["size", "dataset"])["wasserstein"]
        .agg(["mean", "median", "max"])
        .reset_index()
        .sort_values(["size", "dataset"])
    )

    sizes = sorted(summary["size"].unique())
    x = np.arange(len(DATASET_ORDER))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, size in enumerate(sizes):
        subset = summary.loc[summary["size"] == size].set_index("dataset").reindex(DATASET_ORDER)
        ax.bar(
            x + (i - (len(sizes) - 1) / 2) * width,
            subset["mean"],
            width=width,
            label=f"{size} persons",
            color=["#577590", "#90be6d"][i % 2],
        )

    ax.set_xticks(x)
    ax.set_xticklabels([DATASET_LABELS[dataset] for dataset in DATASET_ORDER], rotation=15, ha="right")
    ax.set_ylabel("Mean Wasserstein distance")
    ax.set_title("Mean marginal Wasserstein distance by dataset")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_focus_wasserstein(metrics: pd.DataFrame, output_path: Path) -> None:
    focus_rows: List[pd.DataFrame] = []
    for dataset, attributes in FOCUS_WASSERSTEIN_ATTRIBUTES.items():
        focus_rows.append(
            metrics.loc[
                (metrics["dataset"] == dataset) & (metrics["attribute"].isin(attributes)),
                :,
            ].copy()
        )

    focus = pd.concat(focus_rows, ignore_index=True)
    focus["attribute_label"] = focus["dataset"] + ": " + focus["attribute"]
    focus = focus.sort_values(["dataset", "attribute", "size"])

    labels = focus["attribute_label"].drop_duplicates().tolist()
    label_positions = np.arange(len(labels))
    widths = 0.35

    fig, ax = plt.subplots(figsize=(11, 7))
    for i, size in enumerate(sorted(focus["size"].unique())):
        subset = (
            focus.loc[focus["size"] == size, ["attribute_label", "wasserstein"]]
            .set_index("attribute_label")
            .reindex(labels)
        )
        ax.barh(
            label_positions + (i - 0.5) * widths,
            subset["wasserstein"],
            height=widths,
            label=f"{size} persons",
            color=["#4d908e", "#f9844a"][i % 2],
        )

    ax.set_yticks(label_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Wasserstein distance")
    ax.set_title("Wasserstein distance for key validation attributes")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_marginal_fit_scatter(points: pd.DataFrame, size: int, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for ax, dataset in zip(axes, DATASET_ORDER):
        subset = points.loc[(points["size"] == size) & (points["dataset"] == dataset)].copy()
        x = subset["original_frequency"].to_numpy(dtype=float)
        y = subset["synthetic_frequency"].to_numpy(dtype=float)
        fit = fit_regression(x, y)
        max_value = max(float(x.max(initial=0.0)), float(y.max(initial=0.0)), 1e-6)

        ax.scatter(x, y, s=14, alpha=0.55, color=DATASET_COLORS[dataset])
        ax.plot([0, max_value], [0, max_value], linestyle="--", color="#666666", linewidth=1)
        if np.isfinite(fit["slope"]):
            grid = np.linspace(0, max_value, 100)
            ax.plot(grid, fit["intercept"] + fit["slope"] * grid, color="#111111", linewidth=1.2)

        ax.set_title(DATASET_LABELS[dataset])
        ax.set_xlabel("Original frequency")
        ax.set_ylabel("Synthetic frequency")
        ax.grid(alpha=0.2)
        ax.text(
            0.03,
            0.97,
            f"slope={fit['slope']:.3f}\n$R^2$={fit['r2']:.3f}\npoints={len(subset)}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        )

    fig.suptitle(f"Marginal frequency fit against original data ({size} synthetic persons)", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_focus_regressions(
    specs: Sequence[Dict[str, object]],
    title: str,
    size: int,
    original_frames: Dict[str, pd.DataFrame],
    synthetic_frames: Dict[str, pd.DataFrame],
    output_path: Path,
) -> None:
    ncols = 2
    nrows = int(np.ceil(len(specs) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 4.5 * nrows))
    axes = np.atleast_1d(axes).flatten()

    for ax, spec in zip(axes, specs):
        dataset = str(spec["dataset"])
        columns = list(spec["columns"])
        x, y = aligned_frequency_arrays(original_frames[dataset], synthetic_frames[dataset], columns)
        fit = fit_regression(x, y)
        max_value = max(float(x.max(initial=0.0)), float(y.max(initial=0.0)), 1e-6)

        ax.scatter(x, y, s=26, alpha=0.7, color=DATASET_COLORS[dataset])
        ax.plot([0, max_value], [0, max_value], linestyle="--", color="#666666", linewidth=1)
        if np.isfinite(fit["slope"]):
            grid = np.linspace(0, max_value, 100)
            ax.plot(grid, fit["intercept"] + fit["slope"] * grid, color="#111111", linewidth=1.2)

        ax.set_title(str(spec["label"]))
        ax.set_xlabel("Original cell frequency")
        ax.set_ylabel("Synthetic cell frequency")
        ax.grid(alpha=0.2)
        ax.text(
            0.03,
            0.97,
            f"slope={fit['slope']:.3f}\n$R^2$={fit['r2']:.3f}\ncells={len(x)}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        )

    for ax in axes[len(specs) :]:
        ax.axis("off")

    fig.suptitle(f"{title} ({size} synthetic persons)", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def format_metric_table(df: pd.DataFrame, columns: Sequence[str]) -> List[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def format_profile_table(df: pd.DataFrame, sample_sizes: Sequence[int]) -> List[str]:
    columns = ["indicator", *[str(size) for size in sample_sizes]]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]

    for indicator, row in df.iterrows():
        values = [str(indicator)]
        for size in sample_sizes:
            value = float(row[size])
            if "Synthetic" in str(indicator):
                values.append(f"{int(round(value)):,}")
            else:
                values.append(f"{value:.1f}")
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_report(
    original_frames: Dict[str, pd.DataFrame],
    wasserstein_metrics: pd.DataFrame,
    regression_metrics: pd.DataFrame,
    person_profile: pd.DataFrame,
    sme_profile: pd.DataFrame,
    sample_sizes: Sequence[int],
) -> None:
    dataset_summary = (
        wasserstein_metrics.groupby(["size", "dataset"])["wasserstein"]
        .agg(["mean", "median", "max"])
        .reset_index()
    )

    top_worst = (
        wasserstein_metrics.sort_values(["size", "wasserstein"], ascending=[True, False])
        .groupby("size")
        .head(10)
        .copy()
    )
    top_worst["dataset"] = top_worst["dataset"].map(DATASET_LABELS)

    regression_table = regression_metrics.copy()
    regression_table["dataset"] = regression_table["dataset"].map(DATASET_LABELS)

    lines = [
        "# Egypt Synthetic Population Validation",
        "",
        "## Scope",
        "",
        "This report validates the synthetic persons and SMEs generated in `model.py` against the harmonized source microdata from LFS 2024, Global Findex Egypt, ELMPS 2023 persons, and ELMPS 2023 enterprises.",
        "",
        "The validation follows the same logic as the reference workflow: marginal Wasserstein distances, regression slopes and coefficients for selected joint distributions, and scatter plots comparing synthetic and original frequencies.",
        "",
        "## Synthetic Population Profile",
        "",
        "### Persons",
        "",
    ]
    lines.extend(format_profile_table(person_profile, sample_sizes))
    lines.extend(
        [
            "",
            "### SMEs",
            "",
        ]
    )
    lines.extend(format_profile_table(sme_profile, sample_sizes))
    lines.extend(
        [
            "",
        "## Source Frames",
        "",
        f"- LFS 2024 persons: `{len(original_frames['lfs']):,}` rows",
        f"- Global Findex Egypt persons: `{len(original_frames['findex']):,}` rows",
        f"- ELMPS 2023 persons: `{len(original_frames['elmps_person']):,}` rows",
        f"- ELMPS 2023 SMEs: `{len(original_frames['sme']):,}` rows",
        "",
        "## Wasserstein Summary",
        "",
        "![Wasserstein summary](../outputs/validation/wasserstein_summary.png)",
        "",
        "![Wasserstein focus attributes](../outputs/validation/wasserstein_focus_attributes.png)",
        "",
        ]
    )

    for size in sample_sizes:
        lines.append(f"### {size} synthetic persons")
        lines.append("")
        size_summary = dataset_summary.loc[dataset_summary["size"] == size].copy()
        size_summary["dataset"] = size_summary["dataset"].map(DATASET_LABELS)
        lines.extend(format_metric_table(size_summary[["dataset", "mean", "median", "max"]], ["dataset", "mean", "median", "max"]))
        lines.append("")
        lines.append(f"![Marginal fit {size}](../outputs/validation/marginal_fit_scatter_{size}.png)")
        lines.append("")
        lines.append(f"![Person regressions {size}](../outputs/validation/person_focus_regressions_{size}.png)")
        lines.append("")
        lines.append(f"![SME regressions {size}](../outputs/validation/sme_focus_regressions_{size}.png)")
        lines.append("")

    lines.extend(
        [
            "## Largest Marginal Mismatches",
            "",
        ]
    )
    for size in sample_sizes:
        lines.append(f"### Top 10 Wasserstein distances for {size} synthetic persons")
        lines.append("")
        size_top = top_worst.loc[top_worst["size"] == size, ["dataset", "attribute", "wasserstein"]]
        lines.extend(format_metric_table(size_top, ["dataset", "attribute", "wasserstein"]))
        lines.append("")

    lines.extend(
        [
            "## Regression Metrics For Selected Joint Distributions",
            "",
        ]
    )
    for size in sample_sizes:
        lines.append(f"### {size} synthetic persons")
        lines.append("")
        subset = regression_table.loc[
            regression_table["size"] == size,
            ["dataset", "label", "columns", "slope", "r2", "num_cells"],
        ]
        lines.extend(format_metric_table(subset, ["dataset", "label", "columns", "slope", "r2", "num_cells"]))
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- Wasserstein distances are computed on the harmonized discrete state supports of each attribute.",
            "- Regression slopes and $R^2$ values come from linear regressions between original and synthetic normalized cell frequencies.",
            "- The selected joint distributions emphasize the combinations requested for validation: gender, job formality, SME formality, workforce and firm size, urbanicity, and financial behaviour including savings, account ownership, and barriers.",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading original harmonized frames...")
    original_frames = load_original_frames()

    print("Loading synthetic populations...")
    synthetic_outputs_by_size = {size: load_synthetic_outputs(size) for size in args.sample_sizes}
    synthetic_frames_by_size = {
        size: build_validation_frames(outputs) for size, outputs in synthetic_outputs_by_size.items()
    }
    person_profile, sme_profile = compute_population_profiles(synthetic_outputs_by_size)

    print("Computing Wasserstein distances...")
    wasserstein_metrics = compute_wasserstein_metrics(original_frames, synthetic_frames_by_size)
    wasserstein_metrics.to_csv(VALIDATION_DIR / "wasserstein_metrics.csv", index=False)

    print("Computing regression metrics...")
    regression_metrics = compute_regression_metrics(original_frames, synthetic_frames_by_size)
    regression_metrics.to_csv(VALIDATION_DIR / "regression_metrics.csv", index=False)

    print("Preparing marginal fit points...")
    marginal_points = compute_marginal_fit_points(original_frames, synthetic_frames_by_size)
    marginal_points.to_csv(VALIDATION_DIR / "marginal_fit_points.csv", index=False)

    print("Generating plots...")
    plot_wasserstein_summary(wasserstein_metrics, VALIDATION_DIR / "wasserstein_summary.png")
    plot_focus_wasserstein(wasserstein_metrics, VALIDATION_DIR / "wasserstein_focus_attributes.png")
    for size in args.sample_sizes:
        plot_marginal_fit_scatter(
            marginal_points,
            size,
            VALIDATION_DIR / f"marginal_fit_scatter_{size}.png",
        )
        plot_focus_regressions(
            PERSON_COMBINATION_SPECS,
            "Person-level focus regressions",
            size,
            original_frames,
            synthetic_frames_by_size[size],
            VALIDATION_DIR / f"person_focus_regressions_{size}.png",
        )
        plot_focus_regressions(
            SME_COMBINATION_SPECS,
            "SME focus regressions",
            size,
            original_frames,
            synthetic_frames_by_size[size],
            VALIDATION_DIR / f"sme_focus_regressions_{size}.png",
        )

    print("Writing validation report...")
    write_report(
        original_frames,
        wasserstein_metrics,
        regression_metrics,
        person_profile,
        sme_profile,
        args.sample_sizes,
    )
    print(f"Saved validation outputs to {VALIDATION_DIR}")
    print(f"Saved validation report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
