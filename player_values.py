#!/usr/bin/env python3
"""
DTFBL Player Values Calculator
Based on 2026 ATC Projections from FanGraphs

TWO VALUATIONS:
---------------
1. VORP VALUE: What a player is theoretically "worth" (rational market)
2. EXPECTED PRICE: What they'll actually cost based on 16 years of DTFBL history

Your league has STAR INFLATION:
- Top 5 players: avg $72 (vs $38 VORP value) - 90% overpay!
- Picks 70-98: avg $1-3 (subsidize the stars)

STRATEGY INSIGHT:
- If Expected Price > VORP Value: Let someone else overpay
- If Expected Price < VORP Value: Target this player!
"""

# Scoring system
# Hitters: 1B(+1), 2B(+2), 3B(+4), HR(+4), R(+1), RBI(+1), SB(+1), BB(+1), E(-1)
# Pitchers: W(+12), L(-3), SV(+8), K(+1), BB(-1), CG(+5), ShO(+5), QS(+2)

# Replacement levels - the projected points of the LAST starter at each position
# These define the "free" baseline - value comes from exceeding this
REPLACEMENT_LEVELS = {
    "C": 170,
    "1B": 399,
    "2B": 299,
    "SS": 211,
    "3B": 225,
    "OF": 352,
    "DH": 399,  # Same as 1B
    "SP": 202,
    "RP": 131,
}

# League structure
TEAMS = 7
BUDGET_PER_TEAM = 260
TOTAL_BUDGET = TEAMS * BUDGET_PER_TEAM  # $1,820

# Roster slots per team
ROSTER_SLOTS = {
    "C": 1,   # 7 total
    "1B": 1,  # 7 total
    "2B": 1,  # 7 total
    "SS": 1,  # 7 total
    "3B": 1,  # 7 total
    "OF": 3,  # 21 total
    "DH": 1,  # 7 total
    "SP": 3,  # 21 total
    "RP": 1,  # 7 total
    "SP/RP": 1,  # 7 total (assume RP)
}
TOTAL_ROSTER_SPOTS = sum(ROSTER_SLOTS.values()) * TEAMS  # 98

# Historical price curve from 16 years of DTFBL data (2009-2025)
# This is what players ACTUALLY sell for based on their rank
# Rank 1 = most expensive pick, Rank 98 = cheapest
HISTORICAL_PRICE_BY_RANK = {
    1: 81, 2: 76, 3: 71, 4: 68, 5: 64,
    6: 61, 7: 58, 8: 56, 9: 54, 10: 52,
    11: 49, 12: 47, 13: 45, 14: 44, 15: 42,
    16: 40, 17: 39, 18: 37, 19: 36, 20: 36,
    21: 34, 22: 33, 23: 32, 24: 31, 25: 30,
    26: 29, 27: 28, 28: 27, 29: 26, 30: 27,
    31: 25, 32: 24, 33: 23, 34: 22, 35: 22,
    36: 21, 37: 20, 38: 19, 39: 18, 40: 18,
    41: 17, 42: 16, 43: 15, 44: 15, 45: 14,
    46: 13, 47: 12, 48: 12, 49: 11, 50: 12,
    51: 10, 52: 10, 53: 9, 54: 9, 55: 8,
    56: 8, 57: 7, 58: 7, 59: 7, 60: 7,
    61: 6, 62: 5, 63: 5, 64: 5, 65: 4,
    66: 4, 67: 4, 68: 3, 69: 3, 70: 3,
    71: 3, 72: 2, 73: 2, 74: 2, 75: 2,
    76: 2, 77: 1, 78: 1, 79: 1, 80: 1,
    81: 1, 82: 1, 83: 1, 84: 1, 85: 1,
    86: 1, 87: 1, 88: 1, 89: 1, 90: 1,
    91: 1, 92: 1, 93: 1, 94: 1, 95: 1,
    96: 1, 97: 1, 98: 1,
}


def calc_hitter_points(singles, doubles, triples, hr, runs, rbi, sb, bb):
    """Calculate fantasy points for a hitter"""
    return (singles * 1) + (doubles * 2) + (triples * 4) + (hr * 4) + runs + rbi + sb + bb


def calc_pitcher_points(wins, losses, saves, strikeouts, walks, ip):
    """Calculate fantasy points for a pitcher"""
    # Estimate quality starts: ~55% of starts for good pitchers
    estimated_starts = ip / 6
    estimated_qs = estimated_starts * 0.55

    points = (wins * 12) + (losses * -3) + (saves * 8) + strikeouts + (walks * -1) + (estimated_qs * 2)
    return points


