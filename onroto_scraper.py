#!/usr/bin/env python3
"""
DTFBL OnRoto Daily Scraper
--------------------------
Logs in to OnRoto once a day, pulls standings and Jon's roster,
logs everything to CSV, and emails alerts for injuries or
significantly underperforming players.

Run nightly via Windows Task Scheduler (see README for setup).
"""

import os
import csv
import re
import sys
import smtplib
import logging
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import argparse
import json

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Pull ATC projections from player_values.py in the same directory
sys.path.insert(0, str(Path(__file__).parent))
from player_values import (
    HITTER_PROJECTIONS, PITCHER_PROJECTIONS,
    calc_hitter_points, calc_pitcher_points,
    REPLACEMENT_LEVELS,
)

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

LEAGUE_ID   = "dtfbl1989"
JON_TEAM_ID = "6"
BASE_URL    = "https://onroto.fangraphs.com/baseball/webnew"

TEAMS = {
    "Forest Rangers":  "0",
    "Bert's Bombers":  "1",
    "Charlie's Stars": "2",
    "Ryan's Lions":    "3",
    "David's Devils":  "4",
    "Jake's Snakes":   "5",
    "Jon's Generals":  "6",
}

DATA_DIR          = Path(__file__).parent / "data"
DEBUG_DIR         = DATA_DIR / "debug"
STANDINGS_LOG     = DATA_DIR / "standings_log.csv"
ROSTER_LOG        = DATA_DIR / "roster_log.csv"
ALERTS_LOG        = DATA_DIR / "alerts_log.csv"
SCRAPER_LOG       = DATA_DIR / "scraper.log"

# ATC projection points per player (for underperformance check)
# Values from player_values.py — points expected over a full 162-game season
ATC_PROJECTIONS = {
    "wcontreras":   454,
    "ssteer":       432,
    "oalbies":      471,
    "tturner":      486,
    "abregman":     453,
    "jwood":        500,
    "thernandez":   474,
    "jchourio":     442,
    "mozuna":       506,
    "csale":        290,
    "sstrider":     264,
    "yyamamoto":    280,
    "dsantana":     130,
    "dwilliams":    357,
}

INJURY_KEYWORDS = [
    "injured list", " il ", "10-day", "15-day", "60-day",
    "fracture", "strain", "sprain", "surgery", "disabled",
    "placed on", "transferred to",
]

# How far below pace triggers an alert (fraction of projected pts)
UNDERPERFORM_THRESHOLD = 0.70   # below 70% of expected pace = alert

# ── Logging ───────────────────────────────────────────────────────────────────

DATA_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(SCRAPER_LOG),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Debug helpers ─────────────────────────────────────────────────────────────

