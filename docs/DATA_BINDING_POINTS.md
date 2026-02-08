# DNA Bet Engine - Data Binding Points
## Designer Handoff: Every Dynamic Element Catalogued

**For:** Design tool import (Figma, etc.)  
**Purpose:** Ensure all data flows are visually mapped  
**Date:** 2026-02-08

---

## LEGEND

| Symbol | Meaning |
|--------|---------|
| `{{variable}}` | Data from API |
| `{{#array}}` | Loop through array |
| `[action]` | User interaction |
| `{{?condition}}` | Conditional display |
| `{{>component}}` | Reusable component |

---

## SCREEN 1: LANDING PAGE
**Static: 85% | Dynamic: 15%**

### Header
```html
<div class="logo">
  <div class="logo-icon">🧬</div>           <!-- Static icon -->
  <span>DNA BET</span>                       <!-- Static text -->
</div>
<button>[menu]</button>                      <!-- Action: Open mobile menu -->
```
**Bindings:** None (static)

### Hero Section
```html
<span class="neon-text">{{hero.badge}}</span>     <!-- Default: "The Genetic Edge" -->
<h1>
  <span>{{hero.line1}}</span>                      <!-- Default: "PARLAY" -->
  <span class="neon-text">{{hero.line2}}</span>    <!-- Default: "INTELLIGENCE" -->
</h1>
<p>{{hero.subtitle}}</p>                           <!-- Default: Marketing copy -->

<!-- DNA Helix Animation -->
<div class="helix-container">                     <!-- CSS animation only -->
  {{#helix.dots}}                                  <!-- 12 rotating dots -->
    <div class="dot"></div>
  {{/helix.dots}}
</div>

<a href="{{cta.primary.url}}" class="neon-btn">    <!-- Default: "/app?screen=dashboard" -->
  {{cta.primary.text}}                             <!-- Default: "GET STARTED" -->
</a>
```
**Bindings:**
- `hero.badge` - String (marketing tagline)
- `hero.line1` - String (main title line 1)
- `hero.line2` - String (main title line 2 - neon)
- `hero.subtitle` - String (description)
- `cta.primary.url` - URL (destination)
- `cta.primary.text` - String (button text)

### How It Works Section
```html
<h2>{{howItWorks.title}}</h2>                     <!-- Default: "HOW IT WORKS" -->
{{#howItWorks.steps}}                             <!-- Array of 3 steps -->
  <div class="step">
    <div class="step-number">{{number}}</div>     <!-- 01, 02, 03 -->
    <h3>{{title}}</h3>                             <!-- Step title -->
    <p>{{description}}</p>                         <!-- Step description -->
  </div>
{{/howItWorks.steps}}
```
**Bindings:**
- `howItWorks.title` - String
- `howItWorks.steps[]` - Array
  - `number` - String ("01", "02", "03")
  - `title` - String
  - `description` - String

### Core Protocols Section
```html
<h2>{{protocols.title}}</h2>                      <!-- Default: "CORE PROTOCOLS" -->
{{#protocols.features}}                           <!-- Array of 4 features -->
  <div class="feature-card">
    <div class="icon">{{icon}}</div>              <!-- Emoji/icon -->
    <h4>{{title}}</h4>                             <!-- Feature name -->
    <p>{{stat}}</p>                                <!-- Statistic -->
  </div>
{{/protocols.features}}
```
**Bindings:**
- `protocols.title` - String
- `protocols.features[]` - Array
  - `icon` - String (emoji)
  - `title` - String ("Accuracy", "Speed", etc.)
  - `stat` - String ("98.4% predictive precision")

### Pricing Tiers Section
```html
<h2>{{pricing.title}}</h2>                        <!-- Default: "ACCESS TIERS" -->
{{#pricing.tiers}}                                <!-- Array of 3 tiers -->
  <div class="tier-card {{?popular}}popular{{/popular}}">
    {{?popular}}<span class="badge">Popular</span>{{/popular}}
    <h3>{{name}}</h3>                              <!-- "RECRUIT", "ELITE", "EXOME" -->
    <p class="subtitle">{{subtitle}}</p>           <!-- Tier description -->
    <div class="price">
      <span class="amount">${{price}}</span>
      <span class="period">/{{billingPeriod}}</span>
    </div>
    {{#features}}                                  <!-- Array of features -->
      <li>{{text}}</li>
    {{/features}}
    <a href="{{cta.url}}" class="btn">{{cta.text}}</a>
  </div>
{{/pricing.tiers}}
```
**Bindings:**
- `pricing.title` - String
- `pricing.tiers[]` - Array
  - `popular` - Boolean (show badge)
  - `name` - String (tier name)
  - `subtitle` - String (tier tagline)
  - `price` - Number
  - `billingPeriod` - String ("mo", "year")
  - `features[]` - Array of strings
  - `cta.url` - String (Stripe/checkout link)
  - `cta.text` - String ("SELECT TIER")