def calc_vorp(points, position):
    """Calculate Value Over Replacement Player"""
    replacement = REPLACEMENT_LEVELS.get(position, 300)
    return max(0, points - replacement)


# 2026 ATC Projections - Hitters
# Format: (name, position, singles, doubles, triples, hr, runs, rbi, sb, bb)
HITTER_PROJECTIONS = [
    ("Shohei Ohtani", "DH", 79, 27, 5, 46, 120, 107, 24, 91),
    ("Juan Soto", "OF", 84, 25, 1, 38, 107, 98, 21, 123),
    ("Ketel Marte", "2B", 86, 29, 2, 29, 88, 87, 5, 67),
    ("Fernando Tatis Jr.", "OF", 94, 28, 2, 28, 97, 78, 26, 70),
    ("Ronald Acuna Jr.", "OF", 93, 25, 2, 28, 104, 76, 24, 84),
    ("Kyle Tucker", "OF", 81, 28, 2, 29, 93, 87, 23, 84),
    ("Francisco Lindor", "SS", 88, 27, 1, 25, 91, 76, 23, 55),
    ("Will Smith", "C", 70, 21, 1, 20, 69, 69, 2, 58),
    ("Corbin Carroll", "OF", 73, 27, 10, 26, 98, 77, 32, 64),
    ("William Contreras", "C", 92, 27, 1, 19, 76, 77, 6, 69),
    ("Trea Turner", "SS", 111, 29, 4, 18, 90, 71, 28, 40),
    ("Mookie Betts", "OF", 92, 30, 2, 21, 88, 78, 9, 65),
    ("Elly De La Cruz", "SS", 88, 30, 5, 22, 91, 75, 40, 60),
    ("Geraldo Perdomo", "SS", 99, 27, 4, 12, 87, 63, 20, 74),
    ("Jackson Merrill", "OF", 92, 31, 4, 22, 77, 81, 8, 40),
    ("Pete Crow-Armstrong", "OF", 81, 28, 5, 22, 83, 76, 33, 35),
    ("Alex Bregman", "3B", 91, 27, 1, 22, 79, 79, 2, 64),
    ("Bryce Harper", "1B", 83, 31, 1, 26, 82, 83, 9, 74),
    ("Matt Chapman", "3B", 72, 27, 2, 23, 80, 72, 9, 69),
    ("Gabriel Moreno", "C", 75, 20, 1, 11, 53, 54, 4, 41),
    ("Willy Adames", "SS", 77, 26, 1, 27, 83, 83, 11, 69),
    ("Rafael Devers", "3B", 82, 28, 1, 31, 87, 92, 2, 83),
    ("Dansby Swanson", "SS", 87, 24, 2, 22, 77, 74, 16, 52),
    ("Austin Riley", "3B", 86, 28, 2, 27, 80, 84, 2, 45),
    ("Freddie Freeman", "1B", 92, 32, 2, 22, 83, 83, 8, 64),
    ("Bo Bichette", "SS", 109, 29, 2, 17, 74, 75, 5, 38),
    ("Kyle Schwarber", "OF", 63, 20, 1, 41, 97, 104, 6, 96),
    ("Brice Turang", "2B", 102, 25, 3, 15, 79, 67, 30, 57),
    ("Andy Pages", "OF", 82, 28, 2, 22, 73, 75, 10, 35),
    ("Manny Machado", "3B", 95, 26, 0, 26, 77, 87, 9, 50),
    ("Ozzie Albies", "2B", 85, 28, 3, 24, 85, 80, 12, 45),
    ("Pete Alonso", "1B", 70, 25, 1, 38, 85, 100, 2, 65),
    ("Matt Olson", "1B", 72, 30, 1, 35, 90, 95, 2, 80),
    ("Nolan Arenado", "3B", 85, 30, 1, 22, 75, 85, 3, 55),
    ("J.T. Realmuto", "C", 75, 22, 2, 15, 60, 55, 12, 40),
    ("Willson Contreras", "C", 80, 24, 1, 18, 65, 70, 3, 50),
    ("CJ Abrams", "SS", 95, 22, 5, 18, 85, 60, 35, 45),
    ("Marcell Ozuna", "DH", 75, 25, 1, 35, 80, 100, 2, 55),
    ("Ian Happ", "OF", 70, 28, 2, 22, 75, 75, 8, 70),
    ("Michael Harris II", "OF", 90, 25, 4, 20, 80, 70, 18, 40),
    ("Brandon Marsh", "OF", 75, 22, 3, 15, 70, 60, 12, 55),
    ("Lars Nootbaar", "OF", 65, 20, 2, 18, 70, 60, 8, 70),
    ("Bryan De La Cruz", "OF", 80, 25, 2, 22, 70, 75, 5, 35),
    ("Spencer Steer", "3B", 80, 28, 2, 20, 75, 75, 8, 50),
    ("Jesse Winker", "OF", 70, 22, 1, 18, 65, 65, 3, 75),
    ("Travis d'Arnaud", "C", 70, 18, 1, 14, 50, 55, 1, 35),
    ("Patrick Bailey", "C", 65, 18, 1, 12, 50, 50, 3, 40),
    ("Yasmani Grandal", "C", 55, 15, 0, 12, 45, 50, 1, 55),
    ("Luis Arraez", "2B", 120, 25, 1, 5, 70, 55, 3, 50),
    ("Gavin Lux", "2B", 80, 22, 2, 12, 65, 55, 8, 50),
    ("Jake Cronenworth", "2B", 85, 25, 2, 15, 70, 65, 5, 50),
    ("Bryson Stott", "2B", 90, 24, 3, 14, 75, 65, 15, 50),
    ("Ha-Seong Kim", "SS", 80, 22, 3, 12, 70, 55, 18, 55),
    ("Ezequiel Tovar", "SS", 85, 25, 4, 18, 75, 70, 15, 35),
    ("Ryan McMahon", "3B", 65, 25, 2, 22, 70, 75, 5, 60),
    ("Ke'Bryan Hayes", "3B", 85, 28, 2, 12, 65, 60, 8, 45),
    ("Alec Bohm", "3B", 100, 32, 1, 18, 75, 85, 3, 45),
    ("Max Muncy", "3B", 55, 20, 1, 25, 70, 75, 2, 80),
    ("Cody Bellinger", "OF", 80, 28, 2, 22, 80, 75, 10, 55),
    ("Christian Walker", "1B", 70, 28, 1, 30, 80, 90, 3, 60),
    ("Josh Bell", "1B", 75, 28, 1, 20, 70, 75, 2, 65),
    ("LaMonte Wade Jr.", "1B", 60, 20, 1, 15, 55, 55, 3, 55),
    ("Rhys Hoskins", "1B", 60, 22, 1, 28, 75, 85, 2, 70),
    ("JD Martinez", "DH", 70, 28, 1, 25, 70, 85, 1, 55),
    ("Jorge Soler", "DH", 60, 22, 1, 30, 75, 85, 2, 60),
    ("Brandon Lowe", "2B", 60, 22, 2, 22, 70, 70, 5, 55),
    # Additional depth
    ("Jackson Chourio", "OF", 85, 25, 3, 22, 78, 72, 15, 42),
    ("Teoscar Hernandez", "OF", 78, 26, 2, 28, 82, 88, 6, 48),
    ("Randy Arozarena", "OF", 80, 25, 3, 22, 78, 72, 18, 52),
    ("Nick Castellanos", "DH", 85, 30, 1, 22, 75, 80, 3, 45),
]