def dump_html(name: str, html: str):
    """Save raw HTML to data/debug/<name>.html for inspection."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    log.info("  [debug] HTML saved → %s", path)


def dump_tables(name: str, html: str):
    """
    Print every <table> found in a page with:
      - its index
      - all <th> header text
      - first 3 data rows (raw cell text)
    Helps figure out which table index holds which data.
    """
    soup   = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"\n{'='*70}")
    print(f"PAGE: {name}  —  {len(tables)} table(s) found")
    print(f"{'='*70}")
    for i, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows    = table.find_all("tr")
        print(f"\n  [table {i}]  headers={headers}")
        # Print up to 4 data rows so we can see values
        for tr in rows[1:5]:
            cells = [td.get_text(separator="|", strip=True) for td in tr.find_all("td")]
            if cells:
                print(f"    row: {cells}")
    print()


# ── Session / Auth ────────────────────────────────────────────────────────────

def extract_session_id(html: str) -> str | None:
    """Pull the session_id out of any link in the page HTML."""
    match = re.search(r"session_id=([A-Za-z0-9]+)", html)
    return match.group(1) if match else None


def login() -> tuple[requests.Session, str]:
    """
    Log in to OnRoto, return (session, session_id).
    OnRoto rotates the session_id with every response — we track it
    by extracting it from links in each page we fetch.
    """
    username = os.getenv("ONROTO_USERNAME")
    password = os.getenv("ONROTO_PASSWORD")
    if not username or not password:
        raise ValueError("Set ONROTO_USERNAME and ONROTO_PASSWORD in your .env file")

    session = requests.Session()
    # Full browser headers — some sites 403 on minimal user-agents
    session.headers.update({
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/123.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # Login page is at the root index, not under /baseball/webnew/
    login_url = "https://onroto.fangraphs.com/index.pl"
    resp = session.get(login_url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Could not find login form — page may have changed")

    action = form.get("action", "")
    if not action:
        action = "/index.pl"   # form likely posts back to root index
    if not action.startswith("http"):
        action = "https://onroto.fangraphs.com" + action

    # Collect any hidden fields the form might have
    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        val  = inp.get("value", "")
        if name:
            payload[name] = val

    # Detect credential field names from the form
    email_field = next(
        (inp.get("name") for inp in form.find_all("input")
         if inp.get("type") in ("text", "email")
         or any(kw in (inp.get("name") or "").lower() for kw in ("mail", "user", "login", "id"))),
        "email",
    )
    pass_field = next(
        (inp.get("name") for inp in form.find_all("input")
         if inp.get("type") == "password"),
        "password",
    )
    payload[email_field] = username
    payload[pass_field]  = password

    log.debug("POSTing login to %s with fields: %s", action, list(payload.keys()))
    session.headers["Referer"] = resp.url
    resp = session.post(action, data=payload, timeout=30, allow_redirects=True)
    resp.raise_for_status()

    session_id = extract_session_id(resp.text)
    if not session_id:
        # Check if we were redirected back to login (wrong password)
        if "password" in resp.text.lower() and "sign" in resp.text.lower():
            raise RuntimeError("Login failed — check ONROTO_USERNAME and ONROTO_PASSWORD")
        raise RuntimeError(
            "Logged in but could not find session_id in response. "
            "The site structure may have changed."
        )

    log.info("Logged in successfully. session_id=%s…", session_id[:8])
    return session, session_id


# ── Fetching ──────────────────────────────────────────────────────────────────

def fetch(session: requests.Session, path: str, session_id: str,
          extra: str = "") -> tuple[str, str]:
    """
    Fetch a page, return (html, new_session_id).
    OnRoto rotates session_id on every response so we always
    extract a fresh one to use on the next request.
    `extra` is appended to the query string before the session_id
    (e.g. "+SORT_6" for the team stats page).
    """
    url = f"{BASE_URL}/{path}?{LEAGUE_ID}+{JON_TEAM_ID}{extra}&session_id={session_id}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    new_sid = extract_session_id(resp.text) or session_id
    return resp.text, new_sid


def fetch_team_stats(session: requests.Session, session_id: str) -> tuple[str, str]:
    """Fetch the detailed team stats page which marks IL players with an asterisk."""
    return fetch(session, "display_team_stats.pl", session_id, extra="+SORT_6")


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_player_table(soup: BeautifulSoup, table_index: int) -> list[dict]:
    """
    Parse hitter or pitcher stats table.
    Returns list of player dicts, skipping the Totals row.

    Each stat cell contains two stacked values (YTD and current-period) separated
    by a line break in the HTML.  We take only the first (YTD) value.
    """
    tables = soup.find_all("table")
    if len(tables) <= table_index:
        return []

    table = tables[table_index]
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    # Fix colspan issue: '2026 Games by Position' is a row-1 spanning header
    # for 7 position columns whose sub-headers (DH,C,1B,2B,3B,SS,OF) appear
    # at the *end* of find_all("th") because they live in a second header row.
    # This causes a 6-column shift in all stats after 'Sta'.
    # Solution: remove the spanning header and the trailing sub-headers,
    # and insert the sub-headers (prefixed) at the correct position.
    if "2026 Games by Position" in headers:
        span_idx = headers.index("2026 Games by Position")
        pos_sub  = [f"_g_{h}" for h in headers[-7:]]   # _g_DH, _g_C, etc.
        headers  = headers[:span_idx] + pos_sub + headers[span_idx + 1 : -7]

    players = []

    for tr in table.find_all("tr")[1:]:          # skip header row
        # separator="\n" preserves the YTD|period boundary; we take [0] (YTD)
        cells = [
            td.get_text(separator="\n", strip=True).split("\n")[0].strip()
            for td in tr.find_all("td")
        ]
        if not cells:
            continue
        first = cells[0].lower().rstrip(":")
        if first in ("totals", "total", "") or first.startswith("stats of previously"):
            continue
        row = dict(zip(headers, cells))
        # Clean status codes like (a0)/(b0) and IL markers from Name
        if "Name" in row:
            row["Name"] = re.sub(r'\([ab]\d+\)', '', row["Name"]).replace("*", "").strip()
        # Build lookup key from Name (not Pos which is cells[0])
        name_val = row.get("Name", cells[0])
        row["_key"] = name_val.lower().replace(" ", "").replace(".", "").replace(",", "")
        players.append(row)

    return players


def parse_team_page(html: str) -> dict:
    """
    Parse the display_team_stats page.
    Returns dict with 'hitters', 'pitchers', 'total_pts'.

    The page has four player tables:
      active hitters   → first table with AB + PTS headers
      reserved hitters → second table with AB + PTS headers  (skip — all zeros)
      active pitchers  → first table with IP + PTS headers
      reserved pitchers→ second table with IP + PTS headers  (skip — all zeros)
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    hitters  = []
    pitchers = []

    # Take only the FIRST matching table for each type (active roster)
    for i, table in enumerate(tables):
        headers = [th.get_text(strip=True).upper() for th in table.find_all("th")]
        if "AB" in headers and "PTS" in headers and not hitters:
            hitters = parse_player_table(soup, i)
        elif "IP" in headers and "PTS" in headers and not pitchers:
            pitchers = parse_player_table(soup, i)

    # Total points: sum PTS column from both tables
    def sum_pts(players):
        total = 0.0
        for p in players:
            try:
                total += float(p.get("PTS", 0) or 0)
            except ValueError:
                pass
        return total

    total_pts = sum_pts(hitters) + sum_pts(pitchers)

    return {
        "hitters":   hitters,
        "pitchers":  pitchers,
        "total_pts": total_pts,
    }


