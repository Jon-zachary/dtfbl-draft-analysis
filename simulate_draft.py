#!/usr/bin/env python3
"""
Full 7-team draft simulation with owner profiles.
Jon uses value hunting strategy, others use historical tendencies.
"""

import random
import json
from player_values import (
    calculate_all_players,
    calculate_dollar_values,
    HISTORICAL_PRICE_BY_RANK
)

# Load owner profiles
with open('owner_profiles.json', 'r') as f:
    OWNER_PROFILES = json.load(f)

# Remove Jon - he'll use value hunting
del OWNER_PROFILES["Jon's Generals"]

# Roster requirements
ROSTER_NEEDS = {'C': 1, '1B': 1, '2B': 1, 'SS': 1, '3B': 1, 'OF': 3, 'DH': 1, 'SP': 3, 'RP': 2}
TOTAL_SLOTS = sum(ROSTER_NEEDS.values())  # 14


class Owner:
    def __init__(self, name, profile=None, is_value_hunter=False):
        self.name = name
        self.profile = profile
        self.is_value_hunter = is_value_hunter
        self.budget = 260
        self.roster = {pos: [] for pos in ROSTER_NEEDS}
        self.picks = []

    def spots_filled(self):
        return sum(len(v) for v in self.roster.values())

    def spots_left(self):
        return TOTAL_SLOTS - self.spots_filled()

    def max_bid(self):
        """Maximum we can bid while keeping $1 for remaining spots"""
        return self.budget - (self.spots_left() - 1)

    def needs_position(self, pos):
        """Do we still need this position?"""
        # Map DH to 1B for flexibility
        if pos == 'DH':
            return len(self.roster['DH']) < ROSTER_NEEDS['DH']
        return len(self.roster.get(pos, [])) < ROSTER_NEEDS.get(pos, 0)

    def get_position_interest(self, pos):
        """How interested is this owner in this position? (0.5 to 1.5)"""
        if self.is_value_hunter:
            return 1.0  # Value hunter doesn't have position bias

        if not self.profile:
            return 1.0

        prefs = self.profile.get('position_preferences', {})
        if pos in prefs:
            premium = prefs[pos].get('premium_pct', 0)
            # Convert premium to interest multiplier (capped)
            # +50% premium -> 1.3 interest, -50% premium -> 0.7 interest
            return max(0.6, min(1.4, 1 + premium / 100 * 0.6))
        return 1.0

    def decide_bid(self, player, current_bid, all_owners):
        """Decide whether to bid and how much"""
        pos = player['position']

        # Don't bid if we don't need the position
        if not self.needs_position(pos):
            return 0

        # Don't bid more than we can afford
        max_possible = self.max_bid()
        if current_bid >= max_possible:
            return 0

        if self.is_value_hunter:
            return self._value_hunter_bid(player, current_bid, max_possible)
        else:
            return self._profile_based_bid(player, current_bid, max_possible)

    def _value_hunter_bid(self, player, current_bid, max_possible):
        """Value hunter: bid up to VORP value, never chase stars"""
        vorp_value = player['vorp_value']

        # Only bid if price is at or below value
        if current_bid >= vorp_value:
            return 0  # Let someone else overpay

        # Bid up to value, but leave room
        willing_to_pay = min(vorp_value, max_possible)

        if current_bid < willing_to_pay:
            return current_bid + 1
        return 0

    def _profile_based_bid(self, player, current_bid, max_possible):
        """AI owner: bid based on historical behavior"""
        pos = player['position']
        interest = self.get_position_interest(pos)

        # Base willingness = expected price adjusted by interest
        expected = player['expected_price']
        willing_to_pay = int(expected * interest)

        # Add some randomness (+/- 15%)
        willing_to_pay = int(willing_to_pay * random.uniform(0.85, 1.15))

        # Cap at what we can afford
        willing_to_pay = min(willing_to_pay, max_possible)

        # Budget pressure: if we have lots of money, be more aggressive
        target_per_slot = self.budget / self.spots_left() if self.spots_left() > 0 else 0
        if target_per_slot > 25 and current_bid < target_per_slot:
            willing_to_pay = max(willing_to_pay, int(target_per_slot * 0.9))

        if current_bid < willing_to_pay:
            return current_bid + 1
        return 0

    def add_player(self, player, price):
        """Add a player to roster"""
        pos = player['position']
        self.roster[pos].append(player)
        self.picks.append((player, price))
        self.budget -= price

    def total_points(self):
        return sum(p['points'] for p, _ in self.picks)

    def total_vorp(self):
        return sum(p['vorp'] for p, _ in self.picks)


