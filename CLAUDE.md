# DTFBL Fantasy Baseball Draft Analysis - Project Overview

## What This Project Does

This project analyzes **16 years of fantasy baseball auction draft data** (2009-2025) from the Downtown Fantasy Baseball League (DTFBL), a 7-team NL-only auction league. It provides:

1. **Historical analysis** of owner spending patterns
2. **Exploitable tendencies** for each owner (who overpays/underpays for positions)
3. **Mock auction simulator** to practice draft strategy
4. **AI opponents** that mimic real owner behavior based on 16 years of data

---

## File Structure

```
draft-analysis/
├── all_drafts_2009_2025.csv          # Raw historical data (1,354 picks)
├── owner_profiles.json                # AI behavior profiles (CORRECTED)
├── position_analysis.json             # League baselines and roster structure
├── OWNER_PROFILES.md                  # Human-readable analysis
├── mock_auction.py                    # Interactive auction simulator ⚠️ BUGGY
├── watch_auction.py                   # Automated auction observer ⚠️ BUGGY
├── README.md                          # User documentation
└── CLAUDE.md                          # This file (for Claude Code)
```

---

## Current Bugs 🐛

### **CRITICAL BUG: AI Not Spending Money Properly**

**Problem:**
- AI owners finish auction with $50-100+ left unspent
- In real auctions, you MUST spend your budget
- If you have $100 and 5 spots left, you should average $20/pick
- AI is only bidding based on historical averages, ignoring budget reality

**Expected Behavior:**
- Most teams should end with **$0-10 remaining**
- Late auction should be aggressive (must spend!)
- Teams with high `$/remaining_slot` should bid more

**Where the bug is:**
- `AIOwner.should_bid()` - decision to enter bidding
- `AIOwner.get_max_bid()` - maximum willing to pay
- Not properly accounting for budget urgency as auction progresses

---

## How the Code Works

### **Auction Flow**

1. **Nomination Rotation:**
   - Each owner takes turns nominating a player
   - Order is randomized at start
   - Continues until everyone has 14 players

2. **Bidding Process:**
   - Nominator selects player + position
   - AI owners decide if interested (based on position preferences + budget)
   - Bidding war ensues
   - Winner pays final price, adds to roster

