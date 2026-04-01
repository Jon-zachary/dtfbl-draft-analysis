#!/usr/bin/env python3
"""
Generate markdown cheat sheets for the 2026 DTFBL draft.

Outputs:
  cheat_sheets/all_players.md       - Full ranked board with both valuations
  cheat_sheets/C.md, 1B.md, ...    - Per-position sheets
"""

import os
from player_values import (
    calculate_all_players,
    calculate_dollar_values,
    REPLACEMENT_LEVELS,
)

OUTPUT_DIR = "cheat_sheets"

# Injury / news notes shown in the cheat sheets
NOTES = {
    # Injury flags
    "Zack Wheeler":       "⚠️  TOS surgery; return ~late May/June. Other teams pricing full season!",
    "Blake Snell":        "⚠️  Shoulder; starts on IL, return June+. Other teams pricing full season!",
    "Tyler Glasnow":      "⚠️  Shoulder history; only 90 IP in 2025",
    "Ronald Acuna Jr.":   "⚠️  Multi-knee + calf history; SBs cut from 73 to ~14",
    "Francisco Lindor":   "ℹ️  Hamate surgery Feb; spring debut 3/15, on track OD",
    "Corbin Carroll":     "ℹ️  Hamate injury; back in Cactus League, on track OD",
    "Spencer Strider":    "ℹ️  First healthy spring in 3 yrs; high upside",
    "Yoshinobu Yamamoto": "ℹ️  Healthy; named Opening Day starter",
    "Freddy Peralta":     "ℹ️  Traded to Mets; Opening Day starter",
    "Seiya Suzuki":       "⚠️  PCL sprain spring; IL candidate to open season",
    # Team/position notes
    "Luis Arraez":        "ℹ️  Signed with Giants (1-yr deal)",
    "Kyle Tucker":        "ℹ️  Signed with Dodgers as top FA",
    "Alex Bregman":       "ℹ️  Signed with CHC (was wrongly assumed AL)",
    "Rafael Devers":      "ℹ️  Signed with SF as 1B (not 3B!) — thins 1B pool",
    "Bo Bichette":        "ℹ️  Signed with NYM (was wrongly assumed AL)",
    "Brandon Lowe":       "ℹ️  Signed with PIT (was wrongly assumed AL)",
    "Mookie Betts":       "ℹ️  Playing SS full-time in 2026 — SS price, elite production",
    "Spencer Steer":      "ℹ️  Playing 1B in 2026 — moved from 3B",
    "Jhoan Duran":        "ℹ️  Signed with PHI from Twins (AL) — elite new NL closer",
    "Mason Miller":       "ℹ️  Signed with SD from A's (AL) — elite K closer",
    "Pete Fairbanks":     "ℹ️  Signed with MIA from Rays (AL)",
    "Edwin Diaz":         "ℹ️  Now with LAD (not Mets)",
    "James Wood":         "ℹ️  WSH young star; 508 pts projected by league mgr",
    "Hunter Goodman":     "ℹ️  COL catcher — Coors inflated stats",
}

POSITION_ORDER = ["C", "1B", "2B", "SS", "3B", "OF", "DH", "SP", "RP"]

POSITION_SLOTS = {
    "C": 7, "1B": 7, "2B": 7, "SS": 7, "3B": 7,
    "OF": 21, "DH": 7, "SP": 21, "RP": 14,
}

OWNER_NOTES = {
    "C":  "Jake overpays C (+72%). Forest punts C (-31%).",
    "SS": "Jake overpays SS (+42%). Forest overpays SS (+37%). David punts SS (-53%).",
    "3B": "Forest overpays 3B (+49%). (Bregman/Devers gone — NL-only pool thinner this yr.)",
    "RP": "David overpays RP (+72%). Jake punts RP (-45%).",
    "1B": "David overpays 1B (+48%).",
    "OF": "David punts OF (-37%).",
    "SP": "Forest punts SP (-52%).",
}


def signal(delta):
    if delta >= 10:
        return "🟢 BUY"
    if delta <= -15:
        return "🔴 AVOID"
    return ""


def make_row(p):
    note = NOTES.get(p["name"], "")
    delta_str = f"+{p['delta']}" if p["delta"] > 0 else str(p["delta"])
    sig = signal(p["delta"])
    return (
        f"| {p['rank']:<4} | {p['name']:<24} | {p['position']:<3} "
        f"| {p['points']:<4} | {p['vorp']:<4} "
        f"| ${p['vorp_value']:<4} | ${p['expected_price']:<4} | {delta_str:<6} "
        f"| {sig:<9} | {note} |"
    )


