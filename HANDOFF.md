# Dinnerly Recipe Catalog — Handoff Doc

## Greeting Protocol
Brian opens with "Good morning/afternoon/evening/night." Claude reads this doc silently, then responds with a brief status summary and asks what we're working on today.

---

## Project Overview
A personal recipe catalog app for Brian's physical Dinnerly recipe card collection. Scans physical cards via Claude vision API, stores recipes in **Cloudflare KV** (shared across all devices), and serves as a hands-free cooking assistant on a Samsung Android tablet. Brian's wife can access the same catalog and shopping list from her own device.

**Live URL:** https://dinnerly-catalog.pages.dev
**Repo:** https://github.com/BlinkinLi9hts/dinnerly-catalog
**Local file:** C:\Projects\dinnerly-catalog\index.html
**Current version:** v2.7 (pending — rewrite in progress via Cowork)

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
- Single `index.html` — no build step, React 18 via CDN + Babel standalone
- **Cloud storage:** Cloudflare KV (`DINNERLY_KV` namespace) via Pages Functions
- **Auth:** `DINNERLY_SECRET` env var in Cloudflare, validated on all writes via `X-Dinnerly-Secret` header
- Shopping check-off state stays in localStorage (device-specific by design)
- API key stored in localStorage per device (`dinnerly-api-key`)
- Shared password stored in localStorage per device (`dinnerly-secret`)
- Claude Sonnet 4.6 via direct browser API calls (`anthropic-dangerous-direct-browser-access: true`)
- Primary device: Samsung Android tablet, Chrome browser

## File Structure
```
C:\Projects\dinnerly-catalog\
├── index.html                    (main app, v2.2)
├── functions\
│   └── api\
│       ├── recipes.js            (GET/POST recipes to KV)
│       └── schedule.js           (GET/POST schedule to KV)
├── HANDOFF.md
├── dinnerly-watch.ps1            (auto-deploy watcher)
├── start-watcher.vbs             (hidden launcher, green D tray icon)
└── .gitignore
```

---

## Cloudflare Setup (completed)
- **KV Namespace:** `DINNERLY_KV` — created and bound to Pages project
- **Environment variable:** `DINNERLY_SECRET` — encrypted, set in Pages Settings → Functions
- **Binding variable name:** `DINNERLY_KV` (must match exactly in functions)
- Pages Functions in `functions/api/recipes.js` and `functions/api/schedule.js`

---

## Cloud API
```
GET  /api/recipes   → returns all recipes array from KV
POST /api/recipes   → saves recipes array to KV (requires X-Dinnerly-Secret header)
GET  /api/schedule  → returns weekly schedule object from KV
POST /api/schedule  → saves schedule object to KV (requires X-Dinnerly-Secret header)
```
- Reads are public (no auth needed — recipes are not sensitive)
- Writes require `X-Dinnerly-Secret` header matching `DINNERLY_SECRET` env var
- 401 returned on bad/missing secret

---

## First-Time Setup Flow (per device)
1. **API Key Screen** — enter Anthropic API key (sk-ant-...), tested on save
2. **Secret Screen** — enter shared `DINNERLY_SECRET` password (plum-themed), tests write access
3. **Loading screen** — fetches recipes + schedule from KV
4. **Migration banner** (if local recipes exist and cloud is empty) — "Upload to Cloud" button migrates localStorage data to KV, then clears local

---

## Screen Flow
**Home → Catalog (category grid) → Recipe List → Detail → Cook**
**Home → Weekly Planner → Shopping List**

**Planner pick mode:** tap empty/edit day → catalog browse with purple banner → recipe detail → "Add to [Day]" → returns to planner

---

## Feature Summary (v2.2 — current)

### Cloud Storage & Sync
- All recipe saves, deletes, photo updates, category changes → auto-POST to `/api/recipes`
- Schedule changes → auto-POST to `/api/schedule`
- **Save status toast** bottom-right: "Saving..." → "Saved" / "Save failed" (2.5s auto-dismiss)
- Both Brian and wife see same recipes and weekly plan from any device

