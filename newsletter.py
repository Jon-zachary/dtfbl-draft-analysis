#!/usr/bin/env python3
"""
DTFBL Newsletter Visualizations
---------------------------------
Generates interactive HTML charts for the biweekly league newsletter.

Charts produced (saved to visualizations/):
  civ_chart.html     — Animated stacked area, Civilization end-game style
  pace_chart.html    — Points pace + projected season total per team
  draft_profile.html — How each team allocated $260, sorted by current standing

Usage:
    python3 newsletter.py
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import openpyxl

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VIZ_DIR  = BASE_DIR / "visualizations"

# ── League constants ──────────────────────────────────────────────────────────

TEAMS = [
    "Forest Rangers",
    "Bert's Bombers",
    "Charlie's Stars",
    "Ryan's Lions",
    "David's Devils",
    "Jake's Snakes",
    "Jon's Generals",
]

TEAM_COLORS = {
    "Forest Rangers":  "#27ae60",   # green
    "Bert's Bombers":  "#e74c3c",   # red
    "Charlie's Stars": "#2980b9",   # steel blue
    "Ryan's Lions":    "#e67e22",   # orange
    "David's Devils":  "#8e44ad",   # purple
    "Jake's Snakes":   "#e91e8c",   # fuchsia
    "Jon's Generals":  "#f1c40f",   # bright yellow (you — stands out on dark bg)
}

SEASON_START = date(2026, 3, 26)
SEASON_END   = date(2026, 9, 28)   # last day of MLB regular season

TEAM_IDS = {
    "Forest Rangers":  "0",
    "Bert's Bombers":  "1",
    "Charlie's Stars": "2",
    "Ryan's Lions":    "3",
    "David's Devils":  "4",
    "Jake's Snakes":   "5",
    "Jon's Generals":  "6",
}

PLAYER_STATS_CACHE = DATA_DIR / "player_stats.json"

MIN_G = 3   # ignore players with fewer games than this


def rgba(hex_color: str, alpha: float) -> str:
    """Convert '#rrggbb' + alpha float to 'rgba(r,g,b,a)' for Plotly."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_standings() -> pd.DataFrame:
    """
    Load and clean data/standings_log.csv.
    Returns one row per calendar date (last snapshot per day wins),
    with a zero row prepended at SEASON_START.
    """
    df = pd.read_csv(DATA_DIR / "standings_log.csv", parse_dates=["date"])
    df = df[["date"] + TEAMS].copy()

    # Dedup: keep the last snapshot logged per calendar day
    df["_day"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.sort_values("date").drop_duplicates("_day", keep="last")
    df = df.drop(columns=["_day"]).reset_index(drop=True)

    # Drop all-zero rows (pre-season noise before any games were played)
    df = df[df[TEAMS].sum(axis=1) > 0].reset_index(drop=True)

    # Prepend a zero row at season start so the chart starts from the origin
    zero = {"date": pd.Timestamp(SEASON_START), **{t: 0.0 for t in TEAMS}}
    df = pd.concat([pd.DataFrame([zero]), df], ignore_index=True)

    return df.sort_values("date").reset_index(drop=True)


def parse_draft_2026() -> pd.DataFrame:
    """
    Parse DTFBL Draft 2026.xlsx.

    The workbook has a single sheet split into two sections:
      Section 1  rows 4-18  (0-indexed 3-17):  Forest Rangers, Bert's, Charlie's, Ryan's
      Section 2  rows 22-36 (0-indexed 21-35):  David's, Jake's, Jon's

    Each section has 6-column blocks per team: Name | MLB | Price | (blank) | $Left
    starting at columns 1, 7, 13, 19 (section 1) or 1, 7, 13 (section 2).

    Returns DataFrame with columns: team, position, player, mlb_team, price
    """
    wb   = openpyxl.load_workbook(BASE_DIR / "DTFBL Draft 2026.xlsx", data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))

    records = []

    def extract(rows_slice, team_col_map):
        """
        rows_slice  : list of row tuples
        team_col_map: {team_name: (name_col, mlb_col, price_col)}
        """
        for row in rows_slice:
            pos = row[0]
            if not isinstance(pos, str) or pos.lower() == "position":
                continue
            for team, (nc, mc, pc) in team_col_map.items():
                name  = row[nc]
                mlb   = row[mc]
                price = row[pc]
                if not isinstance(name, str) or not isinstance(price, (int, float)):
                    continue
                records.append({
                    "team":     team,
                    "position": pos.strip(),
                    "player":   name.strip(),
                    "mlb_team": str(mlb).strip() if mlb else "?",
                    "price":    int(price),
                })

    # Section 1: data in rows[3:18]  (R04–R18; totals row has None name, skipped)
    extract(rows[3:18], {
        "Forest Rangers":  (1,  2,  3),
        "Bert's Bombers":  (7,  8,  9),
        "Charlie's Stars": (13, 14, 15),
        "Ryan's Lions":    (19, 20, 21),
    })

    # Section 2: data in rows[21:36]  (R22–R36; totals row skipped same way)
    extract(rows[21:36], {
        "David's Devils":  (1,  2,  3),
        "Jake's Snakes":   (7,  8,  9),
        "Jon's Generals":  (13, 14, 15),
    })

    return pd.DataFrame(records)


