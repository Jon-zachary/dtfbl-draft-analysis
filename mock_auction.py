#!/usr/bin/env python3
"""
DTFBL Mock Auction Simulator
Practice your auction strategy against AI opponents modeled on 16 years of draft data
"""

import json
import random
import pandas as pd

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
        # Must leave $1 for each remaining spot
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
    
    def should_bid(self, player_position, current_price, nomination_owner):
        """Decide if AI should enter bidding"""
        
        # Don't bid if can't afford
        if not self.can_bid(current_price + 1):
            return False
        
        # Already have full roster
        if not self.needs_players():
            return False
        
        # Get position preference from profile
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        position_interest = pos_data.get('pct_budget', 10) / 100  # Convert to 0-1
        
        # Base interest (0-1 scale)
        interest = position_interest
        
        # Modify based on current spending
        budget_pct_left = self.budget / 260
        spent_pct = 1 - budget_pct_left
        
        # Stars & Scrubs players are more aggressive early
        if spent_pct < 0.3:  # Early auction
            interest *= 1.3
        elif budget_pct_left < 0.2:  # Low budget, become conservative
            interest *= 0.5
        
        # Heavy bargain hunters (high $1 pick rate) drop out faster
        dollar_rate = self.profile.get('dollar_pick_rate', 0.2)
        if dollar_rate > 0.23 and current_price > 8:
            interest *= 0.6
        
        # Random factor (AI personality variance)
        interest *= random.uniform(0.8, 1.2)
        
        # Probabilistic decision
        return random.random() < interest
    
    def get_max_bid(self, player_position, current_price):
        """Determine maximum AI willing to pay"""
        
        # Get historical avg for this position
        pos_prefs = self.profile.get('position_preferences', {})
        pos_data = pos_prefs.get(player_position, {})
        avg_price = pos_data.get('avg_price', 20)
        
        # AI willing to pay around historical average (with variance)
        max_price = int(avg_price * random.uniform(0.8, 1.4))
        
        # Clamp to budget constraints
        max_affordable = self.budget - self.spots_left() + 1
        max_price = min(max_price, max_affordable)
        
        # Must be more than current price
        max_price = max(max_price, current_price + 1)
        
        return max_price
    
    def decide_bid_increment(self, current_price, max_bid):
        """Decide how much to increase bid"""
        
        gap = max_bid - current_price
        
        if gap > 20:
            # Jump aggressively if way below max
            return random.choice([2, 3, 5])
        elif gap > 5:
            return random.choice([1, 2])
        else:
            return 1


