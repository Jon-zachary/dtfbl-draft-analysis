#!/usr/bin/env python3
"""
DTFBL Mock Auction Simulator
Proper nomination rotation + proper budget spending + roster enforcement
Uses VORP-based player values from 2026 ATC projections
"""

import json
import random

# PLAYER VALUES - Based on 2026 ATC Projections + VORP analysis
# Formula: (Projected Points - Replacement Level) * $0.3206 + $1
PLAYER_VALUES = {
    # Catchers (Replacement: 170 pts) - SCARCE!
    "William Contreras": 92, "Will Smith": 73, "Willson Contreras": 72,
    "J.T. Realmuto": 60, "Gabriel Moreno": 47, "Travis d'Arnaud": 45,
    "Patrick Bailey": 41, "Yasmani Grandal": 38, "Austin Nola": 20,
    "Tucker Barnhart": 10, "Carson Kelly": 15, "Elias Diaz": 12,

    # First Base (Replacement: 399 pts) - DEEP
    "Matt Olson": 47, "Pete Alonso": 42, "Bryce Harper": 34,
    "Freddie Freeman": 30, "Christian Walker": 28, "Rhys Hoskins": 18,
    "Josh Bell": 10, "LaMonte Wade Jr.": 1, "Cody Bellinger": 33,
    "Rowdy Tellez": 8, "CJ Cron": 5, "Jake Bauers": 3, "Brandon Belt": 5,

    # Second Base (Replacement: 299 pts)
    "Ketel Marte": 70, "Ozzie Albies": 56, "Brice Turang": 52,
    "Bryson Stott": 37, "Brandon Lowe": 33, "Jake Cronenworth": 31,
    "Luis Arraez": 24, "Gavin Lux": 20, "Brendan Rodgers": 15,
    "Nico Hoerner": 45, "Jonathan India": 35, "Grae Kessinger": 5, "David Fry": 25,

    # Shortstop (Replacement: 211 pts) - SCARCE!
    "Elly De La Cruz": 101, "Francisco Lindor": 91, "Trea Turner": 89,
    "Willy Adames": 89, "Geraldo Perdomo": 81, "CJ Abrams": 80,
    "Dansby Swanson": 78, "Bo Bichette": 73, "Ezequiel Tovar": 67,
    "Ha-Seong Kim": 56, "Mookie Betts": 43, "Nick Ahmed": 8, "Paul DeJong": 12,

    # Third Base (Replacement: 225 pts)
    "Rafael Devers": 99, "Manny Machado": 81, "Austin Riley": 79,
    "Alex Bregman": 77, "Matt Chapman": 75, "Nolan Arenado": 75,
    "Alec Bohm": 72, "Spencer Steer": 67, "Max Muncy": 65,
    "Ryan McMahon": 64, "Ke'Bryan Hayes": 49, "Eugenio Suarez": 40,
    "Christopher Morel": 28, "Patrick Wisdom": 18,

    # Outfield (Replacement: 352 pts)
    "Juan Soto": 93, "Kyle Schwarber": 72, "Ronald Acuna Jr.": 65,
    "Kyle Tucker": 64, "Fernando Tatis Jr.": 62, "Corbin Carroll": 62,
    "Pete Crow-Armstrong": 39, "Jackson Merrill": 37, "Jackson Chourio": 35,
    "Ian Happ": 32, "Michael Harris II": 30, "Andy Pages": 25,
    "Bryan De La Cruz": 20, "Jesse Winker": 16, "Lars Nootbaar": 14,
    "Brandon Marsh": 13, "Teoscar Hernandez": 38, "Lourdes Gurriel Jr.": 28,
    "Randy Arozarena": 35, "TJ Friedl": 22, "Jake McCarthy": 18,
    "Jordan Walker": 25, "Mark Canha": 12, "Mike Yastrzemski": 15,

    # DH (Replacement: 399 pts)
    "Shohei Ohtani": 91, "Marcell Ozuna": 35, "Jorge Soler": 17,
    "JD Martinez": 14, "Wilmer Flores": 8, "Daniel Vogelbach": 5,
    "Nick Castellanos": 22,

    # Starting Pitchers (Replacement: 202 pts)
    "Paul Skenes": 42, "Logan Webb": 33, "Cristopher Sanchez": 30,
    "Chris Sale": 29, "Jesus Luzardo": 28, "Yoshinobu Yamamoto": 26,
    "Hunter Greene": 23, "Freddy Peralta": 23, "Zac Gallen": 22,
    "Spencer Strider": 21, "Tyler Glasnow": 21, "Yu Darvish": 15,
    "Ranger Suarez": 14, "Shota Imanaga": 14, "Dylan Cease": 13,
    "Sonny Gray": 13, "Mitch Keller": 13, "Zack Wheeler": 9,
    "Blake Snell": 9, "Miles Mikolas": 3, "Joe Musgrove": 18,
    "Adam Wainwright": 5, "MacKenzie Gore": 15, "Merrill Kelly": 12,

    # Relief Pitchers (Replacement: 131 pts) - CLOSERS VALUABLE!
    "Ryan Helsley": 94, "Josh Hader": 87, "Edwin Diaz": 80,
    "Raisel Iglesias": 74, "Robert Suarez": 73, "Tanner Scott": 73,
    "Devin Williams": 73, "Camilo Doval": 66, "Kenley Jansen": 63,
    "Alexis Diaz": 61, "A.J. Minter": 55, "Yuki Matsui": 54,
    "Evan Phillips": 45, "Daniel Hudson": 21, "Jeff Hoffman": 27,
    "Pierce Johnson": 40,
}

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