## Scan Flow (v2.7 target — simple, no viewfinder)
1. Tap "Scan" → camera auto-opens for **front** card
2. Take photo → **CropModal** opens (pinch/drag, 16:9 frame, canvas-based)
3. Tap "Use Photo" → camera auto-opens for **back** card
4. Take photo → "Reading both sides..." → ReviewForm → Save
- "Retake" in CropModal → back to front camera
- Back photo: no crop (text only, no display value)
- Front image: cropped version stored, 1200×675 JPEG at 0.82 quality
- **No ViewfinderCapture / getUserMedia** — file inputs only

### CropModal
- Canvas-based, full-screen black overlay
- Pinch to zoom (min: fill frame, max: 8×), drag to pan
- Pan clamped so image can't leave crop frame
- "Retake" → back to front camera; "Use Photo" → confirms crop, moves to back
- Output: 1200×675 JPEG at 0.82 quality

### Ingredient Routing (scan + shopping list)
- **Scan prompt** explicitly tells Claude: no "to taste" / unmeasured items in `ingredientsSent`
- **`cleanIngredients()`** post-processes every scan result: items with `qty=0`, `qty` missing, or matching `/to taste|as needed|as desired|to season|pinch of/i` are moved from `ingredientsSent` to `ingredientsNeeded`
- **`buildShoppingList()`** applies same regex filter at aggregation time — fixes already-scanned recipes retroactively without re-scanning

### Weekly Planner
- Mon–Sun cards; empty day tap → catalog browse flow
- Assigned day: Cook button, ✏️ (re-pick), ✕ (clear)
- All buttons fully visible — flex overflow fixed with `minWidth:0`, `overflow:hidden` on title div, `flexShrink:0` + `marginLeft:8` on button group

### Shopping List
- **Ingredients to Buy:** `ingredientsSent` aggregated by name+unit, "Used in N recipes" note
- **Pantry Staples:** `ingredientsNeeded` deduplicated + any "to taste" items that slipped into `ingredientsSent`
- **Tools:** deduplicated
- Check-off persists in localStorage per device (`dinnerly-shop-checked-v1`)
- Reset button clears all checks

### Category System
- 9 categories: Beef 🥩 Chicken 🍗 Pork 🐷 Seafood 🦐 Lamb 🐑 Pasta 🍝 Veggie 🌱 Eggs 🥚 Other 🍽️
- Auto-detection from title keywords; manual override via "Change" button on detail screen
- Category picker modal

### Detail Screen
- Category pill with "Change" button
- Hero photo (220px, objectFit:contain, dark bg)
- Serving scaler (+/−, presets [2,4,6,8,12,20], live ingredient scaling with fractions)
- Ingredients list with "You'll also need" section
- Steps preview (purple gradient bubbles)
- Ask Claude chat
- "Gather Ingredients & Cook" CTA
- Planner-pick mode: replaces Cook button with purple "Add to [Day]"
- Photo replace/remove overlay (visible on hover; touch may need first-tap to reveal — pending test)