# ── Chart 1: Civilization Chart ───────────────────────────────────────────────

def civ_chart(df: pd.DataFrame, out: Path = VIZ_DIR / "civ_chart.html"):
    """
    Animated stacked area chart of cumulative season points.
    Each frame reveals one more date, drawing left-to-right like the
    Civilization end-game score graph.

    Controls:
      ▶ Play  — animates from the beginning (~1800 ms per frame)
      ⏸ Pause — freezes at current frame
      Slider  — scrub to any date manually
    """
    # Stack order: lowest current total at bottom, leader on top
    final_totals = df.iloc[-1][TEAMS]
    team_order   = final_totals.sort_values().index.tolist()  # ascending = bottom first

    x_min  = df["date"].min() - pd.Timedelta(days=1)
    x_max  = df["date"].max() + pd.Timedelta(days=3)

    def make_traces(sub: pd.DataFrame) -> list[go.Scatter]:
        traces = []
        for team in team_order:
            is_jon = team == "Jon's Generals"
            traces.append(go.Scatter(
                x=sub["date"],
                y=sub[team],
                customdata=sub[team],   # raw pts for hover (y will be % after groupnorm)
                name=team,
                mode="lines",
                stackgroup="one",
                groupnorm="percent",
                line=dict(
                    color=TEAM_COLORS[team],
                    width=2.5 if is_jon else 0.5,
                ),
                fillcolor=rgba(TEAM_COLORS[team], 0.85 if is_jon else 0.65),
                hovertemplate=(
                    f"<b>{team}</b><br>%{{x|%b %d}}: "
                    f"%{{customdata:.0f}} pts (%{{y:.1f}}%)<extra></extra>"
                ),
            ))
        return traces

    # Build one animation frame per date snapshot
    frames = [
        go.Frame(data=make_traces(df.iloc[:i + 1]), name=f"f{i}")
        for i in range(len(df))
    ]

    slider_steps = [
        dict(
            method="animate",
            args=[[f"f{i}"], dict(mode="immediate", frame=dict(duration=0, redraw=True))],
            label=df["date"].iloc[i].strftime("%b %d"),
        )
        for i in range(len(df))
    ]

    fig = go.Figure(
        data=make_traces(df),            # start fully revealed
        frames=frames,
        layout=go.Layout(
            title=dict(
                text="DTFBL 2026 — Season Points Race",
                font=dict(size=24, color="white", family="Arial Black"),
                x=0.5, xanchor="center",
            ),
            template="plotly_dark",
            paper_bgcolor="#0d0d1a",
            plot_bgcolor="#0d0d1a",
            hovermode="x unified",
            xaxis=dict(
                range=[x_min, x_max],
                showgrid=True, gridcolor="#1e1e3a",
                tickformat="%b %d", tickfont=dict(color="#9999bb"),
                fixedrange=True,
            ),
            yaxis=dict(
                range=[0, 100],
                title="Share of Total Points",
                ticksuffix="%",
                showgrid=True, gridcolor="#1e1e3a",
                tickfont=dict(color="#9999bb"),
                fixedrange=True,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                font=dict(color="white", size=11),
                bgcolor="rgba(0,0,0,0)",
                traceorder="reversed",    # leader at top of legend too
            ),
            margin=dict(t=100, b=110, l=75, r=20),
            height=580,
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                bgcolor="#1e1e3a",
                bordercolor="#444466",
                font=dict(color="white"),
                x=0.5, y=-0.16,
                xanchor="center", yanchor="top",
                buttons=[
                    dict(
                        label="▶  Play",
                        method="animate",
                        args=[
                            None,   # None = play all frames from beginning
                            dict(
                                frame=dict(duration=1800, redraw=True),
                                fromcurrent=False,
                                mode="immediate",
                            ),
                        ],
                    ),
                    dict(
                        label="⏸  Pause",
                        method="animate",
                        args=[[None], dict(frame=dict(duration=0), mode="immediate")],
                    ),
                ],
            )],
            sliders=[dict(
                active=len(df) - 1,         # start at rightmost = fully revealed
                bgcolor="#1e1e3a",
                bordercolor="#444466",
                font=dict(color="white", size=10),
                currentvalue=dict(
                    prefix="Date: ",
                    font=dict(color="white", size=12),
                    xanchor="center",
                ),
                pad=dict(t=45, b=10),
                steps=slider_steps,
            )],
        ),
    )

    VIZ_DIR.mkdir(exist_ok=True)
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"✓  civ_chart.html")
    return fig


# ── Chart 2: Points Behind Leader ────────────────────────────────────────────