def run_auction(players, owners):
    """Run a full auction"""
    available = players.copy()
    random.shuffle(owners)  # Randomize nomination order

    pick_num = 0
    nomination_idx = 0

    while any(o.spots_left() > 0 for o in owners) and available:
        # Find next owner who needs players
        attempts = 0
        while owners[nomination_idx].spots_left() == 0:
            nomination_idx = (nomination_idx + 1) % len(owners)
            attempts += 1
            if attempts > len(owners):
                break

        if attempts > len(owners):
            break

        nominator = owners[nomination_idx]

        # Nominator picks a player to nominate
        # AI nominates best available at a position they need
        # Value hunter nominates strategically (put up players others will overpay for)

        needs = [pos for pos, count in ROSTER_NEEDS.items()
                 if len(nominator.roster[pos]) < count]

        candidates = [p for p in available if p['position'] in needs]
        if not candidates:
            candidates = available

        if nominator.is_value_hunter:
            # Nominate players with worst delta (others will overpay)
            # But only if we don't want them
            overpay_targets = [p for p in available if p['delta'] < -10]
            if overpay_targets:
                player = random.choice(overpay_targets[:5])
            else:
                # Nominate best value we want
                our_needs = [p for p in available if p['position'] in needs]
                if our_needs:
                    player = max(our_needs, key=lambda x: x['delta'])
                else:
                    player = random.choice(available[:10])
        else:
            # AI nominates highest-ranked player at needed position
            if candidates:
                player = min(candidates, key=lambda x: x['rank'])
            else:
                player = min(available, key=lambda x: x['rank'])

        # Bidding war
        current_bid = 1
        current_winner = nominator

        bidding = True
        while bidding:
            bidding = False
            random.shuffle(owners)  # Randomize bid order

            for owner in owners:
                if owner == current_winner:
                    continue

                bid = owner.decide_bid(player, current_bid, owners)
                if bid > current_bid:
                    current_bid = bid
                    current_winner = owner
                    bidding = True
                    break  # Restart bidding round

        # Award player
        current_winner.add_player(player, current_bid)
        available.remove(player)
        pick_num += 1

        # Move to next nominator
        nomination_idx = (nomination_idx + 1) % len(owners)

    return owners


def print_results(owners):
    """Print final results"""
    print("=" * 90)
    print("FINAL DRAFT RESULTS")
    print("=" * 90)

    # Sort by total points
    owners.sort(key=lambda o: o.total_points(), reverse=True)

    for rank, owner in enumerate(owners, 1):
        strategy = "VALUE HUNTER" if owner.is_value_hunter else "AI"
        print(f"\n{'#'}{rank} {owner.name} [{strategy}]")
        print(f"   Budget: ${owner.budget} remaining | Points: {owner.total_points()} | VORP: {owner.total_vorp()}")
        print("-" * 70)

        # Sort picks by price
        for player, price in sorted(owner.picks, key=lambda x: -x[1]):
            delta = player['vorp_value'] - price
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            print(f"   ${price:2d}  {player['name']:<22} {player['position']:<3} {player['points']:4d} pts  (val ${player['vorp_value']}, {delta_str})")

    print("\n" + "=" * 90)
    print("STANDINGS BY PROJECTED POINTS")
    print("=" * 90)

    for rank, owner in enumerate(owners, 1):
        marker = " <<<" if owner.is_value_hunter else ""
        print(f"  {rank}. {owner.name:<20} {owner.total_points():,} pts  |  {owner.total_vorp():,} VORP  |  ${260 - owner.budget} spent{marker}")

    # Summary
    jon = next(o for o in owners if o.is_value_hunter)
    jon_rank = owners.index(jon) + 1

    print("\n" + "=" * 90)
    print("ANALYSIS")
    print("=" * 90)

    if jon_rank == 1:
        second = owners[1]
        margin = jon.total_points() - second.total_points()
        print(f"Jon's Generals (Value Hunter) WINS!")
        print(f"  Margin of victory: {margin} points over {second.name}")
    else:
        winner = owners[0]
        gap = winner.total_points() - jon.total_points()
        print(f"Jon's Generals finishes #{jon_rank}")
        print(f"  Gap to winner ({winner.name}): {gap} points")

    # Value analysis
    print(f"\nJon's value gained: ${sum(p['vorp_value'] - price for p, price in jon.picks)}")
    avg_ai_value = sum(sum(p['vorp_value'] - price for p, price in o.picks)
                       for o in owners if not o.is_value_hunter) / 6
    print(f"Average AI value gained: ${avg_ai_value:.0f}")


def main():
    print("Loading player values...")
    players = calculate_all_players()
    players, _ = calculate_dollar_values(players)

    print(f"Loaded {len(players)} players")
    print()

    # Create owners
    owners = []

    # Add AI owners
    for name, profile in OWNER_PROFILES.items():
        owners.append(Owner(name, profile, is_value_hunter=False))

    # Add Jon as value hunter
    owners.append(Owner("Jon's Generals", None, is_value_hunter=True))

    print("Teams in draft:")
    for o in owners:
        strategy = "VALUE HUNTER" if o.is_value_hunter else "Historical Profile"
        print(f"  - {o.name} ({strategy})")
    print()

    print("Running auction simulation...")
    print("=" * 90)

    owners = run_auction(players, owners)

    print_results(owners)


if __name__ == "__main__":
    main()