# 2026 ATC Projections - Pitchers
# Format: (name, position, wins, losses, saves, strikeouts, walks, ip)
PITCHER_PROJECTIONS = [
    ("Paul Skenes", "SP", 12, 8, 0, 221, 45, 184),
    ("Logan Webb", "SP", 13, 10, 0, 183, 44, 193),
    ("Cristopher Sanchez", "SP", 12, 7, 0, 179, 45, 185),
    ("Yoshinobu Yamamoto", "SP", 12, 7, 0, 175, 47, 160),
    ("Chris Sale", "SP", 11, 6, 0, 187, 39, 152),
    ("Jesus Luzardo", "SP", 12, 9, 0, 191, 53, 173),
    ("Hunter Greene", "SP", 10, 8, 0, 198, 53, 164),
    ("Zack Wheeler", "SP", 9, 5, 0, 143, 33, 124),
    ("Freddy Peralta", "SP", 12, 9, 0, 183, 60, 164),
    ("Spencer Strider", "SP", 10, 6, 0, 180, 45, 145),
    ("Yu Darvish", "SP", 10, 8, 0, 165, 45, 160),
    ("Blake Snell", "SP", 10, 8, 0, 175, 70, 150),
    ("Ranger Suarez", "SP", 11, 7, 0, 145, 45, 170),
    ("Dylan Cease", "SP", 10, 9, 0, 190, 75, 175),
    ("Miles Mikolas", "SP", 9, 9, 0, 130, 35, 175),
    ("Sonny Gray", "SP", 10, 7, 0, 160, 50, 160),
    ("Shota Imanaga", "SP", 10, 7, 0, 155, 40, 155),
    ("Mitch Keller", "SP", 10, 8, 0, 165, 55, 175),
    ("Zac Gallen", "SP", 11, 7, 0, 170, 45, 175),
    ("Tyler Glasnow", "SP", 10, 6, 0, 185, 50, 145),
    ("Joe Musgrove", "SP", 9, 8, 0, 145, 40, 155),
    ("MacKenzie Gore", "SP", 9, 7, 0, 155, 55, 150),
    ("Merrill Kelly", "SP", 10, 9, 0, 140, 40, 175),
    # Relievers
    ("Ryan Helsley", "RP", 4, 3, 38, 85, 20, 65),
    ("Edwin Diaz", "RP", 4, 3, 32, 95, 25, 60),
    ("Josh Hader", "RP", 4, 3, 35, 90, 22, 62),
    ("Camilo Doval", "RP", 4, 4, 30, 75, 28, 60),
    ("Alexis Diaz", "RP", 3, 3, 28, 80, 25, 58),
    ("Robert Suarez", "RP", 4, 3, 32, 70, 20, 60),
    ("Tanner Scott", "RP", 5, 4, 30, 85, 30, 65),
    ("A.J. Minter", "RP", 4, 3, 25, 75, 25, 60),
    ("Devin Williams", "RP", 4, 2, 30, 90, 25, 55),
    ("Raisel Iglesias", "RP", 4, 3, 32, 70, 18, 60),
    ("Kenley Jansen", "RP", 4, 4, 28, 75, 22, 58),
    ("Daniel Hudson", "RP", 3, 3, 15, 55, 18, 55),
    ("Yuki Matsui", "RP", 4, 3, 25, 70, 22, 58),
    ("Jeff Hoffman", "RP", 5, 4, 12, 85, 28, 65),
    ("Pierce Johnson", "RP", 4, 3, 20, 70, 25, 55),
    ("Evan Phillips", "RP", 4, 3, 22, 72, 22, 58),
]