### Footer
```html
<div class="logo">{{footer.logo}}</div>
{{#footer.social}}                                <!-- Social links -->
  <a href="{{url}}">{{icon}}</a>
{{/footer.social}}
{{#footer.links}}                                 <!-- Footer nav -->
  <a href="{{url}}">{{text}}</a>
{{/footer.links}}
<p>{{footer.copyright}}</p>
```
**Bindings:**
- `footer.logo` - String (logo HTML)
- `footer.social[]` - Array
- `footer.links[]` - Array
- `footer.copyright` - String

---

## SCREEN 2: DASHBOARD
**Static: 20% | Dynamic: 80%**

### Header
```html
<div>
  <span class="label">{{header.label}}</span>     <!-- "DNA Engine" -->
  <h1>{{header.title}}</h1>                        <!-- "DASHBOARD" -->
</div>
<button class="notification">
  🔔
  {{?notifications.unread > 0}}
    <span class="badge">{{notifications.unread}}</span>
  {{/notifications.unread}}
</button>
<div class="avatar">
  {{?user.avatarUrl}}
    <img src="{{user.avatarUrl}}">
  {{:else}}
    👤
  {{/user.avatarUrl}}
</div>
```
**Bindings:**
- `header.label` - String
- `header.title` - String
- `notifications.unread` - Number
- `user.avatarUrl` - String (URL or null)

### Balance Card
```html
<span class="label">{{balance.label}}</span>      <!-- "Total Balance" -->
<span class="tier-badge">{{user.tier}} Tier</span>
<h2>${{user.balance}}</h2>
<div class="change">
  <span class="pct">{{weeklyChange.direction}}{{weeklyChange.pct}}%</span>
  <span class="period">{{weeklyChange.period}}</span>
</div>
```
**Bindings:**
- `balance.label` - String
- `user.tier` - String ("Pro", "Elite", etc.)
- `user.balance` - Number (formatted: 12,840.50)
- `weeklyChange.direction` - String ("📈+", "📉-")
- `weeklyChange.pct` - Number
- `weeklyChange.period` - String ("this week")

### Primary CTA
```html
<a href="{{cta.browse.url}}">
  {{cta.browse.icon}} {{cta.browse.text}}
</a>
```
**Bindings:**
- `cta.browse.url` - String ("/app?screen=browse")
- `cta.browse.icon` - String (emoji)
- `cta.browse.text` - String

### Quick Stats Grid
```html
{{#stats}}                                        <!-- Array of 2 stats -->
  <div class="stat-card">
    <div class="icon">{{icon}}</div>              <!-- Background decoration -->
    <span class="label">{{label}}</span>
    <div class="value">
      <span class="number">{{value}}</span>
      <span class="suffix">{{suffix}}</span>
    </div>
  </div>
{{/stats}}
```
**Bindings:**
- `stats[]` - Array
  - `icon` - String (emoji for decoration)
  - `label` - String ("Win Rate", "Total Parlays")
  - `value` - Number (68.5, 142)
  - `suffix` - String ("%", "Lifetime")

