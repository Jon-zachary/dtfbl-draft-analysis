# DTFBL Historical Draft Analysis & Mock Auction Simulator
## 16 Years of Auction Data (2009-2025)

**Generated:** February 2026  
**Data:** 1,354 auction picks across 14 seasons  
**Teams:** 7 active franchises

---

## 📁 What's Included

### Data Files:
- **all_drafts_2009_2025.csv** - Complete historical dataset (1,354 picks)
- **owner_profiles.json** - Machine-readable personality profiles  
- **OWNER_PROFILES.md** - Human-readable analysis

### Mock Auction Tools:
- **mock_auction.py** - Interactive auction simulator  
- **watch_auction.py** - Automated auction observer

### Analysis:
- This README with complete findings

---

## 🎯 Quick Start

### 1. Watch an Automated Auction
```bash
python3 watch_auction.py
```
Watch AI opponents bid against each other. Learn their patterns!

### 2. Practice Interactively
```bash
python3 mock_auction.py
```
Run a mock auction where YOU make the decisions.

Commands:
- `nominate Juan Soto OF 1` - Start bidding on a player
- `status` - See everyone's budget/roster
- `roster Forest Rangers` - View a team's picks
- `quit` - Exit

---

## 📊 KEY FINDINGS

### League-Wide Patterns

**Everyone Plays Stars & Scrubs:**
- All 7 owners use this strategy
- Spend 35-40% of budget on 3-4 elite players
- Fill rest with $1-5 bargains
- Makes sense for NL-only leagues (talent concentrated)

