#!/usr/bin/env python3
"""
DTFBL Player Values Calculator
Based on 2026 ATC Projections from FanGraphs
Calculates fantasy points and VORP-based auction values
"""

# Scoring system
# Hitters: 1B(+1), 2B(+2), 3B(+4), HR(+4), R(+1), RBI(+1), SB(+1), BB(+1), E(-1)
# Pitchers: W(+12), L(-3), SV(+8), K(+1), BB(-1), CG(+5), ShO(+5), QS(+2)

# Replacement levels (from user's VORP analysis)
REPLACEMENT_LEVELS = {
    "C": 170,
    "1B": 399,
    "2B": 299,
    "SS": 211,
    "3B": 225,
    "OF": 352,
    "DH": 399,  # Use 1B replacement level
    "SP": 202,
    "RP": 131,
}

# VORP to dollars conversion
DOLLARS_PER_VORP = 0.3206
BASE_SALARY = 1

def calc_hitter_points(singles, doubles, triples, hr, runs, rbi, sb, bb):
    """Calculate fantasy points for a hitter"""
    return (singles * 1) + (doubles * 2) + (triples * 4) + (hr * 4) + runs + rbi + sb + bb

def calc_pitcher_points(wins, losses, saves, strikeouts, walks, ip):
    """Calculate fantasy points for a pitcher"""
    # Estimate quality starts: roughly 60% of starts for good pitchers
    # A start is roughly every 5 days, so starts ≈ IP / 6
    estimated_starts = ip / 6
    estimated_qs = estimated_starts * 0.55  # Conservative QS rate

    points = (wins * 12) + (losses * -3) + (saves * 8) + strikeouts + (walks * -1) + (estimated_qs * 2)
    return points

def calc_dollar_value(points, position):
    """Calculate auction dollar value from points"""
    replacement = REPLACEMENT_LEVELS.get(position, 300)
    vorp = points - replacement
    if vorp < 0:
        return 1  # Minimum $1
    dollars = (vorp * DOLLARS_PER_VORP) + BASE_SALARY
    return max(1, round(dollars))

# 2026 ATC Projections - Hitters
# Format: (name, position, singles, doubles, triples, hr, runs, rbi, sb, bb)
HITTER_PROJECTIONS = [
    # Elite tier
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
    # Additional key players (estimated based on typical production)
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
]

# 2026 ATC Projections - Pitchers
# Format: (name, position, wins, losses, saves, strikeouts, walks, ip)
PITCHER_PROJECTIONS = [
    # Elite starters
    ("Paul Skenes", "SP", 12, 8, 0, 221, 45, 184),
    ("Logan Webb", "SP", 13, 10, 0, 183, 44, 193),
    ("Cristopher Sanchez", "SP", 12, 7, 0, 179, 45, 185),
    ("Yoshinobu Yamamoto", "SP", 12, 7, 0, 175, 47, 160),
    ("Chris Sale", "SP", 11, 6, 0, 187, 39, 152),
    ("Jesus Luzardo", "SP", 12, 9, 0, 191, 53, 173),
    ("Hunter Greene", "SP", 10, 8, 0, 198, 53, 164),
    ("Zack Wheeler", "SP", 9, 5, 0, 143, 33, 124),
    ("Freddy Peralta", "SP", 12, 9, 0, 183, 60, 164),
    ("Spencer Strider", "SP", 10, 6, 0, 180, 45, 145),  # Estimated post-injury
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
    # Relievers (estimated save totals for closers)
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
]


def calculate_all_values():
    """Calculate fantasy points and dollar values for all players"""
    players = {}

    # Process hitters
    for name, pos, s, d, t, hr, r, rbi, sb, bb in HITTER_PROJECTIONS:
        points = calc_hitter_points(s, d, t, hr, r, rbi, sb, bb)
        dollars = calc_dollar_value(points, pos)
        players[name] = {
            "position": pos,
            "points": round(points),
            "dollars": dollars,
        }

    # Process pitchers
    for name, pos, w, l, sv, k, bb, ip in PITCHER_PROJECTIONS:
        points = calc_pitcher_points(w, l, sv, k, bb, ip)
        dollars = calc_dollar_value(points, pos)
        players[name] = {
            "position": pos,
            "points": round(points),
            "dollars": dollars,
        }

    return players


def print_values_by_position():
    """Print all player values grouped by position"""
    players = calculate_all_values()

    # Group by position
    by_pos = {}
    for name, data in players.items():
        pos = data["position"]
        if pos not in by_pos:
            by_pos[pos] = []
        by_pos[pos].append((name, data["points"], data["dollars"]))

    # Sort each position by dollars
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x[2], reverse=True)

    # Print
    for pos in ["C", "1B", "2B", "SS", "3B", "OF", "DH", "SP", "RP"]:
        if pos in by_pos:
            print(f"\n{'='*50}")
            print(f"{pos} (Replacement: {REPLACEMENT_LEVELS[pos]} pts)")
            print(f"{'='*50}")
            for name, pts, dollars in by_pos[pos]:
                print(f"  ${dollars:3d}  {name:25s}  ({pts} pts)")


def export_player_values_dict():
    """Export as a simple {name: dollar_value} dict for the auction sim"""
    players = calculate_all_values()
    return {name: data["dollars"] for name, data in players.items()}


if __name__ == "__main__":
    print("DTFBL 2026 Player Values")
    print("Based on ATC Projections + VORP Analysis")
    print_values_by_position()

    print("\n\n" + "="*50)
    print("PLAYER_VALUES dict for auction sim:")
    print("="*50)
    values = export_player_values_dict()
    # Sort by value descending
    sorted_vals = sorted(values.items(), key=lambda x: x[1], reverse=True)
    print("PLAYER_VALUES = {")
    for name, val in sorted_vals[:20]:
        print(f'    "{name}": {val},')
    print("    # ... etc")
    print("}")
