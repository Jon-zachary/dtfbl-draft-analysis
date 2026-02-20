#!/usr/bin/env python3
"""
Automated Mock Auction - Watch AI opponents draft against each other
Useful for understanding bidding patterns before running interactive version
"""

import json
import random
from mock_auction import AIOwner, Owner

def run_auto_auction():
    """Run a fully automated auction"""
    
    # Load profiles
    with open('/home/claude/owner_profiles.json', 'r') as f:
        profiles = json.load(f)
    
    # Create all AI owners
    owners = []
    for name, profile in profiles.items():
        owners.append(AIOwner(name, profile=profile))
    
    # Sample player pool (simplified)
    players = [
        ("Shohei Ohtani", "DH"), ("Juan Soto", "OF"), ("Francisco Lindor", "SS"),
        ("Kyle Tucker", "OF"), ("Elly De La Cruz", "SS"), ("William Contreras", "C"),
        ("Bryce Harper", "1B"), ("Fernando Tatis", "OF"), ("Trea Turner", "SS"),
        ("Pete Alonso", "1B"), ("Kyle Schwarber", "DH"), ("Matt Olson", "1B"),
        ("Corbin Carroll", "OF"), ("Mookie Betts", "SS"), ("Paul Skenes", "SP"),
        ("Zack Wheeler", "SP"), ("Edwin Diaz", "RP"), ("Chris Sale", "SP"),
        ("Freddie Freeman", "1B"), ("Ketel Marte", "2B"), ("Dansby Swanson", "SS"),
        # Add more players...
    ]
    
    print("="*80)
    print("AUTOMATED MOCK AUCTION")
    print("="*80)
    print("\nWatch AI opponents bid against each other")
    print("Based on 16 years of historical behavior\n")
    
    auction_round = 0
    
    while any(o.needs_players() for o in owners) and auction_round < 98:
        # Pick a random owner to nominate
        nominator = random.choice([o for o in owners if o.needs_players()])
        
        # Pick a player
        if auction_round < len(players):
            player_name, position = players[auction_round]
        else:
            player_name = f"Player {auction_round+1}"
            position = random.choice(["OF", "SP", "SS", "C", "1B"])
        
        auction_round += 1
        
        print(f"\n{'='*80}")
        print(f"PICK #{auction_round}: {nominator.name} nominates {player_name} ({position})")
        print('='*80)
        
        current_price = 1
        current_bidder = None
        
        # Collect interested bidders
        interested = []
        for owner in owners:
            if owner.should_bid(position, current_price, nominator):
                max_bid = owner.get_max_bid(position, current_price)
                interested.append((owner, max_bid))
        
        interested.sort(key=lambda x: x[1], reverse=True)
        
        # Bidding war
        while interested:
            owner, max_bid = interested.pop(0)
            
            if max_bid > current_price and owner.can_bid(max_bid):
                increment = owner.decide_bid_increment(current_price, max_bid)
                new_bid = min(current_price + increment, max_bid)
                
                if owner.can_bid(new_bid):
                    current_price = new_bid
                    current_bidder = owner
                    print(f"  {owner.name} bids ${new_bid}")
                    
                    # Re-filter interested
                    interested = [(o, m) for o, m in interested if m > current_price]
        
        # Finalize
        if current_bidder:
            print(f"  → SOLD to {current_bidder.name} for ${current_price}")
            current_bidder.add_player(player_name, current_price, position)
        
        # Show standings periodically
        if auction_round % 10 == 0:
            print(f"\n{'─'*80}")
            print(f"After {auction_round} picks:")
            for owner in sorted(owners, key=lambda x: x.budget, reverse=True):
                print(f"  {owner.name:20s} | Roster: {len(owner.roster):2d}/14 | Budget: ${owner.budget:3d}")
    
    # Final results
    print(f"\n\n{'='*80}")
    print("FINAL RESULTS")
    print('='*80)
    
    for owner in sorted(owners, key=lambda x: len(owner.roster), reverse=True):
        print(f"\n{owner.name}")
        print(f"  Budget used: ${260 - owner.budget} | Remaining: ${owner.budget}")
        print(f"  Roster ({len(owner.roster)}/14):")
        
        for pick in sorted(owner.roster, key=lambda x: x['price'], reverse=True):
            print(f"    ${pick['price']:3d} - {pick['player']:25s} ({pick['position']})")

if __name__ == '__main__':
    print("\nRunning automated auction...")
    print("(This will take ~30 seconds)\n")
    run_auto_auction()
    
    print("\n\nTo practice interactively:")
    print("  python mock_auction.py")
