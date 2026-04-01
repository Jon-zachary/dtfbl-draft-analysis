# Downtown Fantasy Baseball League - Rules Summary

## League Structure
- **8 teams**, 14-player active rosters per team
- **Players**: National League only
- **FAAB Budget**: $150 per team per season
- **Roster Positions**: C, 1B, 1B, 2B, SS, SS, 3B, 3B, 3B, OF, OF, OF, DH, SP, SP, RP, SP/RP (17 total)
- **Injury Replacements**: Unlimited (don't count toward 14-player limit)

## Scoring System
### Batting (per occurrence)
- Single: 1.5 points
- Double: 2 points
- Triple: 3 points
- Home Run: 5 points
- Run: 1.5 points
- RBI: 1.5 points
- Stolen Base: 3 points
- Walk: 1 point
- Error: -1 point

### Pitching (per occurrence)
- Win: 7 points
- Loss: -5 points
- Save: 7 points
- Strikeout: 0.75 points
- Walk Allowed: -1 point
- Quality Start: 5 points
- Complete Game: 3 points (bonus)
- Shutout: 3 points (bonus)
- No-Hitter: 10 points (bonus)
- Perfect Game: 10 points (bonus)

## Waiver/Acquisition System

### Block Periods
- Created by commissioner with open/close dates
- Statuses: UPCOMING → OPEN (bidding allowed) → CLOSED (no more bids) → PROCESSED (results finalized)

### Bidding Rules
1. **Blind Bidding**: All bids secret until processing
2. **FAAB**: Bid any amount up to remaining budget
3. **Public Block**: Team publicly drops a player, anyone can bid on them
4. **Secret Bids**: Standard free agent pickups (drop not announced)
5. **Tiebreaker**: Lower priority number wins (1 beats 2)
6. **Priority**: Increases each week (1→2→3), resets to 1 after winning bid

### Bid Processing
- Highest bid wins player
- Winner: FAAB deducted, player added, dropped player released
- Losers: Bids refunded, no roster changes
- Conflicts: If dropped player is bid on by others, both bids can fail

### Injury Replacements
- Add temporary replacements for injured players (status: DL)
- Replacements don't count toward 14-player limit
- **Risk**: Other teams can public block your replacement and steal them
- Auto-released when injured player returns to active

## Position Eligibility
- Players eligible for all positions listed (e.g., "2B,SS" can play either)
- Eligibility updated from MLB API
- Multi-position players valuable for roster flexibility

## Draft Process
- Initial draft loaded from Excel file (dtfbbl2025.xlsx)
- Each team drafts 14 players to fill all positions
- Draft order and rounds tracked in Excel

## Season Management
- Commissioner creates season via admin panel
- Loads draft from Excel or manually assigns players
- Manages block periods throughout season
- Processes waiver bids and resolves conflicts