def parse_injured_players(html: str) -> list[str]:
    """
    Parse the display_team_stats page.
    Any player with an asterisk (*) in their name cell is on the IL.
    Returns a deduplicated list of strings like "Spencer Strider (Atl SP)".

    Only processes tables with ≤ 30 headers to avoid the mega outer wrapper.
    """
    soup    = BeautifulSoup(html, "html.parser")
    injured = []
    seen    = set()

    for table in soup.find_all("table"):
        raw_headers = [th.get_text(strip=True) for th in table.find_all("th")]
        # Skip mega/merged wrapper tables
        if len(raw_headers) > 30:
            continue
        if "Name" not in raw_headers:
            continue

        name_col = raw_headers.index("Name")
        tm_col   = raw_headers.index("Tm")  if "Tm"  in raw_headers else None
        pos_col  = raw_headers.index("Pos") if "Pos" in raw_headers else None

        sta_col = raw_headers.index("Sta") if "Sta" in raw_headers else None

        for tr in table.find_all("tr")[1:]:
            # Use "\n" separator so dual-value cells split cleanly; take first value
            cells = [
                td.get_text(separator="\n", strip=True).split("\n")[0].strip()
                for td in tr.find_all("td")
            ]
            if len(cells) <= name_col:
                continue
            # Skip reserved/disabled players (Sta="dis") — user already knows
            # about them. Only alert for active players who just hit the IL.
            if sta_col is not None and len(cells) > sta_col and cells[sta_col] == "dis":
                continue
            raw_name = cells[name_col]
            if "*" not in raw_name:
                continue
            # Strip asterisks and status codes like (a0)/(b0)
            clean = re.sub(r'\([ab]\d+\)', '', raw_name).replace("*", "").strip()
            tm    = cells[tm_col]  if tm_col  is not None and len(cells) > tm_col  else "?"
            pos   = cells[pos_col] if pos_col is not None and len(cells) > pos_col else "?"
            entry = f"{clean} ({tm} {pos})"
            if entry not in seen:
                seen.add(entry)
                injured.append(entry)

    return injured


