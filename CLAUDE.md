# DTFBL Fantasy Baseball Draft Analysis

## Project Summary

Analysis tools for a 7-team NL-only fantasy baseball auction league (DTFBL) with 16 years of historical data (2009-2025). The owner is **Jon (Jon's Generals)**.

## Key Files

| File | Purpose |
|------|---------|
| `all_drafts_2009_2025.csv` | Raw historical draft data (1,354 picks) |
| `owner_profiles.json` | AI behavior profiles derived from historical tendencies |
| `player_values.py` | 2026 player valuations using VORP + historical price curves |
| `simulate_draft.py` | Full 7-team auction simulation (Jon as value hunter vs AI) |
| `grade_drafts.py` | Grade historical drafts by actual player outcomes (uses pybaseball) |
| `INFLATION_CHEAT_SHEET.md` | Calculator-friendly inflation tracking for live drafts |

## League Format

- **Teams:** 7
- **Budget:** $260 per team ($1,820 total)
- **Roster:** 14 players (C, 1B, 2B, SS, 3B, 3×OF, DH, 3×SP, 2×RP)
- **Scoring:** 1B(+1), 2B(+2), 3B(+4), HR(+4), R(+1), RBI(+1), SB(+1), BB(+1), W(+12), L(-3), SV(+8), K(+1), BB(-1), QS(+2)

## Core Concepts

### Value Hunting Strategy
The key finding: **don't chase stars**. Historical data shows:
- Top 5 picks average $72 but are only worth ~$38 (VORP)
- Mid-tier players (ranks 25-50) are often underpriced
- Value hunting wins 90% of simulated drafts vs AI owners

### Inflation Tracking
Formula for live draft: `($ Left) ÷ (Spots Left) ÷ 18.5 = Inflation Multiplier`

### Owner Tendencies (exploitable)
- **Jake's Snakes:** Overpays C (+72%), SS (+42%). Punts 2B (-52%), RP (-45%)
- **Forest Rangers:** Overpays 3B (+49%), SS (+37%). Punts SP (-52%), C (-31%). Has drafted Bryce Harper 9 times.
- **David's Devils:** Overpays RP (+72%), 1B (+48%). Punts SS (-53%), OF (-37%)

## Running the Tools

```bash
# See 2026 player values with expected prices
python player_values.py

# Simulate a full draft (Jon as value hunter)
python simulate_draft.py

# Grade historical drafts by actual outcomes (requires pybaseball)
python grade_drafts.py
```

## Draft Grading Results (2021-2024)

| Rank | Team | Cumulative Points | Efficiency |
|------|------|-------------------|------------|
| 1 | Forest Rangers | 19,065 | 18.3 pts/$ |
| 2 | Jon's Generals | 19,026 | 18.3 pts/$ |
| 3 | Ryan's Lions | 18,667 | 17.9 pts/$ |
| 4 | David's Devils | 18,266 | 17.6 pts/$ |
| 5 | Bert's Bombers | 18,188 | 17.5 pts/$ |
| 6 | Jake's Snakes | 17,698 | 17.0 pts/$ |
| 7 | Charlie's Stars | 16,885 | 16.2 pts/$ |

## Future Work

- Visual presentation of draft analysis for the league
- Extend draft grading to all years (2009-2025)
- Potentially integrate preseason projections if FanGraphs membership obtained