def write_all_players(players):
    path = os.path.join(OUTPUT_DIR, "all_players.md")
    lines = []

    lines.append("# 2026 DTFBL Draft Cheat Sheet — All Players")
    lines.append("")
    lines.append("*Updated March 20, 2026 · Spring training news + injuries applied*")
    lines.append("")
    lines.append("## Legend")
    lines.append("- **Value** = What the player is theoretically worth (VORP-based)")
    lines.append("- **Exp$**  = What they'll actually cost (16 yrs of DTFBL history)")
    lines.append("- **Delta** = Value − Exp$ (positive = bargain, negative = overpay)")
    lines.append("- 🟢 **BUY** = Expected price is ≥$10 below value → target aggressively")
    lines.append("- 🔴 **AVOID** = Expected price is ≥$15 above value → let someone else pay")
    lines.append("")
    lines.append("## Key Injury Flags")
    for name, note in NOTES.items():
        lines.append(f"- **{name}**: {note}")
    lines.append("")

    header = (
        "| Rank | Player                   | Pos "
        "| Pts  | VORP | Value  | Exp$   | Delta  "
        "| Signal    | Notes |"
    )
    sep = (
        "|------|--------------------------|-----"
        "|------|------|--------|--------|--------"
        "|-----------|-------|"
    )

    lines.append("## Full Board (ranked by VORP value)")
    lines.append("")
    lines.append(header)
    lines.append(sep)

    for p in players:
        lines.append(make_row(p))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Top Bargains (best delta)")
    lines.append("")
    draftable = [p for p in players if p["rank"] <= 98]
    bargains = sorted(draftable, key=lambda x: x["delta"], reverse=True)[:12]
    lines.append(header)
    lines.append(sep)
    for p in bargains:
        lines.append(make_row(p))

    lines.append("")
    lines.append("## Worst Overpays (worst delta)")
    lines.append("")
    overpays = sorted(draftable, key=lambda x: x["delta"])[:10]
    lines.append(header)
    lines.append(sep)
    for p in overpays:
        lines.append(make_row(p))

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Wrote {path}")


def write_position_sheet(pos, players):
    pos_players = [p for p in players if p["position"] == pos]
    pos_players.sort(key=lambda x: x["vorp"], reverse=True)

    path = os.path.join(OUTPUT_DIR, f"{pos}.md")
    lines = []

    pos_label = {
        "C": "Catchers", "1B": "First Basemen", "2B": "Second Basemen",
        "SS": "Shortstops", "3B": "Third Basemen", "OF": "Outfielders",
        "DH": "Designated Hitters", "SP": "Starting Pitchers",
        "RP": "Relief Pitchers",
    }.get(pos, pos)

    lines.append(f"# 2026 DTFBL — {pos_label} ({pos})")
    lines.append("")
    lines.append("*Updated March 20, 2026*")
    lines.append("")

    rep = REPLACEMENT_LEVELS.get(pos, "N/A")
    slots = POSITION_SLOTS.get(pos, "?")
    lines.append(f"**Replacement level:** {rep} pts  |  **Roster spots in league:** {slots} ({slots // 7} per team)")
    lines.append("")

    if pos in OWNER_NOTES:
        lines.append(f"> **Owner tendency:** {OWNER_NOTES[pos]}")
        lines.append("")

    header = (
        "| Rank | Player                   | Pos "
        "| Pts  | VORP | Value  | Exp$   | Delta  "
        "| Signal    | Notes |"
    )
    sep = "|------|--------------------------|-----|------|------|--------|--------|--------|-----------|-------|"

    lines.append(header)
    lines.append(sep)

    for p in pos_players:
        lines.append(make_row(p))

    lines.append("")

    # Price tiers
    tiers = []
    for p in pos_players:
        exp = p["expected_price"]
        if exp >= 30:
            tier = "Elite ($30+)"
        elif exp >= 15:
            tier = "Mid ($15-29)"
        elif exp >= 5:
            tier = "Bargain ($5-14)"
        else:
            tier = "Filler ($1-4)"
        tiers.append((tier, p))

    from collections import defaultdict
    tier_groups = defaultdict(list)
    for tier, p in tiers:
        tier_groups[tier].append(p)

    tier_order = ["Elite ($30+)", "Mid ($15-29)", "Bargain ($5-14)", "Filler ($1-4)"]
    lines.append("## Price Tiers")
    lines.append("")
    for tier in tier_order:
        if tier in tier_groups:
            names = ", ".join(p["name"] for p in tier_groups[tier])
            lines.append(f"**{tier}:** {names}")
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Wrote {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    players = calculate_all_players()
    players, multiplier = calculate_dollar_values(players)

    print(f"Calculated {len(players)} players ($/VORP multiplier: {multiplier:.4f})")
    print()

    write_all_players(players)
    for pos in POSITION_ORDER:
        write_position_sheet(pos, players)

    print()
    print(f"All cheat sheets written to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