class Owner:
    """Represents an auction participant (human or AI)"""
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
        # Normalize position name
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
                # Check if primary slots are full
                if self.position_counts[pos] >= ROSTER_SLOTS[pos]:
                    return True

        return False

    def get_slot_for_position(self, position):
        """Determine which roster slot a position fills"""
        pos = position.upper().strip()
        if pos == "SP / RP":
            pos = "SP/RP"

        # Try direct slot first
        if pos in self.position_counts:
            if self.position_counts[pos] < ROSTER_SLOTS[pos]:
                return pos

        # SP or RP overflow to SP/RP flex slot
        if pos in ("SP", "RP"):
            if self.position_counts["SP/RP"] < ROSTER_SLOTS["SP/RP"]:
                return "SP/RP"

        return None

    def add_player(self, player_name, price, position):
        slot = self.get_slot_for_position(position)
        if not slot:
            # No valid slot - this shouldn't happen if bidding logic is correct
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


class AIOwner(Owner):
    """AI opponent that mimics historical behavior"""

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

        total_slots = 14 * 8  # 8 owners (7 AI + 1 human)
        pct_complete = total_picks_so_far / total_slots

        # Get position preference (owner's historical tendency)
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)

        # Adjust player value by owner's position preference
        adjusted_value = player_value * (1 + premium_pct / 100)

        # If player is worth more than current price, be interested
        if current_price < adjusted_value * 0.9:
            interest = 0.85  # Good value - high interest
        elif current_price < adjusted_value:
            interest = 0.65  # Fair value - moderate interest
        elif current_price < adjusted_value * 1.1:
            interest = 0.35  # Slight overpay - lower interest
        else:
            interest = 0.15  # Too expensive - minimal interest

        # Late auction budget pressure: bid more aggressively to spend money
        if pct_complete >= 0.7 and target_per_slot >= 15 and current_price < target_per_slot:
            interest = max(interest, 0.75)

        if pct_complete >= 0.85 and target_per_slot >= 10:
            interest = max(interest, 0.85)

        interest *= random.uniform(0.9, 1.1)
        return random.random() < min(interest, 0.95)
    
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

        # Get owner's position preference
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)

        # Adjust value by owner's historical tendency
        adjusted_value = player_value * (1 + premium_pct / 100)

        total_slots = 14 * 8
        pct_complete = total_picks_so_far / total_slots

        # Base max bid on adjusted player value with some variance
        if pct_complete < 0.4:
            max_price = adjusted_value * random.uniform(0.85, 1.05)
        elif pct_complete < 0.7:
            budget_factor = target_per_slot / 20
            max_price = adjusted_value * random.uniform(0.9, 1.1) * max(1.0, budget_factor * 0.3 + 0.7)
        else:
            max_price = max(adjusted_value, target_per_slot) * random.uniform(1.0, 1.15)

        # Very late auction: ensure we spend money
        if pct_complete >= 0.85 and target_per_slot >= 10:
            max_price = max(max_price, target_per_slot * 1.1)

        max_affordable = self.budget - self.spots_left() + 1
        max_price = min(int(max_price), max_affordable)
        max_price = max(max_price, current_price + 1)

        return max_price
    
    def decide_bid_increment(self, current_price, max_bid):
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

        # Player pool organized by position (NL-only players) - expanded for 8-team league
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

        available_positions = list(dict.fromkeys(available_positions))

        if not available_positions:
            available_positions = list(player_pool.keys())

        # Prefer higher-value players (more realistic nomination behavior)
        random.shuffle(available_positions)
        best_player = None
        best_position = None
        best_value = -1

        for position in available_positions:
            available_players = [p for p in player_pool.get(position, [])
                                 if p not in drafted_players]
            for player in available_players:
                value = get_player_value(player)
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