### Active Bets List
```html
<div class="section-header">
  <h3>
    <span class="live-dot"></span>
    {{betsSection.title}}
  </h3>
  <a href="{{betsSection.viewAllUrl}}">{{betsSection.viewAllText}}</a>
</div>

{{#activeBets}}                                   <!-- Array of bet cards -->
  <div class="bet-card {{?isLive}}live{{/isLive}}">
    <div class="header">
      <div class="teams">
        <img src="{{sportIcon}}">
        <span>{{game.name}}</span>
        {{?isLive}}
          <span class="live-badge">LIVE</span>
        {{/isLive}}
      </div>
      <span class="odds">{{odds}}</span>
    </div>
    
    {{#legs}}                                     <!-- Array of legs -->
      <div class="leg">
        <span class="market">{{market}}</span>
        <span class="separator">|</span>
        <span class="detail">{{detail}}</span>
      </div>
    {{/legs}}
    
    <div class="divider"></div>
    
    <div class="footer">
      <div>
        <span class="label">Wager</span>
        <span class="amount">${{wager}}</span>
      </div>
      <div class="payout">
        <span class="label">Est. Payout</span>
        <span class="amount">${{potentialPayout}}</span>
      </div>
    </div>
    
    {{?hasProgress}}
      <div class="progress">
        <div class="bar" style="width: {{progressPct}}%"></div>
      </div>
    {{/hasProgress}}
  </div>
{{/activeBets}}

{{?activeBets.length === 0}}
  <div class="empty-state">
    <p>{{emptyState.message}}</p>
    <a href="{{emptyState.cta.url}}" class="btn">
      {{emptyState.cta.text}}
    </a>
  </div>
{{/activeBets}}
```
**Bindings:**
- `betsSection.title` - String ("ACTIVE PROTOCOLS")
- `betsSection.viewAllUrl` - String
- `betsSection.viewAllText` - String ("View All")
- `activeBets[]` - Array
  - `isLive` - Boolean
  - `sportIcon` - String (emoji or icon URL)
  - `game.name` - String ("Lakers vs Heat")
  - `odds` - String ("+240", "-110")
  - `legs[]` - Array
    - `market` - String ("Spread", "Total")
    - `detail` - String ("Lakers -4.5")
  - `wager` - Number
  - `potentialPayout` - Number
  - `hasProgress` - Boolean
  - `progressPct` - Number (0-100)
- `emptyState.message` - String
- `emptyState.cta.url` - String
- `emptyState.cta.text` - String

### Bottom Navigation
```html
{{#nav.items}}                                    <!-- Array of 4 nav items -->
  <a href="{{url}}" class="{{?active}}active{{/active}}">
    <span class="icon">{{icon}}</span>
    {{?active}}<span class="indicator"></span>{{/active}}
    <span class="label">{{label}}</span>
  </a>
{{/nav.items}}
```
**Bindings:**
- `nav.items[]` - Array
  - `url` - String
  - `icon` - String (emoji)
  - `label` - String ("Home", "Browse", etc.)
  - `active` - Boolean

---

## SCREEN 3: BROWSE (Bet Placement)
**Static: 30% | Dynamic: 70%**

### Header
```html
<a href="{{nav.back.url}}" class="back">←</a>
<h1>{{header.title}}</h1>                         <!-- "NEW BET PROTOCOL" -->
<div class="live-indicator"></div>
```
**Bindings:**
- `nav.back.url` - String
- `header.title` - String

### Sport Selector
```html
<div class="section-header">
  <h2>{{sportsSection.title}}</h2>
  <span class="badge">{{sportsSection.liveBadge}}</span>
</div>
<div class="sport-grid">
  {{#sports}}                                     <!-- Array of 6 sports -->
    <button class="sport-chip {{?active}}active{{/active}} {{?hasLiveGames}}live{{/hasLiveGames}}"
            onclick="filterGames('{{id}}')">
      {{?hasLiveGames}}<span class="live-dot"></span>{{/hasLiveGames}}
      <span class="icon">{{icon}}</span>
      <span class="name">{{name}}</span>
    </button>
  {{/sports}}
</div>
```
**Bindings:**
- `sportsSection.title` - String ("SELECT LEAGUE")
- `sportsSection.liveBadge` - String ("LIVE FEED ACTIVE")
- `sports[]` - Array
  - `id` - String ("nba", "nfl")
  - `name` - String ("NBA", "NFL")
  - `icon` - String (emoji)
  - `active` - Boolean
  - `hasLiveGames` - Boolean (show live dot)