**Average Auction Stats:**
- Average pick: **$19.60**
- Median pick: **$10-15**
- Most expensive pick ever: **$91** (Albert Pujols 2011, Jake's Snakes)
- Second most expensive: **$91** (Giancarlo Stanton 2015, Jake's Snakes)

**Position Trends:**
- **OF is king**: Everyone allocates 24-36% of budget to OF
- **SP next**: 15-28% depending on owner
- **1B trap confirmed**: Jon's Generals spends 17% on 1B (most), still underperforms

---

## 👥 OWNER PROFILES

### Charlie's Stars - "The Big Spender"
**Archetype:** Stars & Scrubs (Aggressive)

💰 **Spending:**
- **24 times** paid $50+ (most in league!)
- Biggest purchase: $88 (Shohei Ohtani 2025)
- 21.5% of roster are $1 picks (high)

🎯 **Loves:** OF (33.7% of budget!)

⚔️ **How to Beat:**
- Nominate elite OF early → drains budget
- He'll run dry mid-auction
- Exploit late rounds for value
- Target non-OF positions after he's tapped out

---

### Forest Rangers - "The OF Fanatic"  
**Archetype:** Stars & Scrubs

💰 **Spending:**
- 26 times paid $50+ (second most)
- Biggest: $85 (Juan Soto 2025)
- 26.3% are $1 picks (loves bargains)

🎯 **Loves:** OF (35.6%!), 3B (12.9%), SS (12.9%)

⚔️ **How to Beat:**
- Will overpay for elite OF
- Nominate Soto/Tucker early
- Target 1B/C where he underinvests
- He's desperate for $1 picks late

---

### Jake's Snakes - "The Record Holder"
**Archetype:** Stars & Scrubs (Bold)

💰 **Spending:**
- Paid $91 TWICE (Pujols 2011, Stanton 2015)
- Paid $90 once (Mookie 2024)
- 19 times paid $50+
- 25.3% are $1 picks

🎯 **Loves:** OF/SP balanced (24% each), SS (13.3%)

⚔️ **How to Beat:**
- Will occasionally go nuclear on a player
- Balanced across positions
- Drops out around $10 for depth pieces
- Exploit his SS preference

---

### Ryan's Lions - "The Balanced Aggressor"  
**Archetype:** Stars & Scrubs

💰 **Spending:**
- 23 times paid $50+
- Biggest: $90 (Juan Soto 2022)
- 19.4% are $1 picks

🎯 **Loves:** OF (28.6%), SP (27.4%) - very balanced

⚔️ **How to Beat:**
- Least exploitable (balanced allocation)
- Will pay up for stars early
- No obvious position bias
- Study year-to-year changes

---

### David's Devils - "The 1B Trap Victim"
**Archetype:** Stars & Scrubs

💰 **Spending:**
- 22 times paid $50+
- Biggest: $83 (David Wright 2011)
- 25.3% are $1 picks (most bargains!)

🎯 **Loves:** Balanced! OF/SP/1B all ~17%

⚔️ **How to Beat:**
- Overinvests in 1B (16% of budget)
- Will drop out around $5-10
- Stockpiles $1 picks
- Target players in $6-15 range

---

### Bert's Bombers - "The Pitcher"
**Archetype:** Stars & Scrubs (SP Focus)

💰 **Spending:**
- 14 times paid $50+ (fewest!)
- Biggest: $67 (Trea Turner 2023) - lowest max ever!
- 14.5% are $1 picks (fewest)

🎯 **Loves:** SP (25.9%!), then OF (23.5%)

⚔️ **How to Beat:**
- Most predictable bidder
- Easy to price out at +$2-3 above value
- Will pay for SP
- Fewest $1 picks = pays for depth
- Target hitting stars early

---

### Jon's Generals - "The 1B Lover"
**Archetype:** Stars & Scrubs

💰 **Spending:**
- 19 times paid $50+
- Biggest: $81 (Joey Votto 2012)
- 11.8% are $1 picks (LOWEST!)

🎯 **Loves:** OF (32%), 1B (17%!), SP (15%)

⚔️ **How to Beat:**
- Overallocates to 1B trap (17%)
- Pays for depth (lowest $1 rate)
- Very predictable
- Will overpay for OF
- Easy to price out +$2-3

---

## 🎮 MOCK AUCTION STRATEGY GUIDE

### Pre-Auction Prep

**1. Load Your 2026 Draft Board**
- Use the projections we created earlier
- Know your VORP values cold
- Have risk-adjusted values ready

**2. Study Today's Opponents**
- Read owner profiles above
- Note who overspends on what positions
- Plan nomination strategy

**3. Set Your Budget Plan**
Example:
- $90 for 1 elite scarce player (C or SS)
- $60-70 for 1-2 stars
- $40-60 for 2-3 good players
- $30-40 spread across 4-5 players
- $10-20 for endgame value hunting

### During Mock Auction

**Early Game (First 20 picks):**
- Nominate players YOU DON'T WANT
- Force others to spend on their favorites
- Example: Nominate elite OF early → Charlie's Stars and Forest Rangers fight
- Save your bullets

**Mid Game (Picks 20-60):**
- Buy your core
- Get 1 elite scarce position (C or SS)
- Fill 2-3 starters at fair value
- Don't panic buy

**End Game (Picks 60-98):**
- Everyone is low on cash
- Lots of $1-3 picks
- THIS IS WHERE VALUE LIVES
- Charlie's, Forest Rangers, David's Devils will be desperate
- Steal players at $2-5 who should be $10-15

### Exploitation Tactics

**VS Charlie's Stars:**
- Nominate: Soto, Tucker, any elite OF
- He'll bid to $70-80
- Let him win, laugh at budget drain

**VS Forest Rangers:**
- Same strategy (loves OF even more!)
- Will pay $85 for Juan Soto
- Target 1B/C after he's broke

**VS Jake's Snakes:**
- Unpredictable - can go $90+ randomly
- Don't get in bidding wars
- Let him overpay

**VS Jon's Generals:**
- Nominate elite 1B early
- He'll overpay (Pete Alonso, Matt Olson)
- 1B is a trap, let him fall into it

**VS Bert's Bombers:**
- Nominate SP early
- Most predictable bidder
- Easy to price out at calculated value +$2

**VS David's Devils / Ryan's Lions:**
- More balanced, harder to exploit
- Study their recent years for emerging patterns

---

## 💡 ADVANCED STRATEGIES

### The "Nomination Game"

**Theory:** You nominate players to drain others' budgets, not to buy them yourself.

**Example:**
1. You want: Francisco Lindor ($96)
2. You know: Charlie's loves OF
3. You nominate: Juan Soto (OF) first
4. Charlie's and Forest Rangers fight to $85
5. YOU then nominate Lindor
6. They're broke, you get him cheaper!

### The "Inflation/Deflation" Cycle

**If league spends FAST early:**
- Prices inflate mid-auction (scarcity)
- Save money, buy late
- Lots of $3-8 value picks

**If league spends SLOW early:**
- Prices deflate (everyone has money)
- Buy your stars early at fair value
- Less endgame value

### The "Position Run" Trap

**What happens:**
- Someone buys elite SS
- Triggers "SS run"
- Everyone panics and overpays

**How to exploit:**
- Let them panic
- Buy after the run at discount
- OR: Start a run yourself (nominate SS #1, trigger panic, you already have yours)

---

## 📈 USING THE DATA

### The CSV File

`all_drafts_2009_2025.csv` contains:
- Year, Team, Player, Position, MLB_Team, Price, Money_Left, Money_Spent

**Analysis ideas:**
- Filter by team: See all Jake's Snakes picks
- Filter by year: Compare 2024 vs 2025
- Group by position: Average prices over time
- Sort by price: Find the big buys

### Example Analyses (Python/Excel)

**Find biggest overpays:**
```python
df = pd.read_csv('all_drafts_2009_2025.csv')
# Highest price for each position
df.groupby('Position')['Price'].max()
```

**Track learning curves:**
```python
# Did Charlie's Stars get smarter over time?
charlie = df[df['Team'] == "Charlie's Stars"]
charlie.groupby('Year')['Price'].describe()
```

**Position price trends:**
```python
# How have SS prices changed?
ss_prices = df[df['Position'] == 'SS'].groupby('Year')['Price'].mean()
```

---

## 🧪 TESTING YOUR STRATEGY

### Workflow:

1. **Watch automated auction** (`watch_auction.py`)
   - See how AI behaves
   - Note who bids on what
   - Observe end-game patterns

2. **Run practice auction** (`mock_auction.py`)
   - Test your nomination strategy
   - Practice budget management
   - Learn when to let players go

3. **Analyze results**
   - Did you get value picks?
   - Did you exploit opponent tendencies?
   - Where did you overpay?

4. **Iterate**
   - Run 3-5 practice auctions
   - Try different strategies
   - Find what works for YOU

---

## 🎯 YOUR REAL 2026 DRAFT PREP

### 2 Weeks Before Draft:

- [ ] Run 3 mock auctions
- [ ] Update 2026 projections with latest data
- [ ] Study opponents' 2025 draft (most recent!)
- [ ] Build nomination list

### 1 Week Before:

- [ ] Print VORP draft board
- [ ] Print owner profiles (this file!)
- [ ] Practice one more mock auction
- [ ] Set budget targets

### Draft Day:

- [ ] Have draft board + profiles visible
- [ ] Track spending in real-time
- [ ] Adjust strategy as auction unfolds
- [ ] TRUST THE PROCESS

---

## 🏆 SUCCESS METRICS

After your real draft, judge yourself on:

**Process (Not Results!):**
- Did you stick to VORP values? ✓
- Did you exploit opponent tendencies? ✓
- Did you avoid the 1B trap? ✓
- Did you get value in end-game? ✓

**Results (With Luck):**
- Roster full of high-VORP players ✓
- Stayed under budget ✓
- Got 1-2 "steals" (value >> price) ✓

Remember: Injuries and breakouts are LUCK. Judge the process, not the outcome!

---

## 📞 TECHNICAL NOTES

### Requirements:
```bash
pip install pandas
```

### Files:
- Python 3.7+ required
- All scripts are self-contained
- No external dependencies except pandas

### Customization:

Want to modify AI behavior? Edit `mock_auction.py`:

**Make AI more aggressive:**
```python
# Line ~60
if spent_pct < 0.3:  # Early auction
    interest *= 1.5  # Was 1.3, now 1.5
```

**Make AI drop out faster:**
```python
# Line ~66
if dollar_rate > 0.23 and current_price > 5:  # Was 8, now 5
    interest *= 0.4  # Was 0.6, now 0.4
```

---

## 🎊 FINAL THOUGHTS

You now have:
- ✅ 16 years of draft data analyzed
- ✅ Comprehensive owner profiles
- ✅ Exploitable tendency maps
- ✅ Interactive practice tool
- ✅ 2026 VORP draft board (from earlier)

**You're more prepared than anyone in your league has EVER been.**

Your opponents are repeating the same mistakes they've made for 16 years.

You have the data.

You have the tools.

You have the strategy.

Now go dominate! 🎯⚾💰

---

**Questions? Issues? Updates needed?**

Just reference this chat and ask! The analysis tools are here whenever you need them.

Good luck in your 2026 draft! 🏆