def parse_standings(html: str) -> dict:
    """
    Parse the display_stand.pl page.
    Returns {
        "season": {team_name: {"hit": x, "pit": x, "total": x}},
        "week":   {team_name: {"hit": x, "pit": x, "total": x}},
    }

    The page has two clean standings tables:
      table with "Team Name" header → season totals
      table with "Team" header      → current week
    Both are distinguished from the mega wrapper table by having ≤ 6 headers.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = {"season": {}, "week": {}}
    keys = ["season", "week"]
    found = 0

    for table in soup.find_all("table"):
        raw_headers = [th.get_text(strip=True) for th in table.find_all("th")]
        # Skip mega/merged wrapper tables — clean standings tables have ≤ 6 headers
        if len(raw_headers) > 6:
            continue
        headers = [h.upper() for h in raw_headers]
        if "TOTAL" not in headers or "HIT" not in headers:
            continue

        hit_col   = headers.index("HIT")
        pit_col   = headers.index("PIT")
        total_col = headers.index("TOTAL")
        label     = keys[found] if found < len(keys) else "week"
        found    += 1

        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) <= total_col:
                continue
            team_name = cells[0].strip()
            if not team_name or team_name.lower() in ("team", "team name", ""):
                continue
            try:
                results[label][team_name] = {
                    "hit":   float(cells[hit_col]),
                    "pit":   float(cells[pit_col]),
                    "total": float(cells[total_col]),
                }
            except (ValueError, IndexError):
                pass

    return results


# ── Underperformance check ────────────────────────────────────────────────────

def check_underperformance(players: list[dict], games_played: int) -> list[str]:
    """
    Compare each player's current PTS to their ATC-projected pace.
    Returns list of alert strings for anyone significantly below pace.
    """
    if games_played <= 5:
        return []   # Too early in season for meaningful pace data

    season_fraction = games_played / 162.0
    alerts = []

    for p in players:
        key = p.get("_key", "")
        if key not in ATC_PROJECTIONS:
            continue
        projected_season = ATC_PROJECTIONS[key]
        expected_by_now  = projected_season * season_fraction
        try:
            actual = float(p.get("PTS", 0) or 0)
        except ValueError:
            continue

        if expected_by_now > 10 and actual < expected_by_now * UNDERPERFORM_THRESHOLD:
            pct = int(actual / expected_by_now * 100)
            alerts.append(
                f"  ⚠️  {p.get('Name', key)} ({p.get('Tm','?')}/{p.get('Pos','?')}): "
                f"{actual:.1f} pts actual vs {expected_by_now:.1f} expected ({pct}% of pace)"
            )

    return alerts


# ── Logging to CSV ────────────────────────────────────────────────────────────

def append_standings_log(standings: dict):
    """
    Write one row per day to standings_log.csv.
    Logs season total points for every team from the live standings page.
    """
    today      = date.today().isoformat()
    team_order = list(TEAMS.keys())
    season     = standings.get("season", {})

    write_header = not STANDINGS_LOG.exists()
    with open(STANDINGS_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date"] + team_order)
        row = [today]
        for team in team_order:
            pts = season.get(team, {}).get("total", "")
            row.append(pts)
        writer.writerow(row)
    log.info("Standings logged for %s", today)


def append_roster_log(players: list[dict], label: str):
    """Write Jon's current roster stats to roster_log.csv."""
    today = date.today().isoformat()
    if not players:
        return
    write_header = not ROSTER_LOG.exists()
    with open(ROSTER_LOG, "a", newline="") as f:
        fieldnames = ["date", "type"] + [k for k in players[0] if not k.startswith("_")]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for p in players:
            row = {"date": today, "type": label}
            row.update({k: v for k, v in p.items() if not k.startswith("_")})
            writer.writerow(row)


def append_alerts_log(alerts: list[str]):
    """Record any fired alerts to alerts_log.csv."""
    if not alerts:
        return
    today = date.today().isoformat()
    write_header = not ALERTS_LOG.exists()
    with open(ALERTS_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date", "alert"])
        for a in alerts:
            writer.writerow([today, a.strip()])


# ── Email ─────────────────────────────────────────────────────────────────────

def already_alerted_today() -> bool:
    """Return True if we already sent an alert email today."""
    if not ALERTS_LOG.exists():
        return False
    today = date.today().isoformat()
    with open(ALERTS_LOG) as f:
        for row in csv.reader(f):
            if row and row[0] == today:
                return True
    return False


def send_alert_email(subject: str, body: str):
    """Send an alert email via Gmail (requires App Password in .env)."""
    from_addr  = os.getenv("ALERT_FROM_EMAIL")
    app_pw     = os.getenv("ALERT_APP_PASSWORD")
    to_addr    = os.getenv("ALERT_TO_EMAIL")

    if not all([from_addr, app_pw, to_addr]):
        log.warning("Email not configured — alert printed to log only:\n%s", body)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_pw)
            server.sendmail(from_addr, to_addr, msg.as_string())
        log.info("Alert email sent to %s", to_addr)
    except Exception as e:
        log.error("Failed to send email: %s", e)


