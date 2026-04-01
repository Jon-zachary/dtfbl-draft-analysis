# DTFBL League Constitution

## League Overview
- **League Name**: DTFBL (Down to Fantasy Baseball League)
- **League Type**: National League Only
- **Season**: Year-round (follows MLB season)
- **Scoring**: Custom points-based system

---

## Roster Configuration

### Active Roster (14 Players)
- **C** - Catcher (1)
- **1B** - First Base (1)
- **2B** - Second Base (1)
- **SS** - Shortstop (1)
- **3B** - Third Base (1)
- **OF** - Outfield (3)
- **DH** - Designated Hitter (1)
- **SP** - Starting Pitcher (3)
- **RP** - Relief Pitcher (1)
- **RP/SP** - Swing Position (1)

### Disabled List
- **DL Spots**: Unlimited
- **DTFBL IR**: 14-day internal injured reserve for temporary injuries

---

## Scoring System

### Hitting Categories
| Category | Points |
|----------|--------|
| Single | 1 |
| Double | 2 |
| Triple | 4 |
| Home Run | 4 |
| Run | 1 |
| RBI | 1 |
| Stolen Base | 1 |
| Walk | 1 |
| Error | -1 |

### Pitching Categories
| Category | Points |
|----------|--------|
| Win | 12 |
| Loss | -3 |
| Save | 8 |
| Strikeout | 1 |
| Walk | -1 |
| Quality Start | 2 |
| Complete Game | 5 |
| Shutout | 5 |
| No Hitter | 10 |
| Perfect Game | 20 |

---

## Free Agent Acquisition Budget (FAAB)

### Budget Details
- **Total Budget**: $150 per team per season
- **Minimum Bid**: $5
- **Carry Over**: No (resets each season)

### Waiver Period Timeline
- **Tuesday 12:00 PM**: Block opens - teams can put players on the waiver block
- **Saturday 11:59 PM**: Block closes - no more players can be added to block
- **Next Tuesday 12:00 PM**: Bidding closes - bids are processed

### Bidding Rules

#### Public Block System
- **First Bid**: Team that first declares interest in a player must make it PUBLIC
  - Player goes "on the block" (visible to all teams)
  - Must specify which player they're dropping
  - Shows priority if bidding on multiple players

#### Private Bidding
- **Subsequent Bids**: Other teams can bid on blocked players SECRETLY
  - No public announcement required
  - Bid amounts hidden from all other teams
  - Can "snipe" players already on the block

#### Bid Processing
- **Highest Bid Wins**: Ties broken by team priority order
- **Priority System**: If team bids on multiple players:
  - Priority 1 (highest) processed first
  - If Priority 1 succeeds, lower priority bids cancelled
  - If Priority 1 fails, Priority 2 processed, etc.
- **Commissioner Tie-Breaking**: In event of identical bids, commissioner decides OR second round of bidding

#### Weekly Adds
- Teams can make multiple weekly acquisitions
- Each acquisition must go through the block/bidding process
- No limits on number of moves (subject to FAAB availability)

---

## Player Eligibility

### Position Eligibility
- Players gain position eligibility based on MLB appearances
- Multi-position eligibility allowed
- Current season: 71 players have multi-position eligibility

### Position Examples
- Grant Holmes: SP, RP
- Jake Burger: 1B, 3B, DH
- Willson Contreras: C, DH

---

## Roster Management

### Minimum Hold Periods
Players must be held for minimum time before dropping:
- **Hitters**: 7 days (1 week)
- **Starting Pitchers (SP)**: 14 days (2 weeks)
- **Relief Pitchers (RP)**: 7 days (1 week)

### Player Status Tracking
- **Active**: On active roster
- **IL (Injured List)**: MLB injured list (10-day, 60-day, etc.)
- **Paternity Leave**: Short-term absence
- **Suspension**: League/team suspension
- **Sent Down**: Optioned to minors
- **DTFBL IR**: Internal 14-day injury reserve

### Injury Replacements
- Can add temporary replacement for injured players
- Replacement is FREE (no FAAB required)
- Must specify reason (injury, paternity, etc.)
- Tracks which roster spot is being temporarily filled

---

## Trading

### American League Trades
- **Auto-Detection**: System should flag AL trades
- NL-only league, so AL players not eligible
- Commissioner approval required for trades involving AL players

---

## League Schedule

### Season Timeline
- **Opening Day**: MLB Opening Day
- **Weekly Blocks**: Every Tuesday through following Tuesday
- **Trade Deadline**: MLB trade deadline
- **Season End**: End of MLB regular season
- **Playoffs**: Post-season scoring (if applicable)

---

## Commissioner Tools

### Powers
- Process weekly bidding
- Override transactions (with reason)
- Manually add/drop players
- Adjust FAAB budgets
- View all blind bids
- Handle tie-breaking decisions
- League settings management

### Approval Requirements
- AL trade detection
- Suspension/sent-down notifications
- Disputed transactions

---

## Technical Implementation

### Database
- SQLite database with full transaction history
- 637+ players (268 hitters, 369 pitchers)
- Daily stats tracking
- Injury status synchronization with MLB API

### Automation
- Daily stats import from MLB API
- Injury status updates
- Position eligibility calculations
- Scoring engine with historical recalculation
- Block period auto-creation

### Features
- Web interface (FastAPI + Jinja2)
- REST API with auto-documentation
- Real-time FAAB tracking
- Transaction audit trail
- Multi-position eligibility support
- Priority-based bidding system

---

## Additional Rules

### Fair Play
- No collusion between teams
- Commissioner has final say on disputes
- Transaction history is permanent (audit trail)

### Season Continuity
- Rosters carry over between seasons (where applicable)
- FAAB resets each season
- Player eligibility updated annually

---

**Last Updated**: January 18, 2026
**Version**: 2.0 (Bidding System Implementation)
