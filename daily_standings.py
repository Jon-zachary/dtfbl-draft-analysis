#!/usr/bin/env python3
"""
DTFBL Daily Standings — cloud version
--------------------------------------
Logs in to OnRoto, fetches league standings, emails a summary,
and appends one row to data/standings_log.csv (committed back to
the repo by the GitHub Actions workflow).

Secrets expected as environment variables (GitHub Actions secrets):
  ONROTO_USERNAME, ONROTO_PASSWORD
  ALERT_FROM_EMAIL, ALERT_APP_PASSWORD, ALERT_TO_EMAIL
"""

import csv
import os
import re
import smtplib
import sys
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

LEAGUE_ID   = "dtfbl1989"
JON_TEAM_ID = "6"
BASE_URL    = "https://onroto.fangraphs.com/baseball/webnew"

TEAM_ORDER = [
    "Forest Rangers",
    "Bert's Bombers",
    "Charlie's Stars",
    "Ryan's Lions",
    "David's Devils",
    "Jake's Snakes",
    "Jon's Generals",
]

DATA_DIR      = Path(__file__).parent / "data"
STANDINGS_LOG = DATA_DIR / "standings_log.csv"

DATA_DIR.mkdir(exist_ok=True)


# ── Session / Auth ────────────────────────────────────────────────────────────

def extract_session_id(html: str) -> str | None:
    match = re.search(r"session_id=([A-Za-z0-9]+)", html)
    return match.group(1) if match else None


def login() -> tuple[requests.Session, str]:
    username = os.getenv("ONROTO_USERNAME")
    password = os.getenv("ONROTO_PASSWORD")
    if not username or not password:
        sys.exit("ERROR: Set ONROTO_USERNAME and ONROTO_PASSWORD")

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    })

    resp = session.get("https://onroto.fangraphs.com/index.pl", timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form")
    if not form:
        sys.exit("ERROR: Could not find login form")

    action = form.get("action", "/index.pl")
    if not action.startswith("http"):
        action = "https://onroto.fangraphs.com" + action

    payload = {inp.get("name"): inp.get("value", "")
               for inp in form.find_all("input") if inp.get("name")}

    email_field = next(
        (inp.get("name") for inp in form.find_all("input")
         if inp.get("type") in ("text", "email")
         or any(kw in (inp.get("name") or "").lower()
                for kw in ("mail", "user", "login", "id"))),
        "email",
    )
    pass_field = next(
        (inp.get("name") for inp in form.find_all("input")
         if inp.get("type") == "password"),
        "password",
    )
    payload[email_field] = username
    payload[pass_field]  = password

    session.headers["Referer"] = resp.url
    resp = session.post(action, data=payload, timeout=30, allow_redirects=True)
    resp.raise_for_status()

    session_id = extract_session_id(resp.text)
    if not session_id:
        sys.exit("ERROR: Login failed — check credentials")

    print(f"Logged in. session_id={session_id[:8]}…")
    return session, session_id


# ── Fetch & Parse ─────────────────────────────────────────────────────────────

def fetch(session: requests.Session, path: str, session_id: str) -> tuple[str, str]:
    url  = f"{BASE_URL}/{path}?{LEAGUE_ID}+{JON_TEAM_ID}&session_id={session_id}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    new_sid = extract_session_id(resp.text) or session_id
    return resp.text, new_sid


def parse_standings(html: str) -> dict:
    """
    Returns {"season": {team: {"hit", "pit", "total"}},
             "week":   {team: {"hit", "pit", "total"}}}
    """
    soup    = BeautifulSoup(html, "html.parser")
    results = {"season": {}, "week": {}}
    keys    = ["season", "week"]
    found   = 0

    for table in soup.find_all("table"):
        raw_headers = [th.get_text(strip=True) for th in table.find_all("th")]
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


# ── CSV Log ───────────────────────────────────────────────────────────────────

def append_standings_log(standings: dict):
    today  = date.today().isoformat()
    season = standings.get("season", {})

    write_header = not STANDINGS_LOG.exists()
    with open(STANDINGS_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date"] + TEAM_ORDER)
        row = [today] + [season.get(team, {}).get("total", "") for team in TEAM_ORDER]
        writer.writerow(row)
    print(f"Standings logged → {STANDINGS_LOG}")


# ── Email ─────────────────────────────────────────────────────────────────────

def send_standings_email(standings: dict):
    from_addr = os.getenv("ALERT_FROM_EMAIL")
    app_pw    = os.getenv("ALERT_APP_PASSWORD")
    to_addr   = os.getenv("ALERT_TO_EMAIL")

    if not all([from_addr, app_pw, to_addr]):
        print("Email not configured — standings printed above, skipping email.")
        return

    season = standings.get("season", {})
    week   = standings.get("week",   {})
    today  = date.today().strftime("%B %d, %Y")

    ranked = sorted(season.items(), key=lambda x: -x[1]["total"])

    lines = [f"DTFBL Standings — {today}", ""]
    lines.append(f"{'#':<3} {'Team':<22} {'Season':>8}  {'Week':>7}")
    lines.append("-" * 46)
    for i, (team, data) in enumerate(ranked, 1):
        week_pts = week.get(team, {}).get("total", 0)
        marker   = " ←" if team == "Jon's Generals" else ""
        lines.append(
            f"{i:<3} {team:<22} {data['total']:>+8.1f}  {week_pts:>+7.1f}{marker}"
        )

    lines += ["", "Full history: github.com/Jon-zachary/dtfbl-draft-analysis"]
    body = "\n".join(lines)
    print(body)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚾ DTFBL Standings — {today}"
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_pw)
            server.sendmail(from_addr, to_addr, msg.as_string())
        print(f"Email sent to {to_addr}")
    except Exception as e:
        print(f"ERROR sending email: {e}", file=sys.stderr)
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"DTFBL daily standings — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

    session, session_id = login()

    html, _ = fetch(session, "display_stand.pl", session_id)
    standings = parse_standings(html)

    season = standings.get("season", {})
    if not season:
        sys.exit("ERROR: Standings parsed empty — site structure may have changed")

    print(f"Fetched standings for {len(season)} teams")

    append_standings_log(standings)
    send_standings_email(standings)


if __name__ == "__main__":
    main()
