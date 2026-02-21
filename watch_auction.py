#!/usr/bin/env python3
"""
Automated Mock Auction - Watch AI opponents draft against each other
FIXED: Ensures owners spend their money properly + roster enforcement
"""

import json
import random

# PLAYER VALUES - Calibrated to historical DTFBL auction data
# Historical max: $91, top 50 avg: $76, overall avg: $19.59
# Only 13 players ever went $81+ in 16 years of drafts
PLAYER_VALUES = {
    # Catchers - scarce position, elite catchers valuable
    "William Contreras": 55,  # Elite C
    "Will Smith": 48,
    "Willson Contreras": 45,
    "J.T. Realmuto": 40,
    "Gabriel Moreno": 28,
    "Travis d'Arnaud": 18,
    "Patrick Bailey": 15,
    "Yasmani Grandal": 12,
    "Austin Nola": 8,
    "Tucker Barnhart": 3,
    "Carson Kelly": 5,
    "Elias Diaz": 4,

    # First Base - deep position, compressed value
    "Matt Olson": 38,
    "Pete Alonso": 35,
    "Bryce Harper": 45,  # MVP caliber
    "Freddie Freeman": 42,
    "Christian Walker": 22,
    "Rhys Hoskins": 15,
    "Josh Bell": 8,
    "LaMonte Wade Jr.": 2,
    "Cody Bellinger": 28,
    "Rowdy Tellez": 5,
    "CJ Cron": 3,
    "Jake Bauers": 1,
    "Brandon Belt": 2,

    # Second Base
    "Ketel Marte": 50,
    "Ozzie Albies": 42,
    "Brice Turang": 18,
    "Bryson Stott": 22,
    "Brandon Lowe": 18,
    "Jake Cronenworth": 15,
    "Luis Arraez": 25,
    "Gavin Lux": 12,
    "Brendan Rodgers": 8,
    "Nico Hoerner": 28,
    "Jonathan India": 20,
    "Grae Kessinger": 2,
    "David Fry": 12,

    # Shortstop - premium position
    "Elly De La Cruz": 78,  # Elite young talent
    "Francisco Lindor": 65,
    "Trea Turner": 58,
    "Willy Adames": 45,
    "Geraldo Perdomo": 18,
    "CJ Abrams": 35,
    "Dansby Swanson": 32,
    "Bo Bichette": 38,
    "Ezequiel Tovar": 25,
    "Ha-Seong Kim": 18,
    "Mookie Betts": 70,  # Elite OF/SS
    "Nick Ahmed": 2,
    "Paul DeJong": 4,

    # Third Base
    "Rafael Devers": 55,
    "Manny Machado": 48,
    "Austin Riley": 45,
    "Alex Bregman": 42,
    "Matt Chapman": 32,
    "Nolan Arenado": 35,
    "Alec Bohm": 28,
    "Spencer Steer": 22,
    "Max Muncy": 25,
    "Ryan McMahon": 18,
    "Ke'Bryan Hayes": 15,
    "Eugenio Suarez": 12,
    "Christopher Morel": 10,
    "Patrick Wisdom": 5,

    # Outfield - 3 slots needed, good depth
    "Juan Soto": 85,  # Top 3 player
    "Kyle Schwarber": 45,
    "Ronald Acuna Jr.": 75,  # Elite when healthy
    "Kyle Tucker": 55,
    "Fernando Tatis Jr.": 60,
    "Corbin Carroll": 50,
    "Pete Crow-Armstrong": 22,
    "Jackson Merrill": 28,
    "Jackson Chourio": 32,
    "Ian Happ": 25,
    "Michael Harris II": 35,
    "Andy Pages": 15,
    "Bryan De La Cruz": 12,
    "Jesse Winker": 8,
    "Lars Nootbaar": 10,
    "Brandon Marsh": 8,
    "Teoscar Hernandez": 28,
    "Lourdes Gurriel Jr.": 18,
    "Randy Arozarena": 25,
    "TJ Friedl": 15,
    "Jake McCarthy": 10,
    "Jordan Walker": 18,
    "Mark Canha": 6,
    "Mike Yastrzemski": 8,

    # DH
    "Shohei Ohtani": 88,  # Generational talent (historical: $88 in 2025)
    "Marcell Ozuna": 32,
    "Jorge Soler": 15,
    "JD Martinez": 12,
    "Wilmer Flores": 5,
    "Daniel Vogelbach": 3,
    "Nick Castellanos": 18,

    # Starting Pitchers - wins are +12!
    "Paul Skenes": 45,  # Elite young arm
    "Logan Webb": 35,
    "Cristopher Sanchez": 28,
    "Chris Sale": 32,
    "Jesus Luzardo": 30,
    "Yoshinobu Yamamoto": 35,
    "Hunter Greene": 28,
    "Freddy Peralta": 25,
    "Zac Gallen": 30,
    "Spencer Strider": 35,  # When healthy
    "Tyler Glasnow": 30,
    "Yu Darvish": 22,
    "Ranger Suarez": 20,
    "Shota Imanaga": 22,
    "Dylan Cease": 20,
    "Sonny Gray": 18,
    "Mitch Keller": 15,
    "Zack Wheeler": 35,
    "Blake Snell": 25,
    "Miles Mikolas": 8,
    "Joe Musgrove": 22,
    "Adam Wainwright": 3,
    "MacKenzie Gore": 15,
    "Merrill Kelly": 12,

    # Relief Pitchers - saves are +8, elite closers valuable
    "Ryan Helsley": 45,
    "Josh Hader": 40,
    "Edwin Diaz": 35,
    "Raisel Iglesias": 28,
    "Robert Suarez": 25,
    "Tanner Scott": 25,
    "Devin Williams": 32,
    "Camilo Doval": 28,
    "Kenley Jansen": 22,
    "Alexis Diaz": 22,
    "A.J. Minter": 18,
    "Yuki Matsui": 20,
    "Evan Phillips": 18,
    "Daniel Hudson": 8,
    "Jeff Hoffman": 12,
    "Pierce Johnson": 15,
}

