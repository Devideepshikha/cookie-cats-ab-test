"""A/B test analysis for the mobile game Cookie Cats.

Question: the game moved its first "gate" (a forced wait, or pay to skip)
from level 30 to level 40 for half of new players. Did that change how
many players came back 1 day and 7 days after installing?

Run with: python ab_test.py
It downloads the data the first time, prints the results, saves charts
to charts/ and writes a summary to results.md.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save charts to files without opening windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

DATA_URL = "https://raw.githubusercontent.com/robguilarr/ab_testing_cookie_cats/main/datasets/cookie_cats.csv"
DATA_PATH = Path("data/cookie_cats.csv")
CHARTS = Path("charts")
CONTROL, TREATMENT = "gate_30", "gate_40"
METRICS = ["retention_1", "retention_7"]
OUTLIER_ROUNDS = 10_000  # no real player plays this many rounds in 14 days


def load_data(path=DATA_PATH, url=DATA_URL):
    """Read the dataset, downloading it once if it isn't on disk yet."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.read_csv(url).to_csv(path, index=False)
    return pd.read_csv(path)


def clean(df):
    """Check data quality and remove impossible outliers. Returns (clean df, notes)."""
    notes = []
    notes.append(f"{len(df):,} players, {df['userid'].duplicated().sum()} duplicate user IDs, "
                 f"{int(df.isna().sum().sum())} missing values")
    outliers = df[df["sum_gamerounds"] > OUTLIER_ROUNDS]
    notes.append(f"Removed {len(outliers)} player(s) with more than {OUTLIER_ROUNDS:,} game rounds "
                 f"(max was {df['sum_gamerounds'].max():,})")
    return df[df["sum_gamerounds"] <= OUTLIER_ROUNDS].copy(), notes


def sample_ratio_check(df):
    """Chi-square test that players were split 50/50 between the groups (sample ratio mismatch)."""
    counts = df["version"].value_counts()
    observed = [counts[CONTROL], counts[TREATMENT]]
    _, p_value = stats.chisquare(observed)
    return counts.to_dict(), p_value


def retention_rates(df):
    """Share of players in each group who returned after 1 and 7 days."""
    return df.groupby("version")[METRICS].mean()


def two_proportion_ztest(df, metric):
    """Two-sided z-test for the difference in a retention rate between the groups."""
    a = df[df["version"] == CONTROL][metric]
    b = df[df["version"] == TREATMENT][metric]
    p_a, p_b = a.mean(), b.mean()
    pooled = (a.sum() + b.sum()) / (len(a) + len(b))
    se = np.sqrt(pooled * (1 - pooled) * (1 / len(a) + 1 / len(b)))
    z = (p_a - p_b) / se
    p_value = 2 * stats.norm.sf(abs(z))
    return p_a - p_b, z, p_value


def bootstrap_difference(df, metric, n_boot=1000, seed=42):
    """Resample players with replacement and return the gate_30 minus gate_40 difference each time."""
    rng = np.random.default_rng(seed)
    a = df[df["version"] == CONTROL][metric].to_numpy(dtype=float)
    b = df[df["version"] == TREATMENT][metric].to_numpy(dtype=float)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean()
    return diffs


def engagement_segments(df):
    """7-day retention by how many rounds players played, for each group."""
    bins = [-1, 0, 10, 30, 100, np.inf]
    labels = ["0 rounds", "1-10", "11-30", "31-100", "100+"]
    seg = df.assign(segment=pd.cut(df["sum_gamerounds"], bins=bins, labels=labels))
    return seg.pivot_table(index="segment", columns="version", values="retention_7",
                           aggfunc="mean", observed=False)




def plot_bootstrap(results):
    CHARTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for metric, diffs in results.items():
        ax.hist(diffs * 100, bins=40, alpha=0.6, label=metric.replace("_", " "))
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Retention difference, gate_30 minus gate_40 (percentage points)")
    ax.set_ylabel("Bootstrap samples")
    ax.set_title("Bootstrap distribution of the retention difference")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHARTS / "bootstrap_retention_difference.png", dpi=150)
    plt.close(fig)


def plot_segments(table):
    CHARTS.mkdir(exist_ok=True)
    ax = (table * 100).plot(kind="bar", figsize=(8, 4.5), rot=0)
    ax.set_xlabel("Game rounds played in the first 14 days")
    ax.set_ylabel("7-day retention (%)")
    ax.set_title("7-day retention by engagement segment")
    plt.tight_layout()
    plt.savefig(CHARTS / "retention_by_segment.png", dpi=150)
    plt.close()


def main():
    df, notes = clean(load_data())
    counts, srm_p = sample_ratio_check(df)
    rates = retention_rates(df)

    lines = ["# Results", "", "## Data checks", ""] + [f"- {n}" for n in notes]
    lines += [f"- Players per group: {counts[CONTROL]:,} ({CONTROL}) and {counts[TREATMENT]:,} ({TREATMENT}); "
              f"sample ratio check p = {srm_p:.3f}", "", "## Retention", "",
              "| Metric | gate_30 | gate_40 | Difference (pp) | z-test p-value | Bootstrap: chance gate_30 is better |",
              "| --- | --- | --- | --- | --- | --- |"]
    boot = {}
    for metric in METRICS:
        diff, z, p = two_proportion_ztest(df, metric)
        diffs = bootstrap_difference(df, metric)
        boot[metric] = diffs
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        lines.append(f"| {metric} | {rates.loc[CONTROL, metric]:.2%} | {rates.loc[TREATMENT, metric]:.2%} | "
                     f"{diff * 100:.2f} (95% CI {lo * 100:.2f} to {hi * 100:.2f}) | {p:.4f} | {(diffs > 0).mean():.1%} |")

    rounds_p = stats.mannwhitneyu(df[df["version"] == CONTROL]["sum_gamerounds"],
                                  df[df["version"] == TREATMENT]["sum_gamerounds"]).pvalue
    segments = engagement_segments(df)
    lines += ["", f"Game rounds played (Mann-Whitney U test): p = {rounds_p:.3f}", "",
              "## 7-day retention by engagement segment", "",
              "| Rounds played | gate_30 | gate_40 |", "| --- | --- | --- |"]
    lines += [f"| {seg} | {row[CONTROL]:.1%} | {row[TREATMENT]:.1%} |" for seg, row in segments.iterrows()]

    plot_bootstrap(boot)
    plot_segments(segments)
    Path("results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\nCharts saved to charts/, summary saved to results.md")


if __name__ == "__main__":
    main()