### Cook Mode
- Dark (#141414) background
- Purple gradient step number bubbles (Dinnerly style)
- Voice nav: "next step", "continue", etc.
- Ingredient drawer (🧄)
- Wake Lock API (Android/Chrome)
- "Enjoy your meal!" completion badge

### Voice Checklist
- "what's left" → reads unchecked items
- "got that one" → checks next item
- Ingredient name fuzzy match → checks specific item
- "ready to start cooking" → launches cook mode
- 🎙 Heard: debug display still present in v2.2

### Android Back Button
- Intercepts popstate: cook→detail→recipelist→catalog→home; planner-pick mode aware
- "Tap back again to exit" toast on home

---

## Recipe Schema
```json
{
  "id": 1720000000000,
  "title": "...",
  "servings": 4,
  "totalTime": "20 min",
  "frontImage": "base64 compressed JPEG (1200px, 0.82q)",
  "ingredientsSent": [{ "name": "...", "qty": 0.5, "unit": "lb", "display": "½ lb ..." }],
  "ingredientsNeeded": ["kosher salt", "olive oil"],
  "ingredients": "(legacy copy of ingredientsSent — kept for backward compat)",
  "tools": ["medium saucepan"],
  "steps": [{ "title": "Cook pasta", "body": "Full instructions..." }],
  "nutrition": { "calories": 780, "protein": "46g", "carbs": "71g", "fat": "30g" },
  "category": "beef",
  "addedAt": "ISO string"
}
```

---

## Design Tokens
```js
C = { ink:"#1C1C1E", paper:"#F5F2ED", card:"#FFFFFF", sage:"#4A7C59",
      sageDark:"#3A6147", sageMid:"#7AAE8A", sageLight:"#EBF2ED",
      orange:"#D9622B", muted:"#8A8A8E", border:"#E0DDD6",
      dark:"#141414", plum:"#5B3E8C" }
```

---

## Known Issues / Pending

| # | Issue | Status |
|---|-------|--------|
| 1 | Cloud storage end-to-end — needs first full test on live site | ✅ Verified working v2.3 |
| 2 | Secret screen → verify it correctly validates and saves on both devices | ✅ Fixed in v2.3 |
| 3 | Migration flow — needs test: local recipes → "Upload to Cloud" → verify cloud has them | 🔧 Pending (KV was wiped; test once cards are scanned) |
| 4 | Photo Replace/Remove overlay uses hover opacity — may be invisible on first touch on tablet | 🔧 Pending touch test |
| 5 | Voice checklist "got that one" / "what's left" — needs re-test on tablet after rewrite | 🔧 Pending |
| 6 | Seed recipe (Macaroni Bolognese id:1720000000000) still in code | ⏳ Remove once real cards scanned |
| 7 | "Heard:" debug display still in voice checklist | ⏳ Remove once voice confirmed working |
| 8 | File corrupted by incremental edits in v2.5/2.6 — full rewrite needed (in progress via Cowork) | 🔧 In progress |

---

## MCP / Environment
- Filesystem MCP paths: `C:\Projects\blinkinlights-studio` and `C:\Projects\dinnerly-catalog`
- Claude Desktop config: `C:\Users\bbuts\AppData\Roaming\Claude\claude_desktop_config.json`
- Anthropic API key stored in browser localStorage on each device separately
- Shared secret stored in browser localStorage on each device separately
- Primary use device: Samsung Android tablet, Chrome

---

## Version History
- v1.0–1.5: Initial React JSX artifact → standalone HTML, scan, cook mode, voice, checklist
- v1.6: Voice debug display ("Heard:"), expanded phrase lists, back button interception
- v1.7: Photo edit on detail screen (replace/remove/add), category pill placeholder
- v1.8: Image compression (canvas, 800px/0.72q), photo compression on replace
- v1.9: Category system — CategoryScreen landing, RecipeListScreen, CategoryPicker modal, detectCategory(), CATEGORIES array, full routing overhaul
- v2.0: Weekly Planner (Mon–Sun), planner pick flow (catalog browse → add to day), Shopping List (aggregated ingredients + pantry staples + tools), check-off with localStorage persistence, Android back button planner-aware routing
- v2.1: CropModal (pinch/drag 16:9 canvas crop), fast scan flow (camera auto-opens → crop → camera auto-opens → parse → review), no manual "Read Recipe Cards" button
- v2.2: **Cloudflare KV cloud storage** — recipes and schedule stored in KV, shared across all devices; SecretScreen (shared password entry); loading screen; save status toast; migration prompt for existing localStorage data; ingredient routing fix ("to taste" items → pantry staples at scan time and shopping list display time); weekly planner button overflow fix
- v2.3: **Cloud storage bug fixes** — recreated missing `functions/api/recipes.js` and `functions/api/schedule.js` (never committed to repo); fixed SecretScreen POSTing `null` to KV on every new device setup (wiped all recipes); fixed `seedIfEmpty()` re-injecting seed after migration. Full end-to-end cloud round-trip verified working.
- v2.4: **Duplicate detection** — fuzzy title matching (≥60% word overlap) checks for duplicates on save; side-by-side modal shows existing vs new scan with date/steps/ingredients; options to keep existing, replace, or save both.
- v2.5–2.6: **Auto-crop & viewfinder experiments** — attempted fixed-percentage auto-crop and live getUserMedia viewfinder for front card; both abandoned due to card distance variability and UX friction. File became corrupted from incremental edits.
- v2.7: **Clean rewrite** — full file rewritten via Cowork; restores simple scan flow (front file input → CropModal → back file input → parse → review); removes ViewfinderCapture entirely; all v2.4 features preserved.