def gap_chart(df: pd.DataFrame, out: Path = VIZ_DIR / "gap_chart.html"):
    """
    Animated line chart showing each team's deficit vs the day's leader.
    Leader sits at 0 (top); everyone else is plotted as negative points behind.
    Reveals the shape of the race: who's pulling away, who's closing the gap.
    """
    # Pre-compute gap DataFrame: team_score - day's leader score (≤ 0)
    gap_df = df.copy()
    for idx, row in df.iterrows():
        leader_pts = row[TEAMS].max()
        for team in TEAMS:
            gap_df.at[idx, team] = row[team] - leader_pts

    # Order by final gap: leader (0) at top, most behind at bottom
    final_gaps = gap_df.iloc[-1][TEAMS]
    team_order = final_gaps.sort_values(ascending=False).index.tolist()

    x_min   = df["date"].min() - pd.Timedelta(days=1)
    x_max   = df["date"].max() + pd.Timedelta(days=3)
    min_gap = gap_df[TEAMS].min().min()
    y_range = [min_gap * 1.15, 10]   # 0 near top, worst deficit at bottom

    snap_date = df.iloc[-1]["date"].date()

    def make_traces(sub_gap: pd.DataFrame, sub_raw: pd.DataFrame) -> list[go.Scatter]:
        traces = []
        for team in team_order:
            is_jon = team == "Jon's Generals"
            traces.append(go.Scatter(
                x=sub_gap["date"],
                y=sub_gap[team],
                customdata=sub_raw[team],
                name=team,
                mode="lines",
                line=dict(
                    color=TEAM_COLORS[team],
                    width=3.5 if is_jon else 1.5,
                    dash="solid",
                ),
                hovertemplate=(
                    f"<b>{team}</b><br>%{{x|%b %d}}: "
                    f"%{{customdata:.0f}} pts  (%{{y:+.0f}} vs leader)<extra></extra>"
                ),
            ))
        return traces

    frames = [
        go.Frame(
            data=make_traces(gap_df.iloc[:i + 1], df.iloc[:i + 1]),
            name=f"f{i}",
        )
        for i in range(len(gap_df))
    ]

    slider_steps = [
        dict(
            method="animate",
            args=[[f"f{i}"], dict(mode="immediate", frame=dict(duration=0, redraw=True))],
            label=df["date"].iloc[i].strftime("%b %d"),
        )
        for i in range(len(df))
    ]

    fig = go.Figure(
        data=make_traces(gap_df, df),
        frames=frames,
        layout=go.Layout(
            title=dict(
                text=(
                    "DTFBL 2026 — Points Behind Leader<br>"
                    f"<sup>As of {snap_date.strftime('%B %d')} "
                    "· leader sits at 0 · gap closes = you're gaining</sup>"
                ),
                font=dict(size=24, color="white", family="Arial Black"),
                x=0.5, xanchor="center",
            ),
            template="plotly_dark",
            paper_bgcolor="#0d0d1a",
            plot_bgcolor="#0d0d1a",
            hovermode="x unified",
            shapes=[dict(
                type="line",
                x0=x_min, x1=x_max, y0=0, y1=0,
                line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
            )],
            xaxis=dict(
                range=[x_min, x_max],
                showgrid=True, gridcolor="#1e1e3a",
                tickformat="%b %d", tickfont=dict(color="#9999bb"),
                fixedrange=True,
            ),
            yaxis=dict(
                range=y_range,
                title="Points Behind Leader",
                showgrid=True, gridcolor="#1e1e3a",
                tickfont=dict(color="#9999bb"),
                zeroline=False,
                fixedrange=True,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                font=dict(color="white", size=11),
                bgcolor="rgba(0,0,0,0)",
                traceorder="normal",
            ),
            margin=dict(t=110, b=110, l=75, r=20),
            height=580,
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                bgcolor="#1e1e3a",
                bordercolor="#444466",
                font=dict(color="white"),
                x=0.5, y=-0.16,
                xanchor="center", yanchor="top",
                buttons=[
                    dict(
                        label="▶  Play",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=1800, redraw=True),
                                fromcurrent=False,
                                mode="immediate",
                            ),
                        ],
                    ),
                    dict(
                        label="⏸  Pause",
                        method="animate",
                        args=[[None], dict(frame=dict(duration=0), mode="immediate")],
                    ),
                ],
            )],
            sliders=[dict(
                active=len(df) - 1,
                bgcolor="#1e1e3a",
                bordercolor="#444466",
                font=dict(color="white", size=10),
                currentvalue=dict(
                    prefix="Date: ",
                    font=dict(color="white", size=12),
                    xanchor="center",
                ),
                pad=dict(t=45, b=10),
                steps=slider_steps,
            )],
        ),
    )

    VIZ_DIR.mkdir(exist_ok=True)
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"✓  gap_chart.html")
    return fig


# ── Chart 3: Draft Budget Allocation ─────────────────────────────────────────

