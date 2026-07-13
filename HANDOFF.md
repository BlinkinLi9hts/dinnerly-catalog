# Dinnerly Recipe Catalog — Handoff Doc

## Greeting Protocol
Brian opens with "Good morning/afternoon/evening/night." Claude reads this doc silently, then responds with a brief status summary and asks what we're working on today.

---

## Project Overview
A personal recipe catalog app for Brian's physical Dinnerly recipe card collection. Scans physical cards via Claude vision API, stores recipes locally, and serves as a hands-free cooking assistant on a Samsung Android tablet.

**Live URL:** https://dinnerly-catalog.pages.dev
**Repo:** https://github.com/BlinkinLi9hts/dinnerly-catalog
**Local file:** C:\Projects\dinnerly-catalog\index.html
**Current version:** v1.9

---

## Auto-Deploy Pipeline
1. Claude writes directly to `C:\Projects\dinnerly-catalog\index.html`
2. `dinnerly-watch.ps1` detects change (3s debounce), auto-commits and pushes to GitHub
3. Cloudflare Pages auto-deploys (~30 seconds)
4. Live at dinnerly-catalog.pages.dev

**Watcher launch:** double-click `start-watcher.vbs` → hidden PowerShell, green "D" tray icon
**.gitignore:** excludes `*.ps1` and `*.vbs`

---

## Architecture
- Single `index.html` file — no build step, React 18 via CDN + Babel standalone
- localStorage for recipe storage (`dinnerly-recipes-v2`) and API key (`dinnerly-api-key`)
- Claude Sonnet 4.6 via direct browser API calls (`anthropic-dangerous-direct-browser-access: true`)
- Deployed on Cloudflare Pages (static file hosting)
- Primary device: Samsung Android tablet, Chrome browser

---

## Screen Flow
**Categories → Recipe List → Detail → Cook**

- **CategoryScreen** — "What are we cooking tonight?" big emoji tiles, only shows categories with recipes
- **RecipeListScreen** — filtered grid by category
- **DetailScreen** — photo, category pill, scaler, ingredients, steps, Ask Claude chat
- **CookScreen** — dark mode, Dinnerly-style purple numbered bubbles, voice nav, wake lock

---

## Feature Summary (v1.9 — current)

### Categories
- 9 categories: Beef 🥩, Chicken 🍗, Pork 🐷, Seafood 🦐, Lamb 🐑, Pasta 🍝, Veggie 🌱, Eggs 🥚, Other 🍽️
- `detectCategory(title, saved)` — keyword match from title, saved override wins
- `getCategoryInfo(id)` — returns category object
- Category picker modal on detail screen ("Change" button in pill)
- `onUpdateCategory` prop wired through App → DetailScreen

### Scan
- Dual-side upload (front + back of Dinnerly card)
- `UploadZone` top-level component with `<label htmlFor>` + `capture="environment"` (mobile camera fix)
- Claude vision API extracts: title, servings, totalTime, ingredients, steps, nutrition
- **Image compression** via canvas before storing: 800px max, 0.72 JPEG quality (~50-80KB vs 5MB raw)
- Compression applied on scan AND on manual photo replace
- Review/edit screen before saving

### Detail Screen
- Category pill with "Change" button → CategoryPicker modal
- Hero photo (220px, dark bg): tap to replace, hover overlay shows 📷 Replace / 🗑 Remove
- `objectFit: contain` — no cropping on landscape card photos
- Serving scaler: +/− buttons, number input, quick presets [2,4,6,8,12,20], live ingredient scaling with fraction display
- Ingredients list with "Gather List" button
- Steps preview (purple gradient numbered bubbles)
- Ask Claude chat (conversational Q&A about scaled recipe)
- "Gather Ingredients & Cook →" button

### Ingredient Checklist Modal
- Full-screen overlay, large text (19px), tap to check off
- Progress bar + count
- Voice control (Enable Voice button):
  - "what's left" / "whats left" → reads unchecked items aloud
  - "got that" / "got that one" → checks next unchecked item
  - Ingredient name fuzzy match → checks specific item
  - "ready to start cooking" → closes list, launches cook mode
  - 🎙 Heard: debug display shows last transcript (kept for diagnostics)

### Cook Mode
- Dark background (#141414)
- Purple gradient circle (135deg #6B4FC8→#8B6DE0) with zero-padded step number
- Bold step title + body text
- Progress bar (sage green)
- Voice navigation: 🎙 button → "next step" / "ok what's next" / "continue" / "move on"
- ← Back / Next → buttons
- 🧄 ingredient drawer (right side, shows scaled quantities)
- Wake Lock API (Android/Chrome): screen stays on
- "🎉 Enjoy your meal!" completion badge

### Android Back Button
- Intercepts `popstate` event
- cook → detail → recipelist → categories
- scan → recipelist or categories (depending on activeCategory)
- Categories: first back shows "Tap back again to exit" toast (2s), second exits

### API Key Screen
- Show/hide toggle (👁/🙈)
- Live key preview (first 16 chars) + format validation (✓/✗)
- Saves key FIRST, then tests connection
- autoComplete/autoCorrect/autoCapitalize off for mobile paste

---

## Storage
- `dinnerly-recipes-v2` — recipe array in localStorage
- Recipe schema: `{ id, title, servings, totalTime, frontImage (compressed base64), ingredients [{name,qty,unit,display}], steps [{title,body}], nutrition, category, addedAt }`
- Seed recipe: Macaroni with Beef Bolognese (id: 1720000000000) — **remove once real cards are scanned**

---

## Known Issues / Pending

| # | Issue | Status |
|---|-------|--------|
| 1 | Voice checklist "got that one" / "what's left" not registering on tablet | 🔧 Debug display added in v1.9 — needs testing |
| 2 | Photo Replace/Remove overlay uses hover opacity — may be invisible on first touch | 🔧 Needs touch testing on tablet |
| 3 | Seed recipe still in code | ⏳ Remove once real cards scanned |
| 4 | patch-v19.py left in project folder | 🗑 Delete this file |

---

## MCP / Environment
- Filesystem MCP paths: `C:\Projects\blinkinlights-studio` and `C:\Projects\dinnerly-catalog`
- Claude Desktop config: `C:\Users\bbuts\AppData\Roaming\Claude\claude_desktop_config.json`
- Anthropic API key stored in browser localStorage on each device separately
- Primary use device: Samsung Android tablet, Chrome

---

## Version History
- v1.0–1.5: Initial React JSX artifact → standalone HTML, scan, cook mode, voice, checklist
- v1.6: Voice debug display ("Heard:"), expanded phrase lists, back button interception
- v1.7: Photo edit on detail screen (replace/remove/add), category pill placeholder
- v1.8: Image compression (canvas, 800px/0.72q), photo compression on replace
- v1.9: **Category system** — CategoryScreen landing, RecipeListScreen, CategoryPicker modal, detectCategory(), CATEGORIES array, full routing overhaul
