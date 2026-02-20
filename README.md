# DTFBL Historical Draft Analysis & Mock Auction Simulator
## 16 Years of Auction Data (2009-2025) - CORRECTED ANALYSIS

**Generated:** February 2026  
**Data:** 1,354 auction picks across 14 seasons  
**Teams:** 7 active franchises  
**Analysis Method:** Per-roster-slot comparison (accounts for 3 OF, 3 SP, etc.)

---

## ⚠️ IMPORTANT: Why "CORRECTED"?

**Original analysis had a CRITICAL FLAW:** It didn't account for roster construction!

**WRONG:** "Forest Rangers allocates 35% to OF" → Sounds like he LOVES OF  
**RIGHT:** "Forest Rangers pays $31 per OF vs $24 league average" → +27% premium (still high but not crazy)

**Why this matters:**
- You draft **3 OF** but only **1 SS**
- OF SHOULD get ~3x the budget by default
- The question is: **How much PER PLAYER** vs league average?

**This corrected analysis:**
✅ Normalizes for roster slots (3 OF, 3 SP, 1 C, 1 SS, etc.)  
✅ Shows **per-player premiums/discounts**  
✅ Reveals TRUE exploitable patterns  
✅ AI opponents use corrected data

See OWNER_PROFILES.md for complete corrected analysis!

---

## 🚀 Quick Start

```bash
# Watch AI opponents draft
python3 watch_auction.py

# Practice interactively
python3 mock_auction.py
```

---

## 🔥 THE REAL EXPLOITS (Top 3)

### 1. **David's Devils** - Most Exploitable
- Pays $31 for closers when league avg is $18 (+72%!)
- Pays $42 for 1B when league avg is $28 (+48%)
- **BUT** pays $11 for SS when league avg is $24 (-53%!)

**Strategy:** Nominate Edwin Diaz, Pete Alonso early. Steal Lindor late.

### 2. **Jake's Snakes** - The Catcher Lover
- Pays $23 for catchers when league avg is $13 (+72%!)
- **BUT** pays $7 for 2B when league avg is $15 (-52%!)

**Strategy:** Nominate William Contreras → he'll pay $40. Steal Ketel Marte for $5.

### 3. **Forest Rangers** - Corner Power
- Pays $34 for 3B when league avg is $23 (+49%!)
- **BUT** pays $8 for SP when league avg is $17 (-52%!)

**Strategy:** Nominate Manny Machado. Steal Zack Wheeler cheap.

---

## 📁 What's Included

- **all_drafts_2009_2025.csv** - Raw data (1,354 picks)
- **OWNER_PROFILES.md** - Detailed corrected profiles
- **owner_profiles.json** - Machine-readable data
- **mock_auction.py** - Interactive practice tool
- **watch_auction.py** - Automated simulation
- **FINAL_2026_DRAFT_BOARD.csv** - VORP rankings
- **position_analysis.json** - League baselines

---

## 📊 Roster Structure

| Position | Slots | League Avg $ |
|----------|-------|--------------|
| C | 1 | $13 |
| 1B | 1 | $28 |
| 2B | 1 | $15 |
| SS | 1 | $24 |
| 3B | 1 | $23 |
| **OF** | **3** | **$24** |
| **SP** | **3** | **$17** |
| RP | 1 | $18 |
| SP/RP | 1 | $9 |

---

## 💡 Draft Strategy

**EARLY (Picks 1-30):** Nominate players YOU DON'T WANT
- Make David's/Jon's fight over 1B
- Make Bert's/David's fight over closers
- Drain their budgets

**MID (Picks 31-70):** Buy your core at VORP values
- Get 1 elite scarce position (C or SS)
- Don't chase inflated prices
- Stay disciplined

**LATE (Picks 71-98):** Exploit the broke
- Steal positions people punted
- David's punts SS/OF → steal cheap
- Forest punts SP → steal aces
- Jake's punts 2B → steal Ketel Marte

---

## 🎯 Files to Bring to Draft

1. **OWNER_PROFILES.md** (print it!)
2. **FINAL_2026_DRAFT_BOARD.csv** (open on laptop)
3. **This README** (cheat sheet)

---

**Full documentation in OWNER_PROFILES.md**

**Ready to dominate!** 🏆⚾
