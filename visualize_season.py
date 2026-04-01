#!/usr/bin/env python3
"""
DTFBL Season Visualization
---------------------------
Reads data/standings_log.csv and produces a stacked area chart
showing each team's cumulative points over the season —
the Civilization-style "who's winning the long game" view.

Run any time during or after the season:
    python3 visualize_season.py
"""

import csv
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

DATA_FILE = Path(__file__).parent / "data" / "standings_log.csv"

TEAM_COLORS = {
    "Forest Rangers":  "#2d6a4f",   # forest green
    "Bert's Bombers":  "#e63946",   # red
    "Charlie's Stars": "#f4a261",   # orange
    "Ryan's Lions":    "#457b9d",   # steel blue
    "David's Devils":  "#6d2b8f",   # purple
    "Jake's Snakes":   "#e9c46a",   # gold
    "Jon's Generals":  "#264653",   # dark teal  ← you
}

JON = "Jon's Generals"


def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"No data yet at {DATA_FILE}. "
            "Run onroto_scraper.py at least once first."
        )

    dates, team_series = [], {}
    with open(DATA_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = datetime.strptime(row["date"], "%Y-%m-%d")
            except ValueError:
                continue
            dates.append(d)
            for team in TEAM_COLORS:
                val = row.get(team, "") or "0"
                try:
                    team_series.setdefault(team, []).append(float(val))
                except ValueError:
                    team_series.setdefault(team, []).append(0.0)

    return dates, team_series


def plot(dates, team_series):
    fig, (ax_area, ax_line) = plt.subplots(
        2, 1, figsize=(14, 10),
        gridspec_kw={"height_ratios": [2, 1]}
    )
    fig.patch.set_facecolor("#1a1a2e")
    for ax in (ax_area, ax_line):
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444466")

    # ── Top: Stacked area (Civilization style) ────────────────────────────────
    # Sort teams by final total so the biggest are at the bottom of the stack
    team_order = sorted(
        team_series.keys(),
        key=lambda t: team_series[t][-1] if team_series[t] else 0
    )

    ys = np.array([team_series[t] for t in team_order], dtype=float)
    xs = mdates.date2num(dates)

    ax_area.stackplot(
        xs, ys,
        labels=team_order,
        colors=[TEAM_COLORS[t] for t in team_order],
        alpha=0.85,
    )

    # Highlight Jon's boundary with a bold line
    jon_idx   = team_order.index(JON)
    cumulative = np.cumsum(ys, axis=0)
    bottom     = cumulative[jon_idx - 1] if jon_idx > 0 else np.zeros(len(dates))
    top        = cumulative[jon_idx]
    ax_area.fill_between(xs, bottom, top, color=TEAM_COLORS[JON], alpha=1.0, zorder=5)
    ax_area.plot(xs, top, color="white", lw=1.5, ls="--", zorder=6, alpha=0.6)

    ax_area.set_title("DTFBL 2026 — Season Points (stacked)", fontsize=14, pad=12)
    ax_area.set_ylabel("Cumulative Points", color="white")
    ax_area.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_area.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    plt.setp(ax_area.xaxis.get_majorticklabels(), rotation=30, ha="right")

    legend = ax_area.legend(
        loc="upper left", fontsize=8,
        facecolor="#1a1a2e", labelcolor="white",
        edgecolor="#444466",
    )

    # ── Bottom: Jon's pts vs league average ──────────────────────────────────
    jon_pts  = np.array(team_series[JON], dtype=float)
    all_pts  = np.array([team_series[t] for t in team_series], dtype=float)
    avg_pts  = all_pts.mean(axis=0)
    best_pts = all_pts.max(axis=0)

    ax_line.plot(xs, jon_pts,  color=TEAM_COLORS[JON], lw=2.5, label="Jon's Generals")
    ax_line.plot(xs, avg_pts,  color="white",           lw=1.5, ls="--", alpha=0.6, label="League avg")
    ax_line.plot(xs, best_pts, color="#f4a261",          lw=1.0, ls=":",  alpha=0.5, label="League leader")
    ax_line.fill_between(xs, avg_pts, jon_pts,
                         where=(jon_pts >= avg_pts),
                         alpha=0.25, color=TEAM_COLORS[JON], label="Above avg")
    ax_line.fill_between(xs, avg_pts, jon_pts,
                         where=(jon_pts < avg_pts),
                         alpha=0.25, color="#e63946",         label="Below avg")

    ax_line.set_title("Jon's Generals vs League", fontsize=11, pad=8)
    ax_line.set_ylabel("Points", color="white")
    ax_line.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_line.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    plt.setp(ax_line.xaxis.get_majorticklabels(), rotation=30, ha="right")
    legend2 = ax_line.legend(
        fontsize=8, facecolor="#1a1a2e", labelcolor="white", edgecolor="#444466"
    )

    plt.tight_layout(pad=2.0)

    out = Path(__file__).parent / "data" / "season_chart.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Chart saved to {out}")
    plt.show()


if __name__ == "__main__":
    dates, team_series = load_data()
    print(f"Loaded {len(dates)} days of data")
    if len(dates) < 2:
        print("Need at least 2 days of data for a useful chart. Check back tomorrow!")
    else:
        plot(dates, team_series)