# ── Free agent recommendations ────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """
    Convert any name format to a lowercase key for matching.
    Handles both OnRoto style ("Last, First") and ATC style ("First Last").
    """
    name = name.replace("*", "").strip()
    if "," in name:
        last, first = name.split(",", 1)
        name = f"{first.strip()} {last.strip()}"
    return re.sub(r"[.\-']", "", name).lower().strip()


CHEAT_SHEET_DIR = Path(__file__).parent / "cheat_sheets"

# Maps cheat sheet file name → league position abbreviation
_CS_FILES = {
    "C.md": "C", "1B.md": "1B", "2B.md": "2B", "3B.md": "3B",
    "SS.md": "SS", "OF.md": "OF", "DH.md": "DH",
    "SP.md": "SP", "RP.md": "RP",
}


def build_cheat_sheet_eligibility() -> dict[str, set]:
    """
    Parse the cheat sheet markdown files to build a position eligibility lookup.
    Returns {normalized_name: {pos1, pos2, ...}} using the league's own
    'most projected ABs' position assignments.

    Table rows look like:
      | 46   | Rafael Devers  | 1B  | 560  | ...
    """
    eligibility: dict[str, set] = {}

    for filename, pos in _CS_FILES.items():
        path = CHEAT_SHEET_DIR / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            # Only data rows: start with '|' and have at least 4 pipe-separated fields
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            # parts[0] is empty (before first |), parts[1]=rank, parts[2]=player, parts[3]=pos
            if len(parts) < 4:
                continue
            rank_field = parts[1]
            # Skip header/separator rows
            if not rank_field.isdigit():
                continue
            player_name = parts[2].strip()
            if not player_name:
                continue
            key = normalize_name(player_name)
            eligibility.setdefault(key, set()).add(pos)

    return eligibility


def build_atc_lookup() -> dict:
    """
    Build a {normalized_name: {atc_pts, pos}} dict from all ATC projections
    in player_values.py, so we can cross-reference free agents.
    """
    lookup = {}
    for row in HITTER_PROJECTIONS:
        name, pos = row[0], row[1]
        pts = calc_hitter_points(*row[2:])
        lookup[normalize_name(name)] = {"name": name, "pos": pos, "atc_pts": round(pts)}
    for row in PITCHER_PROJECTIONS:
        name, pos = row[0], row[1]
        pts = calc_pitcher_points(*row[2:])
        lookup[normalize_name(name)] = {"name": name, "pos": pos, "atc_pts": round(pts)}
    return lookup


def fetch_roster(session: requests.Session, session_id: str) -> tuple[str, str]:
    """
    Fetch the all-teams roster page — shows every player on every roster.
    Anyone not listed here is available to pick up.
    URL: display_roster.pl?dtfbl1989+6+all+today
    """
    return fetch(session, "display_roster.pl", session_id, extra="+all+today")


def parse_all_rosters(html: str) -> set[str]:
    """
    Parse display_roster.pl (all 7 teams).
    Returns a set of normalized player names for everyone currently on a roster.
    Anyone NOT in this set is a free agent.

    The page has per-team Active and Reserved player tables (headers contain
    'Active Players' or 'Reserved Players').  Player name is in column 1
    (column 0 is position).  We skip the mega wrapper table and nav tables.
    """
    soup    = BeautifulSoup(html, "html.parser")
    drafted = set()

    for table in soup.find_all("table"):
        raw_headers = [th.get_text(strip=True) for th in table.find_all("th")]
        # Only process actual per-team roster tables
        if not any(h in ("Active Players", "Reserved Players") for h in raw_headers):
            continue
        # Skip mega/merged wrapper (has 15+ headers)
        if len(raw_headers) > 15:
            continue

        for tr in table.find_all("tr")[1:]:
            # Use "\n" separator so status codes in their own text node split cleanly
            cells = [
                td.get_text(separator="\n", strip=True).split("\n")[0].strip()
                for td in tr.find_all("td")
            ]
            if len(cells) < 2:
                continue
            raw_name = cells[1]   # col 0 = Pos, col 1 = player name
            # Strip IL markers (* / **) and status codes like (a0)/(b0)
            name = re.sub(r'\([ab]\d+\)', '', raw_name).replace("*", "").strip()
            if name and len(name) > 3 and name.lower() not in ("active players", "reserved players", "name"):
                drafted.add(normalize_name(name))

    return drafted


def atc_to_available(all_drafted: set[str], atc: dict) -> tuple[list[dict], list[dict]]:
    """
    Cross-reference ATC projections against the set of drafted players.
    Returns (available_hitters, available_pitchers) in the same dict format
    expected by recommend_replacements.
    """
    HITTER_POS  = {"C", "1B", "2B", "SS", "3B", "OF", "DH", "MI", "CI"}
    PITCHER_POS = {"SP", "RP"}

    hitters  = []
    pitchers = []

    for norm_name, info in atc.items():
        if norm_name in all_drafted:
            continue
        pos   = info["pos"]
        entry = {
            "name":     info["name"],
            "team":     "?",
            "elig_pos": pos,
            "site_pts": 0.0,
            "on_dl":    False,
        }
        if pos in HITTER_POS:
            hitters.append(entry)
        elif pos in PITCHER_POS:
            pitchers.append(entry)

    return hitters, pitchers


def fetch_free_agents(session: requests.Session, session_id: str,
                      player_type: str) -> tuple[str, str]:
    """
    Fetch the free agent hitters or pitchers page (kept as fallback).
    player_type: "hitters" or "pitchers"
    """
    url = (f"{BASE_URL}/display_new_multi_stats.pl"
           f"?{LEAGUE_ID}+{JON_TEAM_ID}+freeagent+{player_type}"
           f"&session_id={session_id}")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    new_sid = extract_session_id(resp.text) or session_id
    return resp.text, new_sid


def first_val(text: str) -> str:
    """
    Each cell on the free agent page contains two stacked values
    (year-to-date in black, date-range in red), separated by newlines.
    Return only the first (YTD) value.
    """
    return text.split("\n")[0].split()[0] if text.strip() else ""


def parse_free_agents(html: str, player_type: str) -> list[dict]:
    """
    Parse the free agent hitters or pitchers page.
    Each stat cell contains two values (YTD / date-range) — we take YTD.
    Players marked (DL) in their name are already injured; we skip them.
    Returns list of {name, team, elig_pos, site_pts, on_dl}.
    """
    soup    = BeautifulSoup(html, "html.parser")
    players = []

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "Name" not in headers or "PTS" not in headers:
            continue

        name_col = headers.index("Name")
        pts_col  = headers.index("PTS")
        team_col = headers.index("Team")     if "Team"     in headers else None
        pos_col  = headers.index("Elig Pos") if "Elig Pos" in headers else None

        for tr in table.find_all("tr")[1:]:
            # Get raw text per cell, preserving newlines for dual-value splitting
            cells = [td.get_text(separator="\n", strip=True) for td in tr.find_all("td")]
            if len(cells) <= pts_col:
                continue

            raw_name = cells[name_col]
            if not raw_name or raw_name.lower() == "name":
                continue

            # Detect and strip DL marker — skip DL players as pickup candidates
            on_dl = "(dl)" in raw_name.lower() or "(DL)" in raw_name
            clean_name = (raw_name
                          .replace("(DL)", "").replace("(dl)", "")
                          .replace("*", "")
                          .replace("More", "")   # OnRoto appends "More" link text
                          .strip())
            # Strip return-date annotations like "(04.01)" that appear on a
            # second line (e.g. "Misiorowski, Jacob\n(04.01)")
            clean_name = clean_name.split("\n")[0].strip()

            # Take only the YTD value from each dual-value cell
            try:
                pts = float(first_val(cells[pts_col]))
            except (ValueError, IndexError):
                pts = 0.0

            team     = first_val(cells[team_col]) if team_col is not None else "?"
            elig_pos = first_val(cells[pos_col])  if pos_col  is not None else ""

            players.append({
                "name":     clean_name,
                "team":     team,
                "elig_pos": elig_pos,
                "site_pts": pts,
                "on_dl":    on_dl,
                "type":     player_type,
            })

        if players:
            break

    return players


def recommend_replacements(injured: list[str],
                           fa_hitters: list[dict],
                           fa_pitchers: list[dict],
                           atc: dict,
                           cs_elig: dict,
                           n: int = 6) -> dict[str, list[str]]:
    """
    For each injured player, return the top N available free agents
    eligible at that position, ranked by ATC projected points
    (falling back to in-season site_pts pace if no ATC data).

    Position eligibility is determined by the cheat sheet (league's
    'most projected ABs' rule) with the site's elig_pos as fallback.
    """
    # Jon's roster position by roster slot
    JON_SLOT = {
        "William Contreras": "C",  "Spencer Steer":      "1B",
        "Ozzie Albies":      "2B", "Trea Turner":        "SS",
        "Alex Bregman":      "3B", "James Wood":         "OF",
        "Teoscar Hernandez": "OF", "Jackson Chourio":    "OF",
        "Marcell Ozuna":     "DH", "Chris Sale":         "SP",
        "Spencer Strider":   "SP", "Yoshinobu Yamamoto": "SP",
        "Dennis Santana":    "SP", "Devin Williams":     "RP",
        "Tyler Glasnow":     "SP",
    }

    def player_eligible(p: dict, slot: str) -> bool:
        """
        Check eligibility using cheat sheet first (league rule),
        then fall back to site elig_pos.
        """
        key = normalize_name(p["name"])
        if key in cs_elig:
            return slot in cs_elig[key]
        # Fallback: site elig_pos substring check
        return slot in p["elig_pos"]

    results = {}
    for entry in injured:
        # entry looks like "Spencer Strider (Atl SP)"
        player_name = entry.split("(")[0].strip()
        paren       = entry.split("(")[1].rstrip(")") if "(" in entry else ""
        site_pos    = paren.split()[-1] if paren else ""

        slot = JON_SLOT.get(player_name, site_pos)

        is_pitcher = slot in ("SP", "RP", "P")
        pool       = fa_pitchers if is_pitcher else fa_hitters

        eligible = [
            p for p in pool
            if player_eligible(p, slot) and not p.get("on_dl")
        ]

        def score(p):
            key = normalize_name(p["name"])
            if key in atc:
                return atc[key]["atc_pts"]
            return p["site_pts"] * 10

        top = sorted(eligible, key=score, reverse=True)[:n]

        lines = []
        for p in top:
            key     = normalize_name(p["name"])
            atc_pts = atc[key]["atc_pts"] if key in atc else None
            proj    = f"{atc_pts} ATC pts" if atc_pts else f"{p['site_pts']:.0f} site pts"
            # Show cheat-sheet positions if available, else site elig_pos
            pos_display = ",".join(sorted(cs_elig[key])) if key in cs_elig else p["elig_pos"]
            lines.append(f"    {p['name']:<26} {p['team']:<5} {pos_display:<12} {proj}")

        results[player_name] = lines

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DTFBL daily scraper")
    parser.add_argument(
        "--debug", action="store_true",
        help="Dump raw HTML pages to data/debug/ and print table structure for every page fetched",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("DTFBL scraper starting — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    if args.debug:
        log.info("DEBUG MODE ON — raw HTML will be saved to %s", DEBUG_DIR)

    try:
        session, session_id = login()
    except Exception as e:
        log.error("Login failed: %s", e)
        return

    # ── 1. Pull live standings (single fetch, all 7 teams) ───────────────────
    try:
        html, session_id = fetch(session, "display_stand.pl", session_id)
        if args.debug:
            dump_html("1_standings", html)
            dump_tables("display_stand.pl", html)
        standings = parse_standings(html)
        season    = standings.get("season", {})
        week      = standings.get("week", {})
        log.info("Standings fetched — %d teams in season, %d in week", len(season), len(week))
        if args.debug:
            print("\n  [debug] parse_standings result:")
            print("  SEASON:", json.dumps(season, indent=4))
            print("  WEEK:  ", json.dumps(week,   indent=4))
        else:
            for team, data in sorted(season.items(), key=lambda x: -x[1]["total"]):
                log.info("  %-22s  season: %+.1f  week: %+.1f",
                         team, data["total"], week.get(team, {}).get("total", 0))
    except Exception as e:
        log.error("Could not fetch standings: %s", e)
        standings = {"season": {}, "week": {}}
        season    = {}
        week      = {}

    # ── 2. Pull team stats page — player stats + IL detection ────────────────
    # display_team_stats.pl has both active player stats and IL markers (*).
    # (team_home.pl returns the standings page, not player data.)
    try:
        html, session_id = fetch_team_stats(session, session_id)
        if args.debug:
            dump_html("2_team_stats", html)
            dump_tables("display_team_stats.pl", html)
        jon     = parse_team_page(html)
        injured = parse_injured_players(html)
        log.info("Jon's Generals roster parsed — %d hitters, %d pitchers",
                 len(jon["hitters"]), len(jon["pitchers"]))
        if args.debug:
            print("\n  [debug] parse_team_page result:")
            print("  hitters:", json.dumps(jon["hitters"][:3], indent=4), "... (first 3)")
            print("  pitchers:", json.dumps(jon["pitchers"][:3], indent=4), "... (first 3)")
            print(f"  total_pts: {jon['total_pts']}")
        if injured:
            log.info("IL players found: %s", ", ".join(injured))
        else:
            log.info("No IL players detected")
        if not args.debug:
            append_roster_log(jon["hitters"],  "hitter")
            append_roster_log(jon["pitchers"], "pitcher")
    except Exception as e:
        log.error("Failed to fetch/parse team stats page: %s", e)
        jon     = {"hitters": [], "pitchers": [], "total_pts": 0}
        injured = []

    # ── 3. Fetch free agent pages directly from the site ─────────────────────
    # display_new_multi_stats.pl?...+freeagent+hitters/pitchers already filters
    # to NL-only available players (excludes AL, IL, and rostered players).
    atc      = build_atc_lookup()
    cs_elig  = build_cheat_sheet_eligibility()
    log.info("Cheat sheet eligibility loaded — %d players", len(cs_elig))

    fa_hitters  = []
    fa_pitchers = []
    try:
        html, session_id = fetch_free_agents(session, session_id, "hitters")
        if args.debug:
            dump_html("3_fa_hitters", html)
            dump_tables("display_new_multi_stats.pl?freeagent+hitters", html)
        fa_hitters = parse_free_agents(html, "hitters")
        log.info("Free agent hitters fetched — %d players", len(fa_hitters))
        if args.debug:
            print(f"\n  [debug] Top 15 FA hitters (by site pts or ATC):")
            top_h = sorted(fa_hitters, key=lambda p: (
                atc.get(normalize_name(p["name"]), {}).get("atc_pts", 0) or p["site_pts"] * 10
            ), reverse=True)[:15]
            for p in top_h:
                atc_pts = atc.get(normalize_name(p["name"]), {}).get("atc_pts")
                proj = f"{atc_pts} ATC" if atc_pts else f"{p['site_pts']:.0f} site"
                print(f"    {p['name']:<26} {p['team']:<5} {p['elig_pos']:<12} {proj}  IL={p['on_dl']}")
    except Exception as e:
        log.warning("Could not fetch FA hitters: %s", e)

    try:
        html, session_id = fetch_free_agents(session, session_id, "pitchers")
        if args.debug:
            dump_html("3_fa_pitchers", html)
            dump_tables("display_new_multi_stats.pl?freeagent+pitchers", html)
        fa_pitchers = parse_free_agents(html, "pitchers")
        log.info("Free agent pitchers fetched — %d players", len(fa_pitchers))
        if args.debug:
            print(f"\n  [debug] Top 15 FA pitchers (by site pts or ATC):")
            top_p = sorted(fa_pitchers, key=lambda p: (
                atc.get(normalize_name(p["name"]), {}).get("atc_pts", 0) or p["site_pts"] * 10
            ), reverse=True)[:15]
            for p in top_p:
                atc_pts = atc.get(normalize_name(p["name"]), {}).get("atc_pts")
                proj = f"{atc_pts} ATC" if atc_pts else f"{p['site_pts']:.0f} site"
                print(f"    {p['name']:<26} {p['team']:<5} {p['elig_pos']:<12} {proj}  IL={p['on_dl']}")
    except Exception as e:
        log.warning("Could not fetch FA pitchers: %s", e)

    # ── 4. Log standings to CSV ───────────────────────────────────────────────
    if not args.debug:
        append_standings_log(standings)

    # ── 5. Build alerts ───────────────────────────────────────────────────────
    alerts = []
    today  = date.today().strftime("%B %d, %Y")

    # Injury alerts — asterisk-marked players on IL + replacement recommendations
    if injured:
        recs = recommend_replacements(injured, fa_hitters, fa_pitchers, atc, cs_elig)
        alerts.append("🚨 INJURY ALERTS — Jon's Generals:")
        for player in injured:
            alerts.append(f"  * {player} is on the IL")
            player_name = player.split("(")[0].strip()
            if player_name in recs and recs[player_name]:
                alerts.append(f"    Top available replacements:")
                alerts.extend(recs[player_name])

    # Underperformance — estimate games played from AB count
    all_players = jon["hitters"] + jon["pitchers"]
    try:
        total_ab  = sum(int(p.get("AB", 0) or 0) for p in jon["hitters"])
        games_est = total_ab // 30   # rough: ~30 AB per team game
    except Exception:
        games_est = 0

    underperform = check_underperformance(all_players, games_est)
    if underperform:
        alerts.append("\n📉 UNDERPERFORMING vs ATC pace:")
        alerts.extend(underperform)

    # ── 6. Send email if any alerts ───────────────────────────────────────────
    jon_season = season.get("Jon's Generals", {}).get("total", 0)
    jon_week   = week.get("Jon's Generals", {}).get("total", 0)

    if alerts:
        body = f"DTFBL Daily Report — {today}\n\n"
        body += "\n".join(alerts)
        body += f"\n\n---\n"
        body += f"Jon's Generals: {jon_season:+.1f} pts (season)  {jon_week:+.1f} pts (this week)\n"
        body += "\nSeason Standings:\n"
        for team, data in sorted(season.items(), key=lambda x: -x[1]["total"]):
            marker = " ← you" if team == "Jon's Generals" else ""
            body += f"  {team:<22} {data['total']:+.1f}{marker}\n"

        if args.debug:
            print("\n── DEBUG: email body that would be sent ──")
            print(body)
        elif already_alerted_today():
            log.info("Alert already sent today — skipping email.")
        else:
            send_alert_email(f"⚾ DTFBL Alert — {today}", body)
            append_alerts_log(alerts)
    else:
        log.info("No alerts today.")

    log.info("Scraper finished.")


if __name__ == "__main__":
    main()
