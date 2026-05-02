# DTFBL 2026 — Downtown Fantasy Baseball League

Data analytics and live season tracking for a 7-team NL-only auction league with 16 years of historical data.

## Newsletter

The league newsletter updates automatically every day and is published at:

**[jon-zachary.github.io/dtfbl-draft-analysis](https://jon-zachary.github.io/dtfbl-draft-analysis/)**

It includes:

- **Current standings** with points and gap vs leader
- **Points race** — animated stacked area chart showing each team's share of total points over the season
- **Points behind leader** — animated line chart tracking the gap to first place over time
- **Draft budget allocation** — how each team spent their $260 by position, sorted by current standing
- **Draft price vs production** — scatter plot of what each player cost vs what they've returned (VORP)

## League Format

- 7 teams, $260 auction budget, 14-player rosters
- NL-only, rotisserie-style scoring
- Positions: C, 1B, 2B, SS, 3B, 3×OF, DH, 3×SP, 2×RP

## How It Works

Standings are scraped from OnRoto daily via GitHub Actions and committed back to the repo. The newsletter page rebuilds automatically with each update. Player stats refresh every Sunday.
