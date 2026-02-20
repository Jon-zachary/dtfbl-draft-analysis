#!/usr/bin/env python3
"""
DTFBL Mock Auction Simulator
Proper nomination rotation + proper budget spending + roster enforcement
"""

import json
import random

# Roster slot requirements
ROSTER_SLOTS = {
    "C": 1,
    "1B": 1,
    "2B": 1,
    "SS": 1,
    "3B": 1,
    "OF": 3,
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
        if slot:
            self.position_counts[slot] += 1
        self.roster.append({
            'player': player_name,
            'price': price,
            'position': position,
            'slot': slot
        })
        self.budget -= price

    def positions_needed(self):
        """Return list of positions this owner still needs"""
        needed = []
        for pos, max_count in ROSTER_SLOTS.items():
            if self.position_counts[pos] < max_count:
                needed.append(pos)
        return needed


class AIOwner(Owner):
    """AI opponent that mimics historical behavior"""
    
    def should_bid(self, player_position, current_price, total_picks_so_far):
        if not self.can_bid(current_price + 1) or not self.needs_players():
            return False

        # ROSTER ENFORCEMENT: Don't bid if we don't need this position
        if not self.needs_position(player_position):
            return False

        # Calculate target spend per remaining slot
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        total_slots = 14 * 8  # 8 owners (7 AI + 1 human)
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
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0

        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        avg_price = pos_data.get('avg_price', 20)
        premium_pct = pos_data.get('premium_pct', 0)

        # Position-adjusted historical price (what this owner typically pays)
        position_adjusted = avg_price * (1 + premium_pct / 100)

        total_slots = 14 * 8
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
                # Flex slot can be filled by SP or RP
                available_positions.extend(["SP", "RP"])
            else:
                available_positions.append(pos)

        # Remove duplicates while preserving some order
        available_positions = list(dict.fromkeys(available_positions))

        if not available_positions:
            # Fallback if somehow we need nothing (shouldn't happen)
            available_positions = list(player_pool.keys())

        # Pick a random position we need, then a random player at that position
        position = random.choice(available_positions)
        player = random.choice(player_pool.get(position, ["Unknown Player"]))

        return (player, position)


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

            if isinstance(owner, AIOwner) and owner.should_bid(position, current_price, self.total_picks):
                max_bid = owner.get_max_bid(position, current_price, self.total_picks)
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
                        
                        max_bid = owner.get_max_bid(position, current_price, self.total_picks)
                        
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
        
        # Finalize - if no one bid, nominator gets player
        # But they should spend appropriately based on their budget pressure
        if not current_bidder and nominator.can_bid(current_price):
            current_bidder = nominator
            # Calculate what nominator should pay based on budget pressure
            spots = nominator.spots_left()
            if spots > 0:
                target = nominator.budget / spots
                max_affordable = nominator.budget - spots + 1
                fair_price = min(int(target), max_affordable)
                fair_price = max(fair_price, current_price)
                current_price = fair_price
            print(f"\n  (no bids) {nominator.name} takes at ${current_price}")

        if current_bidder:
            print(f"\n[SOLD] {current_bidder.name} wins {player_name} for ${current_price}")
            current_bidder.add_player(player_name, current_price, position)
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
                player_name, position = nominator.nominate_player()
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