def draft_profile_chart(
    draft_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    out: Path = VIZ_DIR / "draft_profile.html",
):
    """
    Stacked horizontal bar showing how each team allocated their $260 by position.
    Teams are sorted by their current season points (best at top) so you can
    visually compare spending patterns with early results.
    """
    # Normalize position labels
    POS_GROUP = {
        "C": "C", "1B": "1B", "2B": "2B", "SS": "SS", "3B": "3B",
        "OF": "OF", "DH": "DH",
        "SP": "SP", "RP": "RP", "SP / RP": "SP/RP",
    }
    GROUP_COLORS = {
        "C":     "#74b9ff",
        "1B":    "#0984e3",
        "2B":    "#00cec9",
        "SS":    "#55efc4",
        "3B":    "#00b894",
        "OF":    "#fdcb6e",
        "DH":    "#e17055",
        "SP":    "#d63031",
        "RP":    "#e84393",
        "SP/RP": "#fd79a8",
    }

    draft_df = draft_df.copy()
    draft_df["pos_group"] = draft_df["position"].map(POS_GROUP).fillna("Other")

    spend = (
        draft_df.groupby(["team", "pos_group"])["price"]
        .sum()
        .reset_index()
    )

    # Sort teams by current season points, best first
    latest = standings_df.iloc[-1]
    teams_sorted = sorted(TEAMS, key=lambda t: -float(latest.get(t, 0)))
    pts_labels   = {t: f"{float(latest.get(t, 0)):.0f} pts" for t in teams_sorted}

    pos_order = ["C", "1B", "2B", "SS", "3B", "OF", "DH", "SP", "RP", "SP/RP"]

    fig = go.Figure()

    MIN_VIS = 8   # minimum display width so $1 segments are visible

    for pg in pos_order:
        sub  = spend[spend["pos_group"] == pg].set_index("team")
        vals      = [int(sub.loc[t, "price"]) if t in sub.index else 0 for t in teams_sorted]
        disp_vals = [max(v, MIN_VIS) if v > 0 else 0 for v in vals]
        # Only add trace if at least one team spent here
        if any(v > 0 for v in vals):
            fig.add_trace(go.Bar(
                name=pg,
                y=teams_sorted,
                x=disp_vals,
                customdata=vals,
                orientation="h",
                marker=dict(
                    color=GROUP_COLORS.get(pg, "#888"),
                    line=dict(width=0),
                ),
                hovertemplate=f"<b>%{{y}}</b> — {pg}: $%{{customdata}}<extra></extra>",
            ))

    # Annotate with current points on the right
    snap_date = standings_df.iloc[-1]["date"].strftime("%b %d")
    for i, team in enumerate(teams_sorted):
        fig.add_annotation(
            x=268, y=i,
            text=pts_labels[team],
            showarrow=False,
            font=dict(color=TEAM_COLORS[team], size=11, family="Arial Bold"),
            xanchor="left",
        )

    fig.update_layout(
        title=dict(
            text=(
                "DTFBL 2026 — Draft Budget Allocation by Position<br>"
                f"<sup>Teams sorted by current season points (as of {snap_date})"
                " · colored labels show pts earned so far</sup>"
            ),
            font=dict(size=20, color="white"),
            x=0.5, xanchor="center",
        ),
        template="plotly_dark",
        paper_bgcolor="#0d0d1a",
        plot_bgcolor="#0d0d1a",
        barmode="stack",
        xaxis=dict(
            title="Draft Dollars Spent ($)",
            range=[0, 310],
            showgrid=True, gridcolor="#1e1e3a",
            tickfont=dict(color="#9999bb"),
        ),
        yaxis=dict(
            tickfont=dict(color="white", size=12),
            autorange="reversed",    # best team at top
        ),
        legend=dict(
            title=dict(text="Position", font=dict(color="white")),
            orientation="v",
            yanchor="middle", y=0.5,
            xanchor="left", x=1.01,
            font=dict(color="white", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(t=110, b=50, l=150, r=130),
        height=430,
    )

    VIZ_DIR.mkdir(exist_ok=True)
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"✓  draft_profile.html")
    return fig


# ── Player stats fetch & cache ────────────────────────────────────────────────

# Known name mismatches between draft xlsx and OnRoto stats page
NAME_FIXES = {
    "jameswoods":           "jameswood",             # draft typo
    "fernandotatis":        "fernandotatisjr",        # Jr. in OnRoto
    "petercrowarmstrong":   "petecrowarmstrong",      # Pete vs Peter
    "cjadams":              "cjabrams",               # draft typo (CJ Abrams)
    "mattolsen":            "mattolson",              # draft typo
    "larsnootbar":          "larsnootbaar",           # draft typo
    "robbyray":             "robbieray",              # Robby vs Robbie
    "christophersanchez":   "cristophersanchez",      # Christopher vs Cristopher
    # Ohtani handled via position in value_chart (hitter/pitcher split)
}


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation/spaces — works for both 'Last, First' and 'First Last'."""
    name = name.replace("*", "").strip()
    if "," in name:                          # OnRoto "Last, First" → "First Last"
        last, first = name.split(",", 1)
        name = f"{first.strip()} {last.strip()}"
    norm = re.sub(r"[.\-'\s]", "", name).lower()
    return NAME_FIXES.get(norm, norm)


def fetch_all_player_stats() -> list[dict]:
    """
    Log in to OnRoto and fetch display_new_multi_stats.pl?...+all+hitters/pitchers.
    This single URL returns all NL players with their G, PTS, and Owner (which
    fantasy team owns them, or empty if FA).
    Saves result to data/player_stats.json.

    Requires ONROTO_USERNAME and ONROTO_PASSWORD in .env
    """
    sys.path.insert(0, str(BASE_DIR))
    from onroto_scraper import login, extract_session_id, first_val
    from bs4 import BeautifulSoup

    LEAGUE_ID = "dtfbl1989"
    BASE_URL  = "https://onroto.fangraphs.com/baseball/webnew"

    print("  Logging in to OnRoto...")
    session, session_id = login()

    all_players = []

    for ptype in ("hitters", "pitchers"):
        url  = (f"{BASE_URL}/display_new_multi_stats.pl"
                f"?{LEAGUE_ID}+6+all+{ptype}&session_id={session_id}")
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        session_id = extract_session_id(resp.text) or session_id

        soup  = BeautifulSoup(resp.text, "html.parser")
        # track by norm key; keep entry with highest G (most stats)
        seen: dict[str, dict] = {}

        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Name" not in headers or "PTS" not in headers:
                continue

            # Fix the colspan shift: "2026 Games By Position" is a single <th>
            # that spans 7 data <td> columns (one per position).  Those sub-columns
            # have no <th> elements on this page, so find_all("th") is 6 entries
            # short.  Replace the spanning header with 7 placeholders so all
            # subsequent header indices align with actual cell indices.
            games_hdr = next(
                (h for h in headers if re.match(r"20\d\d Games", h, re.I)),
                None,
            )
            if games_hdr:
                span_idx = headers.index(games_hdr)
                headers  = (headers[:span_idx]
                            + [f"_g_{i}" for i in range(7)]
                            + headers[span_idx + 1:])

            name_col  = headers.index("Name")
            pts_col   = headers.index("PTS")
            g_col     = headers.index("G") if "G" in headers else None
            owner_col = headers.index("Owner") if "Owner" in headers else None
            team_col  = headers.index("Team")  if "Team"  in headers else None

            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(separator="\n", strip=True) for td in tr.find_all("td")]
                if len(cells) <= pts_col:
                    continue
                raw_name = cells[name_col].split("\n")[0].strip()
                if not raw_name or raw_name.lower() in ("name", "league categories"):
                    continue
                # Strip DL marker and status codes
                clean_name = re.sub(r"\([ab]\d+\)", "", raw_name)
                clean_name = clean_name.replace("(DL)", "").replace("*", "").replace("More", "").strip()
                clean_name = clean_name.split("\n")[0].strip()
                if not clean_name:
                    continue

                try:
                    pts = float(first_val(cells[pts_col]))
                except (ValueError, IndexError):
                    pts = 0.0
                try:
                    g = int(first_val(cells[g_col])) if g_col is not None else 0
                except (ValueError, IndexError):
                    g = 0

                owner = first_val(cells[owner_col]).strip() if owner_col is not None else ""
                mlb   = first_val(cells[team_col]).strip()  if team_col  is not None else "?"

                norm = _normalize(clean_name)
                entry = {
                    "name":  clean_name,
                    "norm":  norm,
                    "owner": owner,
                    "mlb":   mlb,
                    "type":  ptype,
                    "G":     g,
                    "PTS":   pts,
                }
                # Keep whichever entry has more games played
                if norm not in seen or g > seen[norm]["G"]:
                    seen[norm] = entry

        all_players.extend(seen.values())
        print(f"    {ptype}: {len(seen)} players")

    DATA_DIR.mkdir(exist_ok=True)
    PLAYER_STATS_CACHE.write_text(json.dumps(all_players, indent=2))
    print(f"  Cached {len(all_players)} total players → {PLAYER_STATS_CACHE}")
    return all_players


def load_player_stats() -> pd.DataFrame | None:
    """Load cached player stats. Returns None if no cache exists."""
    if not PLAYER_STATS_CACHE.exists():
        return None
    data = json.loads(PLAYER_STATS_CACHE.read_text())
    return pd.DataFrame(data)


# ── Chart 4: Draft Value — Price Paid vs Production ───────────────────────────

def value_chart(
    draft_df: pd.DataFrame,
    player_stats: pd.DataFrame,
    out: Path = VIZ_DIR / "value_chart.html",
):
    """
    Scatter plot: draft price (X) vs VORP (Y).

    VORP = player's season PTS minus the average PTS for all drafted starters
    at the same position. Positive = above replacement, negative = bust.
    Uses total PTS (not pts/G) so all drafted players appear regardless of
    whether the G column was parseable from OnRoto.
    """
    # Build normalized draft lookup: norm_name → {price, team, pos, player}
    draft_df = draft_df.copy()
    draft_df["norm"] = draft_df["player"].apply(_normalize)

    # Ohtani is two separate players in this league — route by position
    _pitcher_pos = {"SP", "RP", "SP / RP", "SP/RP"}
    ohtani = draft_df["norm"] == "shoheiohtani"
    draft_df.loc[ohtani &  draft_df["position"].isin(_pitcher_pos), "norm"] = "shoheiohtanipitcher"
    draft_df.loc[ohtani & ~draft_df["position"].isin(_pitcher_pos), "norm"] = "shoheiohtanihitter"

    # Use all players — PTS is correct for everyone even when G is not
    stats = player_stats.copy()
    stats["PTS"] = pd.to_numeric(stats["PTS"], errors="coerce").fillna(0.0)

    # Join draft picks to actual stats on normalized name
    merged = draft_df.merge(stats[["norm", "PTS"]], on="norm", how="left")
    merged["PTS"] = merged["PTS"].fillna(0.0)

    import numpy as np

    rng = np.random.default_rng(42)   # fixed seed → jitter is stable between runs

    # ── Compute VORP: PTS above position-average among all drafted starters ──
    # Pitchers lumped together (SP + RP sample too small to split at 2 weeks)
    POS_GROUP = {
        "C": "C", "1B": "1B", "2B": "2B", "SS": "SS",
        "3B": "3B", "OF": "OF", "DH": "DH",
        "SP": "P", "RP": "P", "SP / RP": "P",
    }
    merged["pos_group"] = merged["position"].map(POS_GROUP).fillna("P")
    pos_avg   = merged.groupby("pos_group")["PTS"].mean().to_dict()
    pos_count = merged.groupby("pos_group")["PTS"].count().to_dict()
    merged["repl"] = merged["pos_group"].map(pos_avg)
    merged["vorp"] = merged["PTS"] - merged["repl"]

    qualified  = merged   # all 98 picks now have a VORP value
    n_matched  = merged["PTS"].gt(0).sum()

    price_max = int(merged["price"].max())

    fig = go.Figure()

    # ── Zero line (position average = replacement level) ─────────────────────
    fig.add_shape(
        type="line",
        x0=0.9, x1=price_max + 10,
        y0=0, y1=0,
        line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=np.log10(price_max) * 0.55,
        y=0,
        xref="x", yref="y",
        text="position average (replacement level)",
        showarrow=False,
        font=dict(color="rgba(255,255,255,0.45)", size=9),
        yshift=8,
    )

    # ── Shaded "above replacement" region ────────────────────────────────────
    y_max = merged["vorp"].max() * 1.15
    fig.add_shape(
        type="rect",
        x0=0.9, x1=price_max + 10,
        y0=0, y1=y_max,
        fillcolor="rgba(39,174,96,0.06)",
        line=dict(width=0),
        layer="below",
    )

    # ── One scatter series per team ───────────────────────────────────────────
    for team in TEAMS:
        sub    = merged[merged["team"] == team].copy()
        is_jon = team == "Jon's Generals"
        if sub.empty:
            continue

        hover = [
            (
                f"<b>{r['player']}</b>  ({r['position']})<br>"
                f"{team}<br>"
                f"Paid: <b>${r['price']}</b><br>"
                f"PTS: {r['PTS']:.0f}<br>"
                f"Position avg: {r['repl']:.1f} PTS<br>"
                f"VORP: <b>{r['vorp']:+.1f} PTS</b>"
            )
            for _, r in sub.iterrows()
        ]

        labels = sub["player"].apply(
            lambda n: n.split(",")[0].strip() if "," in n else n.split()[-1]
        )

        # Jitter both axes so stacked low-price / low-VORP players spread out
        log_x  = np.log10(sub["price"].clip(lower=0.9))
        x_vals = 10 ** (log_x + rng.uniform(-0.07, 0.07, len(sub)))
        y_vals = sub["vorp"] + rng.uniform(-1.5, 1.5, len(sub))

        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers+text",
            name=team,
            marker=dict(
                color=TEAM_COLORS[team],
                size=11 if is_jon else 9,
                line=dict(
                    color="white" if is_jon else "rgba(0,0,0,0)",
                    width=2 if is_jon else 0,
                ),
            ),
            text=labels,
            textposition="top center",
            textfont=dict(size=8, color=TEAM_COLORS[team]),
            hovertext=hover,
            hoverinfo="text",
        ))

    # ── Position replacement levels in legend area ────────────────────────────
    pos_note = "  ".join(
        f"{p}: {v:.1f} PTS avg (n={pos_count[p]})"
        for p, v in sorted(pos_avg.items())
    )

    snap_date = date.today().strftime("%B %d")

    fig.update_layout(
        title=dict(
            text=(
                "DTFBL 2026 — Draft Price vs VORP<br>"
                f"<sup>As of {snap_date} · VORP = season PTS above position avg among all drafted starters · "
                f"all {len(merged)} picks shown · 0 = replacement level</sup>"
            ),
            font=dict(size=22, color="white"),
            x=0.5, xanchor="center",
        ),
        template="plotly_dark",
        paper_bgcolor="#0d0d1a",
        plot_bgcolor="#0d0d1a",
        dragmode="pan",
        xaxis=dict(
            title="Draft Price ($)  —  log scale",
            type="log",
            showgrid=True, gridcolor="#1e1e3a",
            tickfont=dict(color="#9999bb"),
            tickvals=[1, 2, 5, 10, 20, 30, 50, 75, 100],
            ticktext=["$1", "$2", "$5", "$10", "$20", "$30", "$50", "$75", "$100"],
            range=[np.log10(0.9), np.log10(price_max + 15)],
        ),
        yaxis=dict(
            title="VORP (season PTS above position average)",
            showgrid=True, gridcolor="#1e1e3a",
            tickfont=dict(color="#9999bb"),
            zeroline=False,
        ),
        legend=dict(
            font=dict(color="white", size=10),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
        annotations=[
            # Position averages as a footer annotation
            go.layout.Annotation(
                text=f"Position averages:  {pos_note}",
                xref="paper", yref="paper",
                x=0.5, y=-0.08,
                showarrow=False,
                font=dict(color="#777799", size=9),
                xanchor="center",
            ),
        ],
        margin=dict(t=120, b=80, l=75, r=20),
        height=640,
    )

    VIZ_DIR.mkdir(exist_ok=True)
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"✓  value_chart.html  ({n_matched}/{len(merged)} picks with PTS>0, all {len(merged)} shown)")
    return fig


# ── Newsletter HTML ───────────────────────────────────────────────────────────

def generate_newsletter_html(
    standings: pd.DataFrame,
    draft: pd.DataFrame,
    player_stats: "pd.DataFrame | None",
    out: Path = VIZ_DIR / "index.html",
):
    """
    Combine all four charts + a standings table into a single dark-themed HTML
    page suitable for GitHub Pages.  Individual .html chart files are also
    written as a side-effect (they still work as standalone links).
    """
    # ── Build each figure (also writes individual files) ────────────────────
    fig_civ   = civ_chart(standings,   out=VIZ_DIR / "civ_chart.html")
    fig_gap   = gap_chart(standings,   out=VIZ_DIR / "gap_chart.html")
    fig_draft = draft_profile_chart(draft, standings, out=VIZ_DIR / "draft_profile.html")
    if player_stats is not None:
        fig_value = value_chart(draft, player_stats, out=VIZ_DIR / "value_chart.html")
    else:
        fig_value = None

    # ── Standings table ──────────────────────────────────────────────────────
    latest    = standings.iloc[-1]
    snap_date = latest["date"].strftime("%B %d, %Y")
    ranked    = sorted(TEAMS, key=lambda t: -float(latest.get(t, 0)))
    leader_pts = float(latest.get(ranked[0], 0))

    table_rows = ""
    for i, team in enumerate(ranked, 1):
        pts     = float(latest.get(team, 0))
        gap     = pts - leader_pts
        color   = TEAM_COLORS[team]
        is_jon  = team == "Jon's Generals"
        bold    = "font-weight:700;" if is_jon else ""
        gap_str = f"+{gap:.1f}" if gap >= 0 else f"{gap:.1f}"
        gap_color = "#2ecc71" if gap >= 0 else "#e74c3c"
        marker  = "  ←" if is_jon else ""
        table_rows += (
            f'<tr>'
            f'<td style="color:#666">{i}</td>'
            f'<td style="color:{color};{bold}">{team}{marker}</td>'
            f'<td style="color:#ddd">{pts:+.1f}</td>'
            f'<td style="color:{gap_color}">{gap_str}</td>'
            f'</tr>\n'
        )

    # ── Convert figures to embedded divs ─────────────────────────────────────
    def to_div(fig: "go.Figure") -> str:
        return fig.to_html(full_html=False, include_plotlyjs=False)

    civ_div   = to_div(fig_civ)
    gap_div   = to_div(fig_gap)
    draft_div = to_div(fig_draft)
    value_div = (
        to_div(fig_value)
        if fig_value is not None
        else (
            "<p style='color:#555;text-align:center;padding:40px'>"
            "Value chart unavailable — run <code>newsletter.py --fetch</code> to enable."
            "</p>"
        )
    )

    updated = date.today().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DTFBL 2026 — League Newsletter</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0d0d1a;
      color: #ddd;
      font-family: "Segoe UI", system-ui, Arial, sans-serif;
      line-height: 1.55;
    }}

    a {{ color: #7ecfff; }}

    /* ── Header ─────────────────────────── */
    header {{
      background: linear-gradient(135deg, #0d0d1a 0%, #111128 100%);
      border-bottom: 1px solid #1e1e3a;
      padding: 32px 24px 24px;
      text-align: center;
    }}
    header h1 {{
      font-size: clamp(1.8rem, 5vw, 2.8rem);
      font-weight: 900;
      letter-spacing: .04em;
      background: linear-gradient(90deg, #f1c40f 0%, #e67e22 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    header .subtitle {{
      color: #7777aa;
      font-size: .9rem;
      margin-top: 4px;
      letter-spacing: .06em;
      text-transform: uppercase;
    }}

    /* ── Main layout ────────────────────── */
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 16px 64px;
    }}

    section + section {{ margin-top: 56px; }}

    section h2 {{
      font-size: 1.15rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: #9999cc;
      border-bottom: 1px solid #1e1e3a;
      padding-bottom: 8px;
      margin-bottom: 20px;
    }}

    /* ── Standings table ────────────────── */
    .standings-table {{
      width: 100%;
      max-width: 520px;
      border-collapse: collapse;
      font-size: .95rem;
    }}
    .standings-table th {{
      color: #666;
      font-weight: 600;
      text-transform: uppercase;
      font-size: .75rem;
      letter-spacing: .08em;
      padding: 6px 12px;
      border-bottom: 1px solid #1e1e3a;
      text-align: left;
    }}
    .standings-table td {{
      padding: 7px 12px;
      border-bottom: 1px solid #111128;
    }}
    .standings-table tr:last-child td {{ border-bottom: none; }}

    /* ── Chart containers ───────────────── */
    .chart-wrap {{
      background: #0d0d1a;
      border: 1px solid #1e1e3a;
      border-radius: 8px;
      overflow: hidden;
    }}

    /* ── Footer ─────────────────────────── */
    footer {{
      text-align: center;
      color: #444466;
      font-size: .8rem;
      padding: 24px;
      border-top: 1px solid #1e1e3a;
      margin-top: 56px;
    }}
    footer a {{ color: #555577; }}
  </style>
</head>
<body>

<header>
  <h1>DTFBL 2026</h1>
  <p class="subtitle">League Newsletter &middot; {snap_date}</p>
</header>

<main>

  <section>
    <h2>Current Standings</h2>
    <table class="standings-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Team</th>
          <th>Season Pts</th>
          <th>vs Leader</th>
        </tr>
      </thead>
      <tbody>
{table_rows}      </tbody>
    </table>
  </section>

  <section>
    <h2>Points Race — Civilization Style</h2>
    <div class="chart-wrap">
{civ_div}
    </div>
  </section>

  <section>
    <h2>Points Behind Leader</h2>
    <div class="chart-wrap">
{gap_div}
    </div>
  </section>

  <section>
    <h2>Draft Budget Allocation</h2>
    <div class="chart-wrap">
{draft_div}
    </div>
  </section>

  <section>
    <h2>Draft Price vs Production (VORP)</h2>
    <div class="chart-wrap">
{value_div}
    </div>
  </section>

</main>

<footer>
  Updated {updated} &mdash;
  <a href="https://github.com/Jon-zachary/dtfbl-draft-analysis">github.com/Jon-zachary/dtfbl-draft-analysis</a>
</footer>

</body>
</html>
"""

    VIZ_DIR.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✓  index.html (newsletter page)")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DTFBL newsletter charts")
    parser.add_argument(
        "--fetch", action="store_true",
        help="Log in to OnRoto and refresh all-team player stats cache",
    )
    parser.add_argument(
        "--newsletter", action="store_true", default=True,
        help="Generate combined newsletter index.html (default: on)",
    )
    parser.add_argument(
        "--no-newsletter", dest="newsletter", action="store_false",
        help="Skip combined newsletter index.html, only write individual charts",
    )
    args = parser.parse_args()

    print("Loading data...")
    standings = load_standings()
    print(
        f"  Standings: {len(standings)} snapshots, "
        f"{standings['date'].iloc[1].strftime('%b %d')} → "
        f"{standings['date'].iloc[-1].strftime('%b %d')}"
    )

    draft = parse_draft_2026()
    print(
        f"  Draft: {len(draft)} picks across {draft['team'].nunique()} teams"
        f" (${draft['price'].sum()} total spent)"
    )

    # Fetch or load player stats for the value chart
    if args.fetch:
        print("\nFetching player stats from OnRoto...")
        raw_stats = fetch_all_player_stats()
        player_stats = pd.DataFrame(raw_stats)
    else:
        player_stats = load_player_stats()
        if player_stats is None:
            print("  No player stats cache — run with --fetch to enable value chart")
        else:
            print(f"  Player stats: {len(player_stats)} players from cache")

    print("\nGenerating charts...")
    if args.newsletter:
        generate_newsletter_html(standings, draft, player_stats)
    else:
        civ_chart(standings)
        gap_chart(standings)
        draft_profile_chart(draft, standings)
        if player_stats is not None:
            value_chart(draft, player_stats)
        else:
            print("  (skipping value_chart.html — run with --fetch to generate)")

    print(f"\nAll charts saved to {VIZ_DIR}/")
    print("Open visualizations/index.html in your browser for the full newsletter.")