class MockAuction:
    """Runs the mock auction"""
    
    def __init__(self, profiles_file='/home/claude/owner_profiles.json'):
        # Load profiles
        with open(profiles_file, 'r') as f:
            self.profiles = json.load(f)
        
        # Create AI owners
        self.owners = []
        for name, profile in self.profiles.items():
            self.owners.append(AIOwner(name, profile=profile))
        
        # Add human player
        self.human = Owner("YOU (Practice)", budget=260)
        self.owners.append(self.human)
        
        # Track auction state
        self.auction_log = []
        self.current_player = None
        self.current_price = 0
        self.current_bidder = None
        
    def display_status(self):
        """Show current auction state"""
        print("\n" + "="*80)
        print("AUCTION STATUS")
        print("="*80)
        
        for owner in sorted(self.owners, key=lambda x: x.budget, reverse=True):
            roster_str = f"{len(owner.roster)}/{owner.roster_size}"
            budget_str = f"${owner.budget}"
            marker = " ← YOU" if owner == self.human else ""
            print(f"{owner.name:20s} | Roster: {roster_str:5s} | Budget: {budget_str:>6s}{marker}")
    
    def nominate_player(self, player_name, position, opening_bid=1):
        """Start bidding on a player"""
        print(f"\n{'='*80}")
        print(f"NOMINATED: {player_name} ({position}) - Opening bid: ${opening_bid}")
        print('='*80)
        
        self.current_player = player_name
        self.current_price = opening_bid
        self.current_bidder = None
        
        # Simulate bidding
        interested_owners = []
        
        for owner in self.owners:
            if owner == self.human:
                continue  # Human decides separately
            
            if isinstance(owner, AIOwner) and owner.should_bid(position, self.current_price, None):
                max_bid = owner.get_max_bid(position, self.current_price)
                interested_owners.append((owner, max_bid))
        
        # Sort by max bid (most interested first)
        interested_owners.sort(key=lambda x: x[1], reverse=True)
        
        # Bidding war
        bidding_active = len(interested_owners) > 0
        last_bidder = None
        
        while bidding_active:
            # Highest interested owner bids
            if interested_owners:
                owner, max_bid = interested_owners[0]
                
                if max_bid > self.current_price and owner.can_bid(max_bid):
                    increment = owner.decide_bid_increment(self.current_price, max_bid)
                    new_bid = min(self.current_price + increment, max_bid)
                    
                    if owner.can_bid(new_bid):
                        self.current_price = new_bid
                        self.current_bidder = owner
                        print(f"  {owner.name} bids ${new_bid}")
                        last_bidder = owner
                        
                        # Remove this owner, they've bid
                        interested_owners.pop(0)
                        
                        # Check if others still interested
                        interested_owners = [(o, m) for o, m in interested_owners if m > self.current_price]
                    else:
                        interested_owners.pop(0)
                else:
                    interested_owners.pop(0)
            else:
                bidding_active = False
        
        # Ask human if they want to bid
        if self.human.needs_players():
            print(f"\nCurrent bid: ${self.current_price} by {self.current_bidder.name if self.current_bidder else 'NOBODY'}")
            print(f"Your budget: ${self.human.budget} | Spots left: {self.human.spots_left()}")
            
            while True:
                response = input("\nYour bid (or 'pass'): ").strip().lower()
                
                if response == 'pass':
                    break
                
                try:
                    bid_amount = int(response)
                    if bid_amount <= self.current_price:
                        print(f"Must bid more than ${self.current_price}")
                        continue
                    
                    if not self.human.can_bid(bid_amount):
                        print(f"Can't afford! Need ${self.human.spots_left()} for remaining spots.")
                        continue
                    
                    self.current_price = bid_amount
                    self.current_bidder = self.human
                    print(f"  YOU bid ${bid_amount}")
                    
                    # AI responses
                    for owner in self.owners:
                        if owner == self.human:
                            continue
                        
                        if isinstance(owner, AIOwner):
                            max_bid = owner.get_max_bid(position, self.current_price)
                            
                            if max_bid > self.current_price and owner.can_bid(max_bid) and random.random() < 0.4:
                                counter_bid = self.current_price + random.choice([1, 2])
                                if owner.can_bid(counter_bid):
                                    self.current_price = counter_bid
                                    self.current_bidder = owner
                                    print(f"  {owner.name} bids ${counter_bid}")
                    
                    # Ask human again if outbid
                    if self.current_bidder != self.human:
                        continue
                    else:
                        break
                        
                except ValueError:
                    print("Invalid bid")
        
        # Finalize
        if self.current_bidder:
            print(f"\n🎯 SOLD to {self.current_bidder.name} for ${self.current_price}")
            self.current_bidder.add_player(self.current_player, self.current_price, position)
        else:
            print(f"\n❌ No bids for {self.current_player}")
    
    def run_interactive(self):
        """Run interactive auction"""
        print("\n" + "="*80)
        print("DTFBL MOCK AUCTION SIMULATOR")
        print("="*80)
        print("\nPractice your auction strategy against AI opponents!")
        print("AI behavior based on 16 years of historical draft data.")
        print("\nCommands:")
        print("  nominate <player> <pos> [price] - Start bidding")
        print("  status - Show current standings")
        print("  roster <team> - View a team's roster")
        print("  quit - Exit simulator")
        
        self.display_status()
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'quit':
                print("\nThanks for practicing!")
                break
            
            elif cmd == 'status':
                self.display_status()
            
            elif cmd.startswith('roster'):
                parts = cmd.split()
                if len(parts) > 1:
                    team_name = ' '.join(parts[1:])
                    owner = next((o for o in self.owners if team_name.lower() in o.name.lower()), None)
                    if owner:
                        print(f"\n{owner.name}'s Roster:")
                        for i, pick in enumerate(owner.roster, 1):
                            print(f"  {i}. {pick['player']:25s} {pick['position']:6s} ${pick['price']}")
                        print(f"  Budget remaining: ${owner.budget}")
                    else:
                        print("Team not found")
            
            elif cmd.startswith('nominate'):
                parts = cmd.split()
                if len(parts) >= 3:
                    player = ' '.join(parts[1:-1])
                    position = parts[-1]
                    opening = 1
                    
                    if len(parts) >= 4 and parts[-2].isdigit():
                        opening = int(parts[-2])
                        position = parts[-1]
                    
                    self.nominate_player(player, position, opening)
                else:
                    print("Usage: nominate <player> <position> [opening_bid]")
            
            else:
                print("Unknown command. Try: nominate, status, roster, quit")


if __name__ == '__main__':
    auction = MockAuction()
    auction.run_interactive()