# Default value for unknown players
DEFAULT_PLAYER_VALUE = 10

def get_player_value(player_name):
    """Get player's auction value, with fallback for unknown players"""
    return PLAYER_VALUES.get(player_name, DEFAULT_PLAYER_VALUE)


# Roster slot requirements (14 players total)
ROSTER_SLOTS = {
    "C": 1,
    "1B": 1,
    "2B": 1,
    "SS": 1,
    "3B": 1,
    "OF": 3,
    "DH": 1,
    "SP": 3,
    "RP": 1,
    "SP/RP": 1,  # Flex slot - can be filled by SP or RP
}


class AIOwner:
    """AI opponent that mimics historical behavior"""

    def __init__(self, name, budget=260, profile=None):
        self.name = name
        self.budget = budget
        self.roster = []
        self.roster_size = 14
        self.profile = profile or {}
        # Track how many of each position have been filled
        self.position_counts = {pos: 0 for pos in ROSTER_SLOTS}

    def needs_players(self):
        return len(self.roster) < self.roster_size

    def spots_left(self):
        return self.roster_size - len(self.roster)

    def can_bid(self, amount):
        return self.budget - amount >= self.spots_left() - 1

    def needs_position(self, position):
        """Check if this owner still needs a player at this position"""
        pos = position.upper().strip()
        if pos == "SP / RP":
            pos = "SP/RP"

        # Direct slot available?
        if pos in self.position_counts:
            if self.position_counts[pos] < ROSTER_SLOTS[pos]:
                return True

        # SP or RP can also fill the SP/RP flex slot
        if pos in ("SP", "RP"):
            if self.position_counts["SP/RP"] < ROSTER_SLOTS["SP/RP"]:
                if self.position_counts[pos] >= ROSTER_SLOTS[pos]:
                    return True

        return False

    def get_slot_for_position(self, position):
        """Determine which roster slot a position fills"""
        pos = position.upper().strip()
        if pos == "SP / RP":
            pos = "SP/RP"

        if pos in self.position_counts:
            if self.position_counts[pos] < ROSTER_SLOTS[pos]:
                return pos

        if pos in ("SP", "RP"):
            if self.position_counts["SP/RP"] < ROSTER_SLOTS["SP/RP"]:
                return "SP/RP"

        return None

    def add_player(self, player_name, price, position):
        slot = self.get_slot_for_position(position)
        if not slot:
            # No valid slot - this shouldn't happen if bidding logic is correct
            # but guard against it anyway
            return False
        self.position_counts[slot] += 1
        self.roster.append({
            'player': player_name,
            'price': price,
            'position': position,
            'slot': slot
        })
        self.budget -= price
        return True

    def positions_needed(self):
        """Return list of positions this owner still needs"""
        needed = []
        for pos, max_count in ROSTER_SLOTS.items():
            if self.position_counts[pos] < max_count:
                needed.append(pos)
        return needed

    def should_bid(self, player_name, player_position, current_price, total_picks_so_far):
        """Decide if AI should enter bidding based on player value"""

        if not self.can_bid(current_price + 1) or not self.needs_players():
            return False

        # ROSTER ENFORCEMENT: Don't bid if we don't need this position
        if not self.needs_position(player_position):
            return False

        # Get player's actual value
        player_value = get_player_value(player_name)

        # Calculate target spend per remaining slot
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        total_slots = 14 * 7  # 7 teams * 14 slots = 98 picks
        pct_complete = total_picks_so_far / total_slots

        # Get position preference (owner's historical tendency)
        # Positive = likes this position, negative = avoids this position
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)

        # Premium affects INTEREST, not value - owners who like a position bid more often
        # Cap the adjustment to prevent extreme behavior
        position_interest_modifier = max(-0.3, min(0.3, premium_pct / 100))

        # Base interest on price vs value
        if current_price < player_value * 0.7:
            interest = 0.85  # Great value
        elif current_price < player_value * 0.9:
            interest = 0.70  # Good value
        elif current_price < player_value:
            interest = 0.55  # Fair value
        elif current_price < player_value * 1.1:
            interest = 0.30  # Slight overpay
        else:
            interest = 0.10  # Too expensive

        # Apply position preference (capped modifier)
        interest += position_interest_modifier

        # Late auction budget pressure
        if pct_complete >= 0.7 and target_per_slot >= 15 and current_price < target_per_slot:
            interest = max(interest, 0.70)

        if pct_complete >= 0.85 and target_per_slot >= 10:
            interest = max(interest, 0.80)

        interest *= random.uniform(0.9, 1.1)
        return random.random() < max(0.05, min(interest, 0.90))
    
    def get_max_bid(self, player_name, player_position, current_price, total_picks_so_far):
        """Determine maximum AI willing to pay based on player value"""

        spots_left = self.spots_left()
        money_left = self.budget

        # Last pick - spend entire remaining budget (can't carry it over)
        if spots_left == 1:
            return money_left

        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        # Get player's actual value
        player_value = get_player_value(player_name)

        # Get owner's position preference - small adjustment, not multiplier
        # Historical max is $91, so we cap any bonus to prevent exceeding that
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)

        # Position preference adds a SMALL bonus (max +15% for extreme cases)
        # This reflects that some owners slightly overpay for positions they like
        position_bonus = player_value * max(-0.10, min(0.15, premium_pct / 200))

        total_slots = 14 * 7
        pct_complete = total_picks_so_far / total_slots

        # Base max bid on player value with variance
        if pct_complete < 0.4:
            # Early auction: conservative
            max_price = player_value * random.uniform(0.85, 1.05) + position_bonus
        elif pct_complete < 0.7:
            # Mid auction: blend with budget pressure
            max_price = player_value * random.uniform(0.90, 1.10) + position_bonus
            if target_per_slot > player_value:
                max_price = max(max_price, target_per_slot * 0.85)
        else:
            # Late auction: budget pressure matters more
            max_price = max(player_value, target_per_slot * 0.9) * random.uniform(0.95, 1.10)

        # Very late: spend money
        if pct_complete >= 0.85 and target_per_slot >= 10:
            max_price = max(max_price, target_per_slot)

        # Cap at historical max ($91) unless late auction forces spending
        if pct_complete < 0.8:
            max_price = min(max_price, 91)

        max_affordable = self.budget - self.spots_left() + 1
        max_price = min(int(max_price), max_affordable)
        max_price = max(max_price, current_price + 1)

        return max_price
    
    def decide_bid_increment(self, current_price, max_bid):
        """Decide how much to increase bid"""
        # Last pick - jump straight to max bid to spend entire budget
        if self.spots_left() == 1:
            return max_bid - current_price

        gap = max_bid - current_price

        if gap > 20:
            return random.choice([2, 3, 5])
        elif gap > 5:
            return random.choice([1, 2])
        else:
            return 1
    
    def nominate_player(self, drafted_players=None):
        """Nominate a player at a position the AI still needs"""
        if drafted_players is None:
            drafted_players = set()

        # Player pool organized by position (NL-only players)
        # Need 98 total (14 players × 7 teams)
        player_pool = {
            "C": ["J.T. Realmuto", "William Contreras", "Willson Contreras", "Travis d'Arnaud",
                  "Gabriel Moreno", "Will Smith", "Patrick Bailey", "Yasmani Grandal",
                  "Austin Nola", "Tucker Barnhart", "Carson Kelly", "Elias Diaz"],
            "1B": ["Freddie Freeman", "Pete Alonso", "Matt Olson", "Bryce Harper",
                   "Cody Bellinger", "Christian Walker", "Josh Bell", "LaMonte Wade Jr.",
                   "Rowdy Tellez", "CJ Cron", "Jake Bauers", "Brandon Belt"],
            "2B": ["Ketel Marte", "Ozzie Albies", "Luis Arraez", "Gavin Lux",
                   "Brendan Rodgers", "Jake Cronenworth", "Brandon Lowe", "Bryson Stott",
                   "Nico Hoerner", "Jonathan India", "Grae Kessinger", "David Fry"],
            "SS": ["Francisco Lindor", "Trea Turner", "Elly De La Cruz",
                   "Dansby Swanson", "CJ Abrams", "Ha-Seong Kim", "Ezequiel Tovar",
                   "Willy Adames", "Geraldo Perdomo", "Bo Bichette", "Nick Ahmed", "Paul DeJong"],
            "3B": ["Manny Machado", "Nolan Arenado", "Austin Riley", "Ryan McMahon",
                   "Matt Chapman", "Ke'Bryan Hayes", "Alec Bohm", "Max Muncy",
                   "Rafael Devers", "Eugenio Suarez", "Christopher Morel", "Patrick Wisdom"],
            "OF": ["Juan Soto", "Fernando Tatis Jr.", "Kyle Tucker", "Corbin Carroll",
                   "Ronald Acuna Jr.", "Mookie Betts", "Ian Happ", "Jackson Chourio",
                   "Lars Nootbaar", "Bryan De La Cruz", "Brandon Marsh", "Michael Harris II",
                   "Kyle Schwarber", "Pete Crow-Armstrong", "Jackson Merrill", "Andy Pages",
                   "Teoscar Hernandez", "Lourdes Gurriel Jr.", "Randy Arozarena", "TJ Friedl",
                   "Jake McCarthy", "Jordan Walker", "Mark Canha", "Mike Yastrzemski"],
            "DH": ["Shohei Ohtani", "Marcell Ozuna", "Jesse Winker",
                   "Spencer Steer", "JD Martinez", "Jorge Soler", "Rhys Hoskins",
                   "Wilmer Flores", "Daniel Vogelbach", "Nick Castellanos"],
            "SP": ["Zack Wheeler", "Spencer Strider", "Chris Sale", "Paul Skenes",
                   "Logan Webb", "Shota Imanaga", "Yu Darvish", "Blake Snell",
                   "Ranger Suarez", "Dylan Cease", "Miles Mikolas", "Sonny Gray",
                   "Zac Gallen", "Tyler Glasnow", "Mitch Keller", "Hunter Greene",
                   "Freddy Peralta", "Cristopher Sanchez", "Jesus Luzardo", "Yoshinobu Yamamoto",
                   "Joe Musgrove", "Adam Wainwright", "MacKenzie Gore", "Merrill Kelly"],
            "RP": ["Edwin Diaz", "Ryan Helsley", "Josh Hader", "Camilo Doval",
                   "Alexis Diaz", "Robert Suarez", "Tanner Scott", "A.J. Minter",
                   "Devin Williams", "Kenley Jansen", "Raisel Iglesias", "Daniel Hudson",
                   "Yuki Matsui", "Jeff Hoffman", "Pierce Johnson", "Evan Phillips"],
        }

        # Get positions we still need
        needed = self.positions_needed()

        # Map SP/RP flex to actual pitcher positions
        available_positions = []
        for pos in needed:
            if pos == "SP/RP":
                available_positions.extend(["SP", "RP"])
            else:
                available_positions.append(pos)

        # Remove duplicates while preserving some order
        available_positions = list(dict.fromkeys(available_positions))

        if not available_positions:
            available_positions = list(player_pool.keys())

        # Try to find an available player at a position we need
        # Prefer higher-value players (more realistic - you want elite players)
        random.shuffle(available_positions)

        best_player = None
        best_position = None
        best_value = -1

        for position in available_positions:
            available_players = [p for p in player_pool.get(position, [])
                                 if p not in drafted_players]
            for player in available_players:
                value = get_player_value(player)
                # Add some randomness so it's not always the top player
                adjusted_value = value * random.uniform(0.7, 1.3)
                if adjusted_value > best_value:
                    best_value = adjusted_value
                    best_player = player
                    best_position = position

        if best_player:
            return (best_player, best_position)

        # Fallback: any available player
        for position in player_pool:
            available_players = [p for p in player_pool[position]
                                 if p not in drafted_players]
            if available_players:
                return (random.choice(available_players), position)

        return ("Unknown Player", "DH")