class MockAuction:
    """Runs the mock auction with proper nomination rotation"""
    
    def __init__(self, profiles_file='owner_profiles.json'):
        with open(profiles_file, 'r') as f:
            self.profiles = json.load(f)
        
        self.owners = []
        for name, profile in self.profiles.items():
            self.owners.append(AIOwner(name, profile=profile))
        
        self.human = Owner("YOU (Practice)", budget=260)
        self.owners.append(self.human)
        
        random.shuffle(self.owners)
        self.nomination_index = 0
        self.total_picks = 0
        self.drafted_players = set()  # Track drafted players
        
    def get_next_nominator(self):
        attempts = 0
        while attempts < len(self.owners):
            nominator = self.owners[self.nomination_index]
            self.nomination_index = (self.nomination_index + 1) % len(self.owners)
            
            if nominator.needs_players():
                return nominator
            attempts += 1
        return None
    
    def display_status(self):
        print("\n" + "="*80)
        print("AUCTION STATUS")
        print("="*80)
        
        for owner in sorted(self.owners, key=lambda x: x.budget, reverse=True):
            roster_str = f"{len(owner.roster)}/{owner.roster_size}"
            budget_str = f"${owner.budget}"
            avg_per_slot = owner.budget / owner.spots_left() if owner.spots_left() > 0 else 0
            marker = " <- YOU" if owner == self.human else ""
            print(f"{owner.name:20s} | Roster: {roster_str:5s} | Budget: {budget_str:>6s} | "
                  f"$/slot: ${avg_per_slot:5.1f}{marker}")
    
    def run_bidding(self, player_name, position, nominator, opening_bid=1):
        print(f"\n{'='*80}")
        print(f"{nominator.name} nominates: {player_name} ({position}) - Opening: ${opening_bid}")
        print('='*80)
        
        current_price = opening_bid
        current_bidder = None
        
        # AI bidding - collect interested bidders with their max bids
        bidders = {}
        for owner in self.owners:
            if owner == self.human or owner == nominator:
                continue

            if isinstance(owner, AIOwner) and owner.should_bid(player_name, position, current_price, self.total_picks):
                max_bid = owner.get_max_bid(player_name, position, current_price, self.total_picks)
                if max_bid > current_price:
                    bidders[owner] = max_bid

        # Proper bidding war - owners keep bidding until price exceeds their max
        last_bidder = None
        stalled_rounds = 0
        bid_count = 0

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
        
        # Human bidding
        if self.human.needs_players() and self.human != nominator:
            while True:
                bidder_name = current_bidder.name if current_bidder else 'NOBODY'
                print(f"\nCurrent bid: ${current_price} by {bidder_name}")
                print(f"Your budget: ${self.human.budget} | Spots left: {self.human.spots_left()}")
                
                if self.human.spots_left() > 0:
                    target = self.human.budget / self.human.spots_left()
                    print(f"Your target per remaining slot: ${target:.1f}")
                
                response = input("\nYour bid (or 'pass'): ").strip().lower()
                
                if response == 'pass':
                    break
                
                try:
                    bid_amount = int(response)
                    if bid_amount <= current_price:
                        print(f"Must bid more than ${current_price}")
                        continue
                    
                    if not self.human.can_bid(bid_amount):
                        print(f"Can't afford! Need ${self.human.spots_left()} for remaining spots.")
                        continue
                    
                    current_price = bid_amount
                    current_bidder = self.human
                    print(f"  YOU bid ${bid_amount}")
                    
                    # AI counter?
                    for owner in self.owners:
                        if owner == self.human or not isinstance(owner, AIOwner):
                            continue

                        max_bid = owner.get_max_bid(player_name, position, current_price, self.total_picks)
                        
                        if max_bid > current_price and owner.can_bid(max_bid) and random.random() < 0.4:
                            counter_bid = current_price + random.choice([1, 2])
                            if owner.can_bid(counter_bid):
                                current_price = counter_bid
                                current_bidder = owner
                                print(f"  {owner.name} bids ${counter_bid}")
                    
                    if current_bidder == self.human:
                        print("\nNo counter-bids. Player is yours!")
                        break
                        
                except ValueError:
                    print("Invalid bid")
        
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
            print(f"\n  (no bids) {nominator.name} takes at ${current_price}")

        if current_bidder:
            print(f"\n[SOLD] {current_bidder.name} wins {player_name} for ${current_price}")
            current_bidder.add_player(player_name, current_price, position)
            self.drafted_players.add(player_name)  # Track as drafted
            self.total_picks += 1
        else:
            print(f"\n[NO SALE] No bids for {player_name}")
    
    def run_auction(self):
        print("\n" + "="*80)
        print("DTFBL MOCK AUCTION SIMULATOR")
        print("="*80)
        print("\nEach owner takes turns nominating players.")
        print("FIXED: AI will spend money properly!\n")
        print("\nNomination order (randomized):")
        for i, owner in enumerate(self.owners, 1):
            marker = " <- YOU" if owner == self.human else ""
            print(f"  {i}. {owner.name}{marker}")
        
        input("\nPress Enter to start the auction...")
        self.display_status()
        
        round_num = 0
        
        while any(o.needs_players() for o in self.owners):
            round_num += 1
            nominator = self.get_next_nominator()
            
            if not nominator:
                break
            
            print(f"\n{'='*80}")
            print(f"ROUND {round_num}: {nominator.name}'s turn to nominate")
            print('='*80)
            
            if nominator == self.human:
                print("\nYour turn to nominate!")
                player_name = input("Player name: ").strip()
                position = input("Position (C/1B/2B/SS/3B/OF/SP/RP/DH): ").strip().upper()
                opening_str = input("Opening bid (default 1): ").strip()
                opening = int(opening_str) if opening_str else 1
            else:
                player_name, position = nominator.nominate_player(self.drafted_players)
                opening = 1
            
            self.run_bidding(player_name, position, nominator, opening)
            
            if round_num % 14 == 0:
                self.display_status()
        
        print(f"\n\n{'='*80}")
        print("AUCTION COMPLETE!")
        print('='*80)
        self.display_status()
        
        print("\n\nYOUR FINAL ROSTER:")
        if self.human.roster:
            for i, pick in enumerate(sorted(self.human.roster, key=lambda x: x['price'], reverse=True), 1):
                print(f"  {i}. ${pick['price']:3d} - {pick['player']:25s} ({pick['position']})")
            print(f"\nTotal spent: ${260 - self.human.budget}")
            print(f"Remaining: ${self.human.budget}")
        else:
            print("  No players drafted!")


if __name__ == '__main__':
    auction = MockAuction()
    auction.run_auction()
