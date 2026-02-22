#!/usr/bin/env python3
"""
Grade historical DTFBL drafts based on actual player performance.
Uses pybaseball to fetch real stats and calculates fantasy points.
"""

import csv
import warnings
from pybaseball import batting_stats, pitching_stats

warnings.filterwarnings('ignore')

# Scoring system
# Hitters: 1B(+1), 2B(+2), 3B(+4), HR(+4), R(+1), RBI(+1), SB(+1), BB(+1), E(-1)
# Pitchers: W(+12), L(-3), SV(+8), K(+1), BB(-1), CG(+5), ShO(+5), QS(+2)


def calc_hitter_points(row):
    """Calculate fantasy points for a hitter from their actual stats"""
    try:
        singles = int(row.get('1B', 0) or 0)
        doubles = int(row.get('2B', 0) or 0)
        triples = int(row.get('3B', 0) or 0)
        hr = int(row.get('HR', 0) or 0)
        runs = int(row.get('R', 0) or 0)
        rbi = int(row.get('RBI', 0) or 0)
        sb = int(row.get('SB', 0) or 0)
        bb = int(row.get('BB', 0) or 0)

        points = singles + (doubles * 2) + (triples * 4) + (hr * 4) + runs + rbi + sb + bb
        return points
    except:
        return 0


def calc_pitcher_points(row):
    """Calculate fantasy points for a pitcher from their actual stats"""
    try:
        wins = int(row.get('W', 0) or 0)
        losses = int(row.get('L', 0) or 0)
        saves = int(row.get('SV', 0) or 0)
        strikeouts = int(row.get('SO', 0) or 0)
        walks = int(row.get('BB', 0) or 0)
        # QS not always available, estimate from GS and ERA
        qs = int(row.get('QS', 0) or 0)

        points = (wins * 12) + (losses * -3) + (saves * 8) + strikeouts - walks + (qs * 2)
        return points
    except:
        return 0


def normalize_name(name):
    """Normalize player names for matching"""
    if not name:
        return ""
    # Remove suffixes, periods, normalize spacing
    name = name.replace(".", "").replace("'", "").replace("-", " ").lower().strip()
    # Handle common variations
    name = name.replace("jr", "").replace("sr", "").replace(" ii", "").replace(" iii", "")
    # Fix common typos/variations in the draft data
    fixes = {
        "elly de la cuz": "elly de la cruz",
        "christian yelish": "christian yelich",
        "zach wheeler": "zack wheeler",
        "iam happ": "ian happ",
        "ronald acuna": "ronald acuna",
        "jt realmuto": "jt realmuto",
        "j t realmuto": "jt realmuto",
        "manny machado": "manny machado",
        "ozzie albies": "ozzie albies",
        "freddy freeman": "freddie freeman",
    }
    normalized = " ".join(name.split())
    return fixes.get(normalized, normalized)


def load_draft_picks(year):
    """Load draft picks for a given year"""
    picks = []
    with open('all_drafts_2009_2025.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Year'] == str(year):
                picks.append({
                    'team': row['Team'],
                    'player': row['Player'],
                    'position': row['Position'],
                    'price': float(row['Price']),
                    'mlb_team': row.get('MLB_Team', ''),
                })
    return picks


def fetch_stats(year):
    """Fetch batting and pitching stats for a year"""
    print(f"  Fetching {year} batting stats...")
    batting = batting_stats(year, qual=1)

    print(f"  Fetching {year} pitching stats...")
    pitching = pitching_stats(year, qual=1)

    return batting, pitching


def match_player_stats(player_name, position, batting_df, pitching_df):
    """Match a drafted player to their actual stats"""
    norm_name = normalize_name(player_name)

    # Determine if hitter or pitcher
    is_pitcher = position in ['SP', 'RP', 'SP / RP']

    if is_pitcher:
        for _, row in pitching_df.iterrows():
            if normalize_name(row['Name']) == norm_name:
                points = calc_pitcher_points(row)
                games = int(row.get('G', 0) or 0)
                return points, games, 'pitcher'
    else:
        for _, row in batting_df.iterrows():
            if normalize_name(row['Name']) == norm_name:
                points = calc_hitter_points(row)
                games = int(row.get('G', 0) or 0)
                return points, games, 'hitter'

    # Try fuzzy match - check if name is contained
    if is_pitcher:
        for _, row in pitching_df.iterrows():
            if norm_name in normalize_name(row['Name']) or normalize_name(row['Name']) in norm_name:
                points = calc_pitcher_points(row)
                games = int(row.get('G', 0) or 0)
                return points, games, 'pitcher'
    else:
        for _, row in batting_df.iterrows():
            if norm_name in normalize_name(row['Name']) or normalize_name(row['Name']) in norm_name:
                points = calc_hitter_points(row)
                games = int(row.get('G', 0) or 0)
                return points, games, 'hitter'

    return 0, 0, 'not_found'