def run_auto_auction():
    """Run a fully automated auction"""
    
    # Load profiles
    with open('owner_profiles.json', 'r') as f:
        profiles = json.load(f)
    
    # Create all AI owners
    owners = []
    for name, profile in profiles.items():
        owners.append(AIOwner(name, profile=profile))
    
    print("="*80)
    print("AUTOMATED MOCK AUCTION - WATCH AI OPPONENTS")
    print("="*80)
    print("\nBased on 16 years of historical behavior")
    print("FIXED: Ensures owners spend their money properly\n")
    
    # Randomize nomination order
    random.shuffle(owners)
    
    print("Nomination order:")
    for i, owner in enumerate(owners, 1):
        print(f"  {i}. {owner.name}")
    
    print("\n" + "="*80)

    auction_round = 0
    nomination_index = 0
    drafted_players = set()  # Track who's been drafted

    while any(o.needs_players() for o in owners) and auction_round < 98:
        # Get next nominator
        nominator = None
        attempts = 0
        while attempts < len(owners):
            candidate = owners[nomination_index]
            nomination_index = (nomination_index + 1) % len(owners)
            
            if candidate.needs_players():
                nominator = candidate
                break
            attempts += 1
        
        if not nominator:
            break
        
        auction_round += 1

        # Nominate (pass drafted_players to avoid duplicates)
        player_name, position = nominator.nominate_player(drafted_players)
        
        if auction_round % 10 == 0 or auction_round <= 5:
            print(f"\n{'='*80}")
            print(f"PICK #{auction_round}: {nominator.name} nominates {player_name} ({position})")
            print('='*80)
        
        current_price = 1
        current_bidder = None
        
        # Collect interested bidders with their max bids
        bidders = {}
        for owner in owners:
            if owner.should_bid(player_name, position, current_price, auction_round):
                max_bid = owner.get_max_bid(player_name, position, current_price, auction_round)
                if max_bid > current_price:
                    bidders[owner] = max_bid

        # Proper bidding war - owners keep bidding until price exceeds their max
        bid_count = 0
        last_bidder = None
        stalled_rounds = 0

        while len(bidders) > 0:
            # Find owners who can still bid (price below their max)
            active_bidders = [(o, m) for o, m in bidders.items()
                              if m > current_price and o.can_bid(current_price + 1) and o != last_bidder]

            if not active_bidders:
                break

            # Pick next bidder (highest max bid gets priority, with some randomness)
            active_bidders.sort(key=lambda x: x[1] + random.uniform(0, 5), reverse=True)
            owner, max_bid = active_bidders[0]

            # Calculate bid increment
            increment = owner.decide_bid_increment(current_price, max_bid)
            new_bid = min(current_price + increment, max_bid)

            if owner.can_bid(new_bid):
                current_price = new_bid
                current_bidder = owner
                last_bidder = owner
                bid_count += 1
                stalled_rounds = 0

                if auction_round % 10 == 0 or auction_round <= 5:
                    print(f"  {owner.name} bids ${new_bid}")

                # Remove bidders who can't compete anymore
                bidders = {o: m for o, m in bidders.items() if m > current_price}
            else:
                # Owner can't afford, remove them
                del bidders[owner]
                stalled_rounds += 1

            # Safety valve
            if stalled_rounds > 10 or bid_count > 50:
                break
        
        # Finalize - if no one bid, nominator gets player (if they need the position)
        if not current_bidder and nominator.can_bid(current_price) and nominator.needs_position(position):
            current_bidder = nominator
            spots = nominator.spots_left()
            if spots == 1:
                # Last pick - spend entire remaining budget (can't carry it over)
                current_price = nominator.budget
            else:
                # Not last pick and no competition - take at $1 (save money for contested positions)
                current_price = 1
            if auction_round % 10 == 0 or auction_round <= 5:
                print(f"  (no bids) {nominator.name} takes at ${current_price}")

        if current_bidder:
            if auction_round % 10 == 0 or auction_round <= 5:
                print(f"  → SOLD to {current_bidder.name} for ${current_price}")
            current_bidder.add_player(player_name, current_price, position)
            drafted_players.add(player_name)  # Track as drafted
        
        # Show standings periodically
        if auction_round % 14 == 0:
            print(f"\n{'─'*80}")
            print(f"After {auction_round} picks:")
            for owner in sorted(owners, key=lambda x: x.budget, reverse=True):
                avg_per_slot = owner.budget / owner.spots_left() if owner.spots_left() > 0 else 0
                print(f"  {owner.name:20s} | Roster: {len(owner.roster):2d}/14 | "
                      f"Budget: ${owner.budget:3d} | Avg/slot: ${avg_per_slot:.1f}")
    
    # Final results
    print(f"\n\n{'='*80}")
    print("FINAL RESULTS")
    print('='*80)

    # Define position order for display
    position_order = ["C", "1B", "2B", "SS", "3B", "OF", "DH", "SP", "RP", "SP/RP"]

    for owner in sorted(owners, key=lambda x: 260 - x.budget, reverse=True):
        print(f"\n{owner.name}")
        print(f"  Budget used: ${260 - owner.budget} | Remaining: ${owner.budget}")
        print(f"  Roster ({len(owner.roster)}/14):")
        print(f"  {'Slot':<6} {'Pos':<4} {'Player':<25} {'Price':>6}")
        print(f"  {'-'*45}")

        # Sort roster by position order, then by price within position
        def sort_key(pick):
            slot = pick.get('slot') or pick['position']
            try:
                pos_idx = position_order.index(slot)
            except ValueError:
                pos_idx = 99
            return (pos_idx, -pick['price'])

        for pick in sorted(owner.roster, key=sort_key):
            slot = pick.get('slot') or pick['position']
            print(f"  {slot:<6} {pick['position']:<4} {pick['player']:<25} ${pick['price']:>5}")

        print(f"  {'-'*45}")
        print(f"  {'TOTAL':<36} ${sum(p['price'] for p in owner.roster):>5}")


if __name__ == '__main__':
    print("\nRunning automated auction...")
    print("(This will take ~30 seconds)\n")
    run_auto_auction()
    
    print("\n\n" + "="*80)
    print("To practice interactively:")
    print("  python mock_auction.py")
    print("="*80)