### Featured Events
```html
<div class="section-header">
  <h2>{{gamesSection.title}}</h2>
  <a href="{{gamesSection.viewAllUrl}}">{{gamesSection.viewAllText}}</a>
</div>

{{#featuredGames}}                                <!-- Array of game cards -->
  <div class="game-card {{?isLive}}live{{/isLive}}">
    <div class="header">
      <div class="meta">
        <span class="sport-icon">{{sportIcon}}</span>
        <span>{{gameType}}</span>
      </div>
      {{?isLive}}
        <div class="live-badge">
          <span class="dot"></span>
          LIVE • {{quarter}} {{timeRemaining}}
        </div>
      {{:else}}
        <span class="start-time">{{startTime}}</span>
      {{/isLive}}
    </div>
    
    <div class="teams">
      <div class="team home">
        <span class="name">{{homeTeam.code}}</span>
        <span class="full-name">{{homeTeam.name}}</span>
        {{?isLive}}<span class="score">{{homeScore}}</span>{{/isLive}}
      </div>
      <div class="vs">
        <span>VS</span>
        <span class="venue">{{venue}}</span>
      </div>
      <div class="team away">
        <span class="name">{{awayTeam.code}}</span>
        <span class="full-name">{{awayTeam.name}}</span>
        {{?isLive}}<span class="score">{{awayScore}}</span>{{/isLive}}
      </div>
    </div>
    
    <div class="odds-grid">
      {{#quickOdds}}                              <!-- 3 quick bet buttons -->
        <button class="odds-btn" onclick="quickBet('{{market}}')">
          <span class="label">{{marketLabel}}</span>
          <span class="line">{{line}}</span>
          <span class="odds">{{odds}}</span>
        </button>
      {{/quickOdds}}
    </div>
    
    <a href="{{cta.url}}" class="btn">
      {{cta.text}} →
    </a>
  </div>
{{/featuredGames}}
```
**Bindings:**
- `gamesSection.title` - String ("FEATURED TARGETS")
- `gamesSection.viewAllUrl` - String
- `gamesSection.viewAllText` - String
- `featuredGames[]` - Array
  - `isLive` - Boolean
  - `sportIcon` - String
  - `gameType` - String ("Regular Season")
  - `quarter` - String ("Q3")
  - `timeRemaining` - String ("8:42")
  - `startTime` - String ("20:30 EST")
  - `homeTeam.code` - String ("LAL")
  - `homeTeam.name` - String ("Lakers")
  - `homeScore` - Number
  - `awayTeam.code` - String ("GSW")
  - `awayTeam.name` - String ("Warriors")
  - `awayScore` - Number
  - `venue` - String ("Crypto.com")
  - `quickOdds[]` - Array
    - `market` - String
    - `marketLabel` - String ("Spread", "Total")
    - `line` - String/Number ("-4.5", "O 224")
    - `odds` - String ("-110", "LIVE")
  - `cta.url` - String
  - `cta.text` - String ("SELECT EVENT TARGET")

### AI Insight Banner
```html
<div class="insight-banner">
  <div class="divider"></div>
  <div class="content">
    <div>
      <span class="badge">{{insight.badge}}</span>
      <p>{{insight.text}}</p>
    </div>
    <button class="icon-btn">
      {{insight.icon}}
    </button>
  </div>
</div>
```
**Bindings:**
- `insight.badge` - String ("AI INSIGHT")
- `insight.text` - String ("Lakers spread has 82% probability")
- `insight.icon` - String (emoji)

### Bottom Navigation
```html
{{#nav.items}}
  <a href="{{url}}" class="{{?active}}active{{/active}}">
    <span class="icon">{{icon}}</span>
    <span class="label">{{label}}</span>
  </a>
{{/nav.items}}
```
**Bindings:** Same as dashboard

---

## SCREEN 4: BUILDER (Parlay Builder)
**Static: 25% | Dynamic: 75%**

### Header
```html
<a href="{{nav.back.url}}" class="back">←</a>
<h1>{{header.title}}</h1>                         <!-- "BUILD PARLAY" -->
<button class="more">⋯</button>
```
**Bindings:**
- `nav.back.url` - String
- `header.title` - String

### Game Matchup Card
```html
<div class="matchup-card">
  <div class="accent-line"></div>
  
  <div class="header">
    <span class="meta">{{game.sport}} • {{game.startTime}}</span>
    <div class="live-badge">
      <span class="dot"></span>
      {{game.liveBadgeText}}
    </div>
  </div>
  
  <div class="teams">
    <div class="team">
      <div class="logo" style="background: {{homeTeam.color}}20; border-color: {{homeTeam.color}}40;">
        {{homeTeam.emoji}}
      </div>
      <span class="code">{{homeTeam.code}}</span>
      <span class="name">{{homeTeam.name}}</span>
    </div>
    <div class="vs">VS</div>
    <div class="team">
      <div class="logo" style="background: {{awayTeam.color}}20; border-color: {{awayTeam.color}}40;">
        {{awayTeam.emoji}}
      </div>
      <span class="code">{{awayTeam.code}}</span>
      <span class="name">{{awayTeam.name}}</span>
    </div>
  </div>
</div>
```
**Bindings:**
- `game.sport` - String ("NBA")
- `game.startTime` - String ("Tonight 7:30 PM")
- `game.liveBadgeText` - String ("Live Odds")
- `homeTeam.code` - String ("LAL")
- `homeTeam.name` - String ("Lakers")
- `homeTeam.color` - String (hex color)
- `homeTeam.emoji` - String
- `awayTeam.code` - String ("GSW")
- `awayTeam.name` - String ("Warriors")
- `awayTeam.color` - String (hex color)
- `awayTeam.emoji` - String