def grade_draft_year(year):
    """Grade all picks for a given draft year"""
    print(f"\nGrading {year} draft...")

    picks = load_draft_picks(year)
    batting, pitching = fetch_stats(year)

    results = []
    for pick in picks:
        points, games, match_type = match_player_stats(
            pick['player'], pick['position'], batting, pitching
        )

        # Calculate value: points per dollar spent
        price = pick['price']
        ppd = points / price if price > 0 else points

        # Flag potential injuries (less than 60 games for hitters, less than 50 IP worth for pitchers)
        injury_flag = ""
        if match_type == 'hitter' and games < 60:
            injury_flag = "INJURED?"
        elif match_type == 'pitcher' and games < 15:
            injury_flag = "INJURED?"
        elif match_type == 'not_found':
            injury_flag = "NO STATS"

        results.append({
            'team': pick['team'],
            'player': pick['player'],
            'position': pick['position'],
            'price': price,
            'points': points,
            'games': games,
            'ppd': ppd,
            'injury_flag': injury_flag,
        })

    return results


def print_team_grades(results, year):
    """Print grades grouped by team"""
    teams = {}
    for r in results:
        team = r['team']
        if team not in teams:
            teams[team] = []
        teams[team].append(r)

    print(f"\n{'='*90}")
    print(f"{year} DRAFT GRADES")
    print(f"{'='*90}")

    # Calculate team totals
    team_totals = []
    for team, picks in teams.items():
        total_points = sum(p['points'] for p in picks)
        total_spent = sum(p['price'] for p in picks)
        team_totals.append((team, total_points, total_spent))

    # Sort by total points
    team_totals.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTEAM STANDINGS BY ACTUAL POINTS PRODUCED:")
    print("-" * 60)
    for rank, (team, points, spent) in enumerate(team_totals, 1):
        ppd = points / spent if spent > 0 else 0
        print(f"  {rank}. {team:<20} {points:>5} pts  (${spent:.0f} spent, {ppd:.1f} pts/$)")

    # Best and worst individual picks
    all_picks = sorted(results, key=lambda x: x['ppd'], reverse=True)

    print(f"\nBEST VALUE PICKS (Points per Dollar):")
    print("-" * 80)
    for p in all_picks[:10]:
        flag = f" [{p['injury_flag']}]" if p['injury_flag'] else ""
        print(f"  ${p['price']:2.0f} {p['player']:<22} {p['team']:<18} {p['points']:>4} pts ({p['ppd']:.1f} pts/$){flag}")

    print(f"\nWORST VALUE PICKS (High price, low return):")
    print("-" * 80)
    # Filter to picks that cost $10+ to find real busts
    expensive_picks = [p for p in results if p['price'] >= 10]
    expensive_picks.sort(key=lambda x: x['ppd'])
    for p in expensive_picks[:10]:
        flag = f" [{p['injury_flag']}]" if p['injury_flag'] else ""
        print(f"  ${p['price']:2.0f} {p['player']:<22} {p['team']:<18} {p['points']:>4} pts ({p['ppd']:.1f} pts/$){flag}")

    return team_totals


def main():
    years = [2021, 2022, 2023, 2024]  # Skip 2025 for now, might be current season

    all_standings = {}

    for year in years:
        try:
            results = grade_draft_year(year)
            standings = print_team_grades(results, year)
            all_standings[year] = standings
        except Exception as e:
            print(f"Error grading {year}: {e}")

    # Summary across all years
    print("\n" + "=" * 90)
    print("MULTI-YEAR SUMMARY (2021-2024)")
    print("=" * 90)

    team_multi_year = {}
    for year, standings in all_standings.items():
        for team, points, spent in standings:
            if team not in team_multi_year:
                team_multi_year[team] = {'points': 0, 'spent': 0, 'years': 0}
            team_multi_year[team]['points'] += points
            team_multi_year[team]['spent'] += spent
            team_multi_year[team]['years'] += 1

    print("\nCUMULATIVE POINTS PRODUCED (2021-2024):")
    print("-" * 60)
    sorted_teams = sorted(team_multi_year.items(), key=lambda x: x[1]['points'], reverse=True)
    for rank, (team, data) in enumerate(sorted_teams, 1):
        avg_ppd = data['points'] / data['spent'] if data['spent'] > 0 else 0
        print(f"  {rank}. {team:<20} {data['points']:>6} pts  ({avg_ppd:.1f} pts/$ avg)")


if __name__ == "__main__":
    main()
