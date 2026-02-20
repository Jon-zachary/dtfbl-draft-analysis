#!/usr/bin/env python3
"""
DTFBL Mock Auction Simulator
Proper nomination rotation + proper budget spending
"""

import json
import random

class Owner:
    """Represents an auction participant (human or AI)"""
    def __init__(self, name, budget=260, profile=None):
        self.name = name
        self.budget = budget
        self.roster = []
        self.roster_size = 14
        self.profile = profile or {}
        
    def needs_players(self):
        return len(self.roster) < self.roster_size
    
    def spots_left(self):
        return self.roster_size - len(self.roster)
    
    def can_bid(self, amount):
        return self.budget - amount >= self.spots_left() - 1
    
    def add_player(self, player_name, price, position):
        self.roster.append({
            'player': player_name,
            'price': price,
            'position': position
        })
        self.budget -= price


class AIOwner(Owner):
    """AI opponent that mimics historical behavior"""
    
    def should_bid(self, player_position, current_price, total_picks_so_far):
        if not self.can_bid(current_price + 1) or not self.needs_players():
            return False
        
        # Calculate target spend per remaining slot
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0
        
        # Get position preference
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        premium_pct = pos_data.get('premium_pct', 0)
        
        base_interest = 0.5
        interest = base_interest + (premium_pct / 200)
        
        # Progressive aggression as auction advances
        total_slots = 14 * 8  # 8 owners (7 AI + 1 human)
        pct_complete = total_picks_so_far / total_slots
        
        if pct_complete < 0.3:
            interest *= 1.1
        elif pct_complete < 0.7:
            interest *= 1.0
        else:
            # Late auction: MUST SPEND
            if current_price < target_per_slot * 0.8:
                interest *= 2.0
            else:
                interest *= 1.3
        
        # If we have lots of money left, be aggressive
        if target_per_slot > 20:
            if current_price < target_per_slot * 0.6:
                interest *= 1.5
        
        interest *= random.uniform(0.8, 1.2)
        return random.random() < interest
    
    def get_max_bid(self, player_position, current_price, total_picks_so_far):
        spots_left = self.spots_left()
        money_left = self.budget
        target_per_slot = money_left / spots_left if spots_left > 0 else 0
        
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        avg_price = pos_data.get('avg_price', 20)
        
        total_slots = 14 * 8
        pct_complete = total_picks_so_far / total_slots
        
        # Early: historical average
        if pct_complete < 0.4:
            max_price = int(avg_price * random.uniform(0.9, 1.3))
        
        # Mid: blend historical with target
        elif pct_complete < 0.7:
            blended = (avg_price * 0.6) + (target_per_slot * 0.4)
            max_price = int(blended * random.uniform(0.9, 1.2))
        
        # Late: MUST SPEND
        else:
            if target_per_slot > 20:
                max_price = int(target_per_slot * random.uniform(0.9, 1.4))
            else:
                max_price = int(avg_price * random.uniform(1.0, 1.5))
        
        max_affordable = self.budget - self.spots_left() + 1
        max_price = min(max_price, max_affordable)
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
        players = [
            ("Shohei Ohtani", "DH"), ("Juan Soto", "OF"), ("Francisco Lindor", "SS"),
            ("Kyle Tucker", "OF"), ("Elly De La Cruz", "SS"), ("William Contreras", "C"),
            ("Bryce Harper", "1B"), ("Fernando Tatis", "OF"), ("Trea Turner", "SS"),
            ("Pete Alonso", "1B"), ("Kyle Schwarber", "DH"), ("Matt Olson", "1B"),
            ("Corbin Carroll", "OF"), ("Mookie Betts", "SS"), ("Paul Skenes", "SP"),
            ("Zack Wheeler", "SP"), ("Edwin Diaz", "RP"), ("Chris Sale", "SP"),
            ("Freddie Freeman", "1B"), ("Ketel Marte", "2B"), ("Manny Machado", "3B"),
            ("Nolan Arenado", "3B"), ("Willson Contreras", "C"), ("Ozzie Albies", "2B"),
        ]
        return random.choice(players)


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
        
        # AI bidding
        interested_owners = []
        for owner in self.owners:
            if owner == self.human or owner == nominator:
                continue
            
            if isinstance(owner, AIOwner) and owner.should_bid(position, current_price, self.total_picks):
                max_bid = owner.get_max_bid(position, current_price, self.total_picks)
                interested_owners.append((owner, max_bid))
        
        interested_owners.sort(key=lambda x: x[1], reverse=True)
        
        while interested_owners:
            owner, max_bid = interested_owners[0]
            
            if max_bid > current_price and owner.can_bid(max_bid):
                increment = owner.decide_bid_increment(current_price, max_bid)
                new_bid = min(current_price + increment, max_bid)
                
                if owner.can_bid(new_bid):
                    current_price = new_bid
                    current_bidder = owner
                    print(f"  {owner.name} bids ${new_bid}")
                    interested_owners.pop(0)
                    interested_owners = [(o, m) for o, m in interested_owners if m > current_price]
                else:
                    interested_owners.pop(0)
            else:
                interested_owners.pop(0)
        
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
        
        # Finalize
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