### Market Tabs
```html
<div class="market-tabs">
  {{#markets}}                                    <!-- Array of market tabs -->
    <button class="tab {{?active}}active{{/active}}"
            onclick="selectMarket('{{id}}')">
      {{label}}
    </button>
  {{/markets}}
</div>
```
**Bindings:**
- `markets[]` - Array
  - `id` - String ("main", "props", "quarters", "halves")
  - `label` - String ("MAIN LINES", "PLAYER PROPS")
  - `active` - Boolean

### Odds Grid
```html
<div class="odds-header">
  <span>Team</span>
  <span>Spread</span>
  <span>Total</span>
  <span>Money</span>
</div>

{{#teams}}                                        <!-- 2 teams -->
  <div class="odds-row">
    <span class="team-name">{{name}}</span>
    
    <button class="odds-cell {{?spread.selected}}selected{{/spread.selected}}"
            onclick="toggleLeg('{{id}}', 'spread')">
      <span class="line">{{spread.line}}</span>
      <span class="odds">{{spread.odds}}</span>
    </button>
    
    <button class="odds-cell {{?total.selected}}selected{{/total.selected}}"
            onclick="toggleLeg('{{id}}', 'total')">
      <span class="line">{{total.line}}</span>
    </button>
    
    <button class="odds-cell {{?ml.selected}}selected{{/ml.selected}}"
            onclick="toggleLeg('{{id}}', 'ml')">
      <span class="line">{{ml.odds}}</span>
    </button>
  </div>
{{/teams}}

{{#playerProps}}                                  <!-- Array if market=props -->
  <div class="prop-row">
    <span class="player">{{playerName}}</span>
    <span class="stat">{{statType}}</span>
    <div class="prop-buttons">
      <button onclick="addProp('{{id}}', 'over')">
        Over {{line}} ({{overOdds}})
      </button>
      <button onclick="addProp('{{id}}', 'under')">
        Under {{line}} ({{underOdds}})
      </button>
    </div>
  </div>
{{/playerProps}}
```
**Bindings:**
- `teams[]` - Array (2 items)
  - `id` - String
  - `name` - String ("LAKERS", "WARRIORS")
  - `spread.line` - String/Number
  - `spread.odds` - String
  - `spread.selected` - Boolean
  - `total.line` - String
  - `total.selected` - Boolean
  - `ml.odds` - String
  - `ml.selected` - Boolean
- `playerProps[]` - Array (optional)
  - `playerName` - String ("LeBron James")
  - `statType` - String ("Points", "Rebounds")
  - `line` - Number (25.5)
  - `overOdds` - String ("-115")
  - `underOdds` - String ("-115")

### Parlay Slip
```html
<div class="slip-header">
  <h3>
    {{slip.title}}
    <span class="count">{{slip.legCount}}</span>
  </h3>
  <button class="clear" onclick="clearSlip()">
    {{slip.clearText}}
  </button>
</div>

{{#slip.legs}}                                    <!-- Array of legs -->
  <div class="leg-card" style="border-color: {{accentColor}};">
    <button class="remove" onclick="removeLeg('{{id}}')">✕</button>
    
    <div class="leg-header">
      <span class="market" style="color: {{accentColor}};">
        {{marketType}}
      </span>
      <span class="divider">|</span>
      <span class="game">{{gameName}}</span>
    </div>
    
    <div class="leg-body">
      <div>
        <span class="selection">{{selection}}</span>
        <span class="category">{{category}}</span>
      </div>
      <span class="odds">{{odds}}</span>
    </div>
  </div>
{{/slip.legs}}

{{?slip.legs.length === 0}}
  <div class="empty-slip">
    <p>{{slip.emptyText}}</p>
  </div>
{{/slip.legs}}
```
**Bindings:**
- `slip.title` - String ("PARLAY SLIP")
- `slip.legCount` - Number
- `slip.clearText` - String ("Clear All")
- `slip.legs[]` - Array
  - `id` - String
  - `accentColor` - String (hex)
  - `marketType` - String ("Spread", "Player Points")
  - `gameName` - String ("Lakers vs Warriors")
  - `selection` - String ("Lakers -4.5", "L. James O 25.5")
  - `category` - String ("Main Lines", "Player Props")
  - `odds` - String ("-110", "-115")