3. **Budget Constraints:**
   - Each owner starts with $260
   - Must draft 14 players
   - Must keep $1 per remaining roster spot (can't bid yourself into a corner)
   - Formula: `can_bid(amount)` returns `budget - amount >= spots_left - 1`

### **AI Decision Making**

**Position Preferences (from owner_profiles.json):**
```json
"Forest Rangers": {
  "position_preferences": {
    "3B": {
      "avg_price": 33.6,
      "league_avg": 22.5,
      "premium_pct": 49.0  // Overpays 3B by 49%!
    },
    "SP": {
      "avg_price": 8.3,
      "league_avg": 17.2,
      "premium_pct": -52.0  // Underpays SP by 52%!
    }
  }
}
```

**Current AI Logic (BROKEN):**

```python
def should_bid(self, player_position, current_price, total_picks_so_far):
    # Uses premium_pct to determine interest
    # Example: Forest Rangers has +49% premium on 3B → more interested
    # Example: Forest Rangers has -52% premium on SP → less interested
    
    # BUG: Doesn't properly account for budget urgency!
    pass

def get_max_bid(self, player_position, current_price, total_picks_so_far):
    # Determines maximum price willing to pay
    # Should blend:
    #   - Historical average for position
    #   - Current budget reality ($/remaining_slot)
    #   - Auction phase (early = conservative, late = aggressive)
    
    # BUG: Late auction doesn't force spending!
    pass
```

---

## What Needs to Happen

### **Target Behavior**

**Early Auction (picks 1-30):**
- AI bids based mostly on historical averages
- Example: If position avg is $20, bid up to ~$25

**Mid Auction (picks 31-70):**
- Blend historical averages with budget reality
- Example: Historical avg $15, but have $100/5 slots = $20 target → bid ~$18

**Late Auction (picks 71-98):**
- **MUST SPEND MODE**
- If you have $80 and 4 spots left → target is $20/slot
- Should be willing to pay $20-25 even if historical avg is $15
- Can't let cheap players slip away when sitting on money

### **Key Formula**

```python
# Calculate urgency
spots_left = self.spots_left()
money_left = self.budget
target_per_slot = money_left / spots_left if spots_left > 0 else 0

# Late auction logic
if late_in_auction and current_price < target_per_slot:
    # MUST BID - can't let bargains go when sitting on cash!
    be_very_aggressive()
```

---

## Roster Structure

From `position_analysis.json`:

```json
{
  "roster_slots": {
    "C": 1,
    "1B": 1,
    "2B": 1,
    "SS": 1,
    "3B": 1,
    "OF": 3,      // Three outfielders!
    "SP": 3,      // Three starting pitchers!
    "RP": 1,
    "SP / RP": 1
  },
  "league_baseline": {
    "C": 13.40,   // League avg per catcher
    "OF": 24.34,  // League avg per outfielder
    "SP": 17.22,  // League avg per starting pitcher
    ...
  }
}
```

**Important:** We draft **3 OF** and **3 SP**, so these positions should collectively get more money - but we judge by **per-player** spending, not total allocation.

---

## Testing the Fix

### **Test 1: Watch Auction**
```bash
python watch_auction.py
```

**Check:**
- Final budgets should be $0-10 for most teams
- Late auction picks should match or exceed `$/slot` targets
- No team should finish with $50+ remaining

### **Test 2: Interactive Auction**
```bash
python mock_auction.py
```

**Check:**
- AI should bid aggressively in late rounds
- Status display shows `$/slot` targets
- If AI has $100/5 slots ($20 target), they should bid $15-25 on players

### **Test 3: Budget Tracking**

After picks 70-80, check status:
```
Forest Rangers    | Roster: 11/14 | Budget: $60  | $/slot: $20.0
```

Next few picks by Forest Rangers should average close to $20, not $8!

---

## Owner Behavior Examples (from OWNER_PROFILES.md)

**David's Devils:**
- Overpays RP by +72% (pays $31 vs $18 league avg)
- Overpays 1B by +48% (pays $42 vs $28 league avg)
- **Underpays SS by -53%** (pays $11 vs $24 league avg)
- **Underpays OF by -37%** (pays $15 vs $24 league avg)

**Forest Rangers:**
- Overpays 3B by +49% (pays $34 vs $23 league avg)
- Overpays SS by +37% (pays $33 vs $24 league avg)
- **Underpays SP by -52%** (pays $8 vs $17 league avg)

**Jake's Snakes:**
- Overpays C by +72% (pays $23 vs $13 league avg)
- Overpays SS by +42% (pays $35 vs $24 league avg)
- **Underpays 2B by -52%** (pays $7 vs $15 league avg)

These premiums/discounts should be reflected in AI bidding, BUT also adjusted for budget reality in late auction!

---

## Data Files

### **all_drafts_2009_2025.csv**
```csv
Year,Team,Position,Player,MLB_Team,Price,Money_Left,Money_Spent
2025,Forest Rangers,C,J.T. Realmuto,Phi,15.0,58.0,202.0
2025,Forest Rangers,1B,Bryce Harper,Phi,42.0,73.0,187.0
...
```

### **owner_profiles.json**
```json
{
  "Forest Rangers": {
    "name": "Forest Rangers",
    "years_active": 14,
    "avg_price": 19.6,
    "max_price": 85.0,
    "position_preferences": {
      "3B": {
        "avg_price": 33.6,
        "league_avg": 22.5,
        "premium_pct": 49.0
      },
      ...
    }
  },
  ...
}
```

---

## Success Criteria

✅ **Watch auction ends with:**
- 5-7 teams with $0-10 remaining
- 0-2 teams with $10-20 remaining
- **0 teams with $50+ remaining**

✅ **Late auction behavior:**
- Picks 70-90 should average close to teams' `$/slot` targets
- Teams sitting on money should bid aggressively
- No "cheap" picks ($1-5) when teams have $20+ per slot budgets

✅ **Interactive mode shows:**
- Clear `$/slot` targets in status display
- AI bids reflect budget urgency
- Realistic auction dynamics

---

## Additional Context

### **Why This Matters**

This is a **real fantasy baseball league** running since 2013. The user wants to:
1. Practice auction strategy
2. Exploit opponent tendencies (e.g., "David's punts SS, so steal Lindor cheap")
3. Learn when to be aggressive vs patient

The mock auction is **useless** if AI doesn't spend money realistically!

### **League Format**
- **NL-only:** Only National League players eligible
- **Auction draft:** $260 budget, nominate players, highest bid wins
- **14-player rosters:** C(1), 1B(1), 2B(1), SS(1), 3B(1), OF(3), SP(3), RP(1), SP/RP(1)

### **User's Real Draft**
- Coming up in 2026
- Wants to practice against realistic AI
- Will use this to prep for actual money league

---

## Questions to Consider

1. **Should late-auction aggression be gradual or sudden?**
   - Gradual: Slowly increase max_bid as auction progresses
   - Sudden: Switch to "must spend" mode at 70% complete

2. **How to handle position preferences vs budget urgency?**
   - If Forest Rangers hates SP (-52%) but has $100/4 slots, should they still bid on Wheeler?
   - Probably yes - budget urgency should override position preference in late auction

3. **What about $1 picks?**
   - Real auctions have lots of $1 picks at the end
   - But only when everyone is broke (all teams at $10-15 remaining)
   - If someone has $50 left, no $1 picks should happen!

---

## Development Notes

**Python Version:** 3.7+  
**Dependencies:** Only `json`, `random` (stdlib)  
**User Environment:** Windows (tested on `C:\Users\jonza\OneDrive\Desktop\fb_drafts\`)

**User reported:**
- Nomination rotation bug (FIXED - each owner nominates once per round)
- Budget spending bug (STILL BROKEN - teams end with $100+)

---

## What I Need Claude Code to Do

1. **Analyze** the buggy `should_bid()` and `get_max_bid()` methods
2. **Fix** the logic to properly account for budget urgency
3. **Test** with `watch_auction.py` to ensure final budgets are $0-20
4. **Verify** AI bids realistically in late auction (matches `$/slot` targets)

The math is tricky - needs to:
- Respect historical position preferences (premium_pct)
- Account for auction phase (early vs late)
- Force spending when sitting on money late
- Still allow $1 picks when everyone is broke

---

## Good Luck! 🎯

Let me know if you need any clarification on the auction mechanics, data structure, or expected behavior!