def calculate_all_players():
    """Calculate points and VORP for all players"""
    players = []

    # Process hitters
    for name, pos, s, d, t, hr, r, rbi, sb, bb in HITTER_PROJECTIONS:
        points = calc_hitter_points(s, d, t, hr, r, rbi, sb, bb)
        vorp = calc_vorp(points, pos)
        players.append({
            "name": name,
            "position": pos,
            "points": round(points),
            "vorp": round(vorp),
        })

    # Process pitchers
    for name, pos, w, l, sv, k, bb, ip in PITCHER_PROJECTIONS:
        points = calc_pitcher_points(w, l, sv, k, bb, ip)
        vorp = calc_vorp(points, pos)
        players.append({
            "name": name,
            "position": pos,
            "points": round(points),
            "vorp": round(vorp),
        })

    return players


def select_drafted_players(players):
    """Select the players who will be drafted based on roster requirements"""
    # Group by position
    by_pos = {}
    for p in players:
        pos = p["position"]
        if pos not in by_pos:
            by_pos[pos] = []
        by_pos[pos].append(p)

    # Sort each position by VORP (descending)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x["vorp"], reverse=True)

    # Select top N at each position based on roster needs
    # 7 teams, so multiply slots by 7
    drafted = []

    slots_needed = {
        "C": 7,
        "1B": 7,
        "2B": 7,
        "SS": 7,
        "3B": 7,
        "OF": 21,  # 3 per team
        "DH": 7,
        "SP": 21,  # 3 per team
        "RP": 14,  # 1 RP + 1 SP/RP flex (assuming RP)
    }

    for pos, count in slots_needed.items():
        if pos in by_pos:
            drafted.extend(by_pos[pos][:count])

    return drafted