- `slip.emptyText` - String

### Wager Summary
```html
<div class="summary-card">
  <div class="row">
    <span>{{summary.oddsLabel}}</span>
    <span class="odds">{{summary.totalOdds}}</span>
  </div>
  
  <div class="wager-input">
    <label>{{summary.wagerLabel}}</label>
    <div class="input-wrapper">
      <span class="currency">$</span>
      <input type="number" 
             value="{{wager.amount}}" 
             oninput="updatePayout(this.value)">
      <button class="max" onclick="setMaxWager()">
        {{wager.maxLabel}}
      </button>
    </div>
  </div>
  
  <div class="row payout">
    <span>{{summary.payoutLabel}}</span>
    <div class="amount">
      <span class="value">${{payout.amount}}</span>
      <span class="note">{{payout.note}}</span>
    </div>
  </div>
</div>
```
**Bindings:**
- `summary.oddsLabel` - String ("Total Odds")
- `summary.totalOdds` - String ("+264")
- `summary.wagerLabel` - String ("Wager Amount")
- `wager.amount` - Number (50.00)
- `wager.maxLabel` - String ("MAX")
- `summary.payoutLabel` - String ("Est. Payout")
- `payout.amount` - String (calculated: "182.00")
- `payout.note` - String ("Incl. Wager")

### Place Bet Button
```html
<button class="place-bet-btn" onclick="placeBet()">
  {{cta.placeBet.text}} →
</button>
```
**Bindings:**
- `cta.placeBet.text` - String ("PLACE BET")

### Bottom Navigation
```html
{{#nav.items}}
  <a href="{{url}}" class="{{?active}}active{{/active}}">
    {{?isCenter}}
      <div class="fab">
        <span class="icon">{{icon}}</span>
      </div>
    {{:else}}
      <span class="icon">{{icon}}</span>
    {{/isCenter}}
    <span class="label">{{label}}</span>
  </a>
{{/nav.items}}
```
**Bindings:**
- `nav.items[]` - Array
  - Same as dashboard PLUS:
  - `isCenter` - Boolean (for FAB style)

---

## DATA FLOW SUMMARY

### API Endpoints Needed

| Endpoint | Used By | Status |
|----------|---------|--------|
| `GET /api/user/me` | Dashboard | ✅ Mock exists |
| `GET /api/user/bets` | Dashboard | ✅ Mock exists |
| `GET /api/user/stats` | Dashboard | ⚠️ Hardcoded |
| `GET /api/sports` | Browse | ✅ Mock exists |
| `GET /api/games` | Browse | ✅ Mock exists |
| `GET /api/odds/{id}` | Browse, Builder | ✅ Mock exists |
| `POST /api/evaluate` | Builder | ✅ Exists |
| `GET /api/insights` | Browse | ❌ Not built |
| `GET /api/notifications` | Dashboard | ❌ Not built |

### State Management

| State | Location | Persistence |
|-------|----------|-------------|
| Selected sport | Client (URL param) | URL |
| Parlay slip | Client (JS variable) | localStorage? |
| User auth | Cookie/Header | Server session |
| Active filters | Client | URL |

---

## DESIGNER CHECKLIST

### For Each Screen:
- [ ] All `{{variables}}` mapped to data model
- [ ] All `{{#arrays}}` show example with 3+ items
- [ ] All `{{?conditions}}` show both states
- [ ] All `[actions]` have click targets defined
- [ ] Empty states designed
- [ ] Loading states designed
- [ ] Error states designed

### Responsive Breakpoints:
- [ ] Mobile: 375px
- [ ] Tablet: 768px  
- [ ] Desktop: 1440px

### Accessibility:
- [ ] Focus states
- [ ] ARIA labels on dynamic content
- [ ] Screen reader text for icons

---

**Ready for design tool import?**
