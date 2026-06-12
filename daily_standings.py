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
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from curl_cffi import requests as curl_requests
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
    cgisessid = os.getenv("ONROTO_CGISESSID", "")
    if not cgisessid:
        raise RuntimeError(
            "ONROTO_CGISESSID secret not set. "
            "In Chrome, open DevTools → Application → Cookies → onroto.fangraphs.com, "
            "copy the CGISESSID value, and add it as a GitHub secret."
        )

    # curl_cffi impersonates Chrome's TLS fingerprint, bypassing Cloudflare's bot detection.
    session = curl_requests.Session(impersonate="chrome136")
    session.cookies.set("CGISESSID", cgisessid, domain="onroto.fangraphs.com")

    # Navigate directly to standings — CGISESSID means we're already authenticated.
    url = f"{BASE_URL}/display_stand.pl?{LEAGUE_ID}+{JON_TEAM_ID}"
    resp = session.get(url, timeout=30)
    if resp.status_code != 200:
        snippet = resp.text[:400].replace("\n", " ").strip()
        raise RuntimeError(f"HTTP {resp.status_code} fetching standings: {snippet}")

    session_id = extract_session_id(resp.text)
    if not session_id:
        raise RuntimeError(
            "Could not extract session_id — CGISESSID may be expired. "
            "Refresh it from Chrome DevTools."
        )

    print(f"Logged in via CGISESSID. session_id={session_id[:8]}…")
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


# ── Message Board / Trade Block ───────────────────────────────────────────────

def fetch_message_board(session: requests.Session, session_id: str) -> tuple[str, str]:
    url  = f"{BASE_URL}/team_message_board.pl?{LEAGUE_ID}+{JON_TEAM_ID}&session_id={session_id}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    new_sid = extract_session_id(resp.text) or session_id
    return resp.text, new_sid


def _current_block_start() -> datetime:
    """Return the datetime when the current block window opened (last Tuesday at noon)."""
    now = datetime.now()
    days_back = (now.weekday() - 1) % 7   # 0 on Tuesday, 1 on Wednesday, …
    last_tuesday = now - timedelta(days=days_back)
    return last_tuesday.replace(hour=12, minute=0, second=0, microsecond=0)


def _parse_post_dt(msg_date: str) -> datetime | None:
    """Parse OnRoto message date like 'On 04-30-2026 at 8:24:46 AM' → datetime."""
    cleaned = re.sub(r"^[Oo]n\s+", "", msg_date.strip())
    for fmt in ("%m-%d-%Y at %I:%M:%S %p", "%m-%d-%Y at %I:%M %p"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def parse_trade_block(html: str) -> list[dict]:
    """
    Parse the message board for this week's trade block posts.
    Returns list of dicts: {team, date, offering, wanting}
    where offering/wanting are lists of player strings.

    Matches messages whose content starts with 'on the block' or 'also on the block'.
    Filters to the current block window (since last Tuesday at noon) so old posts
    don't accumulate.
    """
    soup = BeautifulSoup(html, "html.parser")
    mb   = soup.find(class_="message_board")
    if not mb:
        return []

    block_start = _current_block_start()
    posts = []

    for td in mb.find_all("td"):
        sender_tag  = td.find("font", class_="msg_sender")
        content_tag = td.find("font", class_="msg_content")
        date_tag    = td.find("font", class_="msg_date")
        if not (sender_tag and content_tag and date_tag):
            continue

        msg_date = date_tag.get_text(strip=True)
        post_dt  = _parse_post_dt(msg_date)
        if post_dt is None or post_dt < block_start:
            continue

        content = content_tag.get_text(separator="\n", strip=True)
        if not re.match(r"(?i)(also\s+)?on\s+the\s+block", content):
            continue

        lines = [l.strip() for l in content.splitlines() if l.strip()]

        # Split on "to replace" (case-insensitive)
        split_idx = next(
            (i for i, l in enumerate(lines) if re.match(r"(?i)to\s+replace", l)),
            None,
        )

        # First line is the "On the block MM/DD" header — skip it
        if split_idx is not None:
            offering = [l for l in lines[1:split_idx] if not re.match(r"(?i)to\s+replace", l)]
            wanting  = [l for l in lines[split_idx+1:]]
        else:
            offering = lines[1:]
            wanting  = []

        posts.append({
            "team":     sender_tag.get_text(strip=True),
            "date":     msg_date,
            "offering": offering,
            "wanting":  wanting,
        })

    return posts


# ── Email ─────────────────────────────────────────────────────────────────────

def send_standings_email(standings: dict, trade_block: list[dict]):
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

    if trade_block:
        lines += ["", "─" * 46, "ON THE BLOCK", ""]
        for post in trade_block:
            lines.append(f"{post['team']}  ({post['date']})")
            lines.append("  Offering:")
            for p in post["offering"]:
                lines.append(f"    {p}")
            if post["wanting"]:
                lines.append("  For:")
                for p in post["wanting"]:
                    lines.append(f"    {p}")
            lines.append("")

    lines += ["Full history: github.com/Jon-zachary/dtfbl-draft-analysis"]
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

def _send_scraper_error_email(error: str) -> None:
    from_addr = os.getenv("ALERT_FROM_EMAIL")
    app_pw    = os.getenv("ALERT_APP_PASSWORD")
    to_addr   = os.getenv("ALERT_TO_EMAIL")
    if not all([from_addr, app_pw, to_addr]):
        print("Cannot send error email — email secrets not set", file=sys.stderr)
        return
    msg = MIMEText(f"DTFBL scraper could not log in to OnRoto:\n\n{error}\n\nNo standings recorded today.")
    msg["Subject"] = "DTFBL scraper login failed"
    msg["From"] = from_addr
    msg["To"] = to_addr
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_pw)
            server.sendmail(from_addr, to_addr, msg.as_string())
        print("Error notification sent.")
    except Exception as e:
        print(f"Could not send error email: {e}", file=sys.stderr)


def main():
    print(f"DTFBL daily standings — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

    try:
        session, session_id = login()
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        _send_scraper_error_email(str(e))
        sys.exit(0)  # exit cleanly so the workflow doesn't fail

    html, _ = fetch(session, "display_stand.pl", session_id)
    standings = parse_standings(html)

    season = standings.get("season", {})
    if not season:
        sys.exit("ERROR: Standings parsed empty — site structure may have changed")

    print(f"Fetched standings for {len(season)} teams")

    html_mb, session_id = fetch_message_board(session, session_id)
    trade_block = parse_trade_block(html_mb)
    print(f"Trade block posts this season: {len(trade_block)}")

    append_standings_log(standings)
    send_standings_email(standings, trade_block)


if __name__ == "__main__":
    main()
