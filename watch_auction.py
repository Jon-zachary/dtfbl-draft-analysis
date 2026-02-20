#!/usr/bin/env python3
"""
Automated Mock Auction - Watch AI opponents draft against each other
FIXED: Ensures owners spend their money properly + roster enforcement
"""

import json
import random

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

    def should_bid(self, player_position, current_price, total_picks_so_far):
        """Decide if AI should enter bidding"""

        if not self.can_bid(current_price + 1) or not self.needs_players():
            return False

        # ROSTER ENFORCEMENT: Don't bid if we don't need this position
        if not self.needs_position(player_position):
            return False

        # Calculate target spend per remaining slot
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        total_slots = 14 * 7  # 7 teams * 14 slots = 98 picks
        pct_complete = total_picks_so_far / total_slots

        # CRITICAL FIX: Force bidding when sitting on money in late auction
        # If we have significant $/slot and price is below target, MUST BID
        if pct_complete >= 0.6 and target_per_slot >= 15 and current_price < target_per_slot:
            return True  # Can't let cheap players go when sitting on cash

        # Very late auction: even more aggressive
        if pct_complete >= 0.8 and target_per_slot >= 10 and current_price < target_per_slot * 1.2:
            return True  # Must spend mode

        # Get position preference for normal interest-based bidding
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)

        base_interest = 0.5
        interest = base_interest + (premium_pct / 200)

        # Progressive aggression as auction advances
        if pct_complete < 0.3:
            interest *= 1.1
        elif pct_complete < 0.6:
            interest *= 1.0
        else:
            # Late auction: more aggressive even for non-forced bids
            if current_price < target_per_slot * 0.8:
                interest *= 1.8
            else:
                interest *= 1.3

        # Budget pressure bonus
        if target_per_slot > 25:
            interest *= 1.4
        elif target_per_slot > 18:
            interest *= 1.2

        interest *= random.uniform(0.9, 1.1)
        return random.random() < min(interest, 0.95)
    
    def get_max_bid(self, player_position, current_price, total_picks_so_far):
        """Determine maximum AI willing to pay"""

        spots_left = self.spots_left()
        money_left = self.budget

        # Last pick - spend entire remaining budget (can't carry it over)
        if spots_left == 1:
            return money_left

        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        # Get historical avg for this position
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        avg_price = pos_data.get('avg_price', 20)
        premium_pct = pos_data.get('premium_pct', 0)

        # Position-adjusted historical price (what this owner typically pays)
        position_adjusted = avg_price * (1 + premium_pct / 100)

        total_slots = 14 * 7
        pct_complete = total_picks_so_far / total_slots

        # Early auction: Use position-adjusted historical average (conservative)
        if pct_complete < 0.4:
            max_price = position_adjusted * random.uniform(0.8, 1.15)

        # Mid auction: Blend historical with budget reality
        elif pct_complete < 0.7:
            # Weight shifts toward target as auction progresses
            blend_factor = (pct_complete - 0.4) / 0.3  # 0 at 40%, 1 at 70%
            historical_weight = 1 - (blend_factor * 0.5)  # 1.0 -> 0.5
            target_weight = blend_factor * 0.5  # 0 -> 0.5
            blended = (position_adjusted * historical_weight) + (target_per_slot * target_weight)
            max_price = blended * random.uniform(0.95, 1.2)

        # Late auction: Budget reality takes priority
        else:
            # CRITICAL FIX: target_per_slot is the FLOOR, not a random multiplier
            if target_per_slot >= 15:
                # Pay between target and 1.3x target - never below target
                max_price = target_per_slot * random.uniform(1.0, 1.3)
            elif target_per_slot >= 8:
                # Moderate budget - blend but ensure floor
                max_price = max(position_adjusted * random.uniform(1.0, 1.3), target_per_slot)
            else:
                # Everyone is winding down - use historical with small boost
                max_price = position_adjusted * random.uniform(1.0, 1.2)

        # Very late auction: guarantee we hit target to force spending
        if pct_complete >= 0.85 and target_per_slot >= 10:
            max_price = max(max_price, target_per_slot * 1.1)

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
    
    def nominate_player(self):
        """Nominate a player at a position the AI still needs"""
        # Player pool organized by position (NL-only players)
        player_pool = {
            "C": ["J.T. Realmuto", "William Contreras", "Willson Contreras", "Travis d'Arnaud",
                  "Gabriel Moreno", "Will Smith", "Patrick Bailey", "Yasmani Grandal"],
            "1B": ["Freddie Freeman", "Pete Alonso", "Matt Olson", "Bryce Harper",
                   "Cody Bellinger", "Christian Walker", "Josh Bell", "LaMonte Wade Jr."],
            "2B": ["Ketel Marte", "Ozzie Albies", "Luis Arraez", "Gavin Lux",
                   "Brendan Rodgers", "Jake Cronenworth", "Brandon Lowe", "Bryson Stott"],
            "SS": ["Francisco Lindor", "Trea Turner", "Elly De La Cruz", "Mookie Betts",
                   "Dansby Swanson", "CJ Abrams", "Ha-Seong Kim", "Ezequiel Tovar"],
            "3B": ["Manny Machado", "Nolan Arenado", "Austin Riley", "Ryan McMahon",
                   "Matt Chapman", "Ke'Bryan Hayes", "Alec Bohm", "Max Muncy"],
            "OF": ["Juan Soto", "Fernando Tatis Jr.", "Kyle Tucker", "Corbin Carroll",
                   "Ronald Acuna Jr.", "Mookie Betts", "Ian Happ", "Jackson Chourio",
                   "Lars Nootbaar", "Bryan De La Cruz", "Brandon Marsh", "Michael Harris II"],
            "DH": ["Shohei Ohtani", "Kyle Schwarber", "Marcell Ozuna", "Jesse Winker",
                   "Spencer Steer", "JD Martinez", "Jorge Soler", "Rhys Hoskins"],
            "SP": ["Zack Wheeler", "Spencer Strider", "Chris Sale", "Paul Skenes",
                   "Logan Webb", "Shota Imanaga", "Yu Darvish", "Blake Snell",
                   "Ranger Suarez", "Dylan Cease", "Miles Mikolas", "Sonny Gray"],
            "RP": ["Edwin Diaz", "Ryan Helsley", "Josh Hader", "Camilo Doval",
                   "Alexis Diaz", "Robert Suarez", "Tanner Scott", "A.J. Minter"],
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

        # Pick a random position we need, then a random player at that position
        position = random.choice(available_positions)
        player = random.choice(player_pool.get(position, ["Unknown Player"]))

        return (player, position)


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
        
        # Nominate
        player_name, position = nominator.nominate_player()
        
        if auction_round % 10 == 0 or auction_round <= 5:
            print(f"\n{'='*80}")
            print(f"PICK #{auction_round}: {nominator.name} nominates {player_name} ({position})")
            print('='*80)
        
        current_price = 1
        current_bidder = None
        
        # Collect interested bidders with their max bids
        bidders = {}
        for owner in owners:
            if owner.should_bid(position, current_price, auction_round):
                max_bid = owner.get_max_bid(position, current_price, auction_round)
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