def calculate_dollar_values(players):
    """
    Calculate TWO values:
    1. VORP Value: Theoretical "rational" value
    2. Expected Price: What they'll actually cost based on historical behavior
    """
    # Get drafted players
    drafted = select_drafted_players(players)

    # Calculate VORP-based values
    total_vorp = sum(p["vorp"] for p in drafted)
    base_salaries = len(drafted) * 1
    vorp_pool = TOTAL_BUDGET - base_salaries
    multiplier = vorp_pool / total_vorp if total_vorp > 0 else 0

    # Calculate VORP value for ALL players
    for p in players:
        dollar_value = (p["vorp"] * multiplier) + 1
        p["vorp_value"] = max(1, round(dollar_value))

    # Now rank ALL players by VORP and assign expected price
    players.sort(key=lambda x: x["vorp"], reverse=True)
    for rank, p in enumerate(players, 1):
        if rank <= 98:
            p["expected_price"] = HISTORICAL_PRICE_BY_RANK[rank]
        else:
            p["expected_price"] = 1
        p["rank"] = rank
        # Delta: positive = bargain (expected < value), negative = overpay
        p["delta"] = p["vorp_value"] - p["expected_price"]

    return players, multiplier


def print_draft_board(players):
    """Print the master draft board ranked by VORP with both valuations"""
    print("=" * 85)
    print("2026 DTFBL DRAFT BOARD")
    print("=" * 85)
    print(f"{'Rank':<5} {'Player':<22} {'Pos':<4} {'Pts':<5} {'VORP':<5} {'Value':<6} {'Expect':<7} {'Delta':<6}")
    print("-" * 85)

    for p in players[:50]:  # Top 50
        delta_str = f"+{p['delta']}" if p['delta'] > 0 else str(p['delta'])
        signal = "BUY!" if p['delta'] >= 10 else "AVOID" if p['delta'] <= -15 else ""
        print(f"{p['rank']:<5} {p['name']:<22} {p['position']:<4} {p['points']:<5} {p['vorp']:<5} ${p['vorp_value']:<5} ${p['expected_price']:<6} {delta_str:<6} {signal}")

    print("-" * 85)
    print("\nLEGEND:")
    print("  Value  = What player is WORTH (VORP-based)")
    print("  Expect = What they'll COST (based on 16 years of data)")
    print("  Delta  = Value - Expected (positive = bargain)")
    print("  BUY!   = Expected to be significantly underpriced")
    print("  AVOID  = Expected to be significantly overpriced")


def print_bargains_and_avoids(players):
    """Show the best bargains and worst overpays"""
    # Only consider draftable players (top 98)
    draftable = [p for p in players if p['rank'] <= 98]

    print("\n" + "=" * 85)
    print("STRATEGY GUIDE: BARGAINS & AVOIDS")
    print("=" * 85)

    print("\nBEST BARGAINS (high value, low expected cost):")
    print("-" * 60)
    bargains = sorted(draftable, key=lambda x: x['delta'], reverse=True)[:10]
    for p in bargains:
        print(f"  {p['name']:<22} {p['position']:<4} Value ${p['vorp_value']:<3} → Expect ${p['expected_price']:<3} = +${p['delta']} savings")

    print("\nWORST OVERPAYS (low value, high expected cost):")
    print("-" * 60)
    overpays = sorted(draftable, key=lambda x: x['delta'])[:10]
    for p in overpays:
        print(f"  {p['name']:<22} {p['position']:<4} Value ${p['vorp_value']:<3} → Expect ${p['expected_price']:<3} = ${p['delta']} overpay")


def print_by_position(players):
    """Print values by position for position-specific targeting"""
    by_pos = {}
    for p in players:
        pos = p["position"]
        if pos not in by_pos:
            by_pos[pos] = []
        by_pos[pos].append(p)

    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x["vorp"], reverse=True)

    print("\n" + "=" * 85)
    print("BY POSITION (sorted by VORP)")
    print("=" * 85)

    for pos in ["C", "1B", "2B", "SS", "3B", "OF", "DH", "SP", "RP"]:
        if pos in by_pos:
            print(f"\n{pos} (Replacement: {REPLACEMENT_LEVELS[pos]} pts)")
            print("-" * 70)
            for p in by_pos[pos][:8]:  # Top 8 at each position
                delta_str = f"+{p['delta']}" if p['delta'] > 0 else str(p['delta'])
                print(f"  #{p['rank']:<3} {p['name']:<22} {p['points']} pts  Val ${p['vorp_value']:<3} Exp ${p['expected_price']:<3} ({delta_str})")


if __name__ == "__main__":
    print("DTFBL 2026 DRAFT VALUES")
    print("Based on ATC Projections + 16 Years of Historical Pricing")
    print("=" * 85)
    print()

    # Calculate all players
    players = calculate_all_players()

    # Calculate both valuations
    players, multiplier = calculate_dollar_values(players)

    # Print draft board
    print_draft_board(players)

    # Print bargains and avoids
    print_bargains_and_avoids(players)

    # Print by position
    print_by_position(players)
