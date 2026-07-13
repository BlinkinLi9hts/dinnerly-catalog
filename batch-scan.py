#!/usr/bin/env python3
"""
Dinnerly Batch Scanner
======================
Pairs pages from fronts.pdf and backs.pdf, sends each pair to Claude,
and saves extracted recipes to Cloudflare KV.

Setup:
    pip install pdf2image pillow requests
    Install Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
    Add Poppler bin folder to PATH (e.g. C:\poppler\Library\bin)

Usage:
    1. Place fronts.pdf and backs.pdf in the scan-inbox\ folder
    2. Set your ANTHROPIC_API_KEY and DINNERLY_SECRET below (or as env vars)
    3. Run: python batch-scan.py
"""

import os
import sys
import json
import base64
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────

SCAN_INBOX   = Path(__file__).parent / "scan-inbox"
FRONTS_PDF   = SCAN_INBOX / "fronts.pdf"
BACKS_PDF    = SCAN_INBOX / "backs.pdf"
DONE_DIR     = SCAN_INBOX / "done"
LOG_FILE     = SCAN_INBOX / "scan-log.txt"

API_URL      = "https://dinnerly-catalog.pages.dev/api/recipes"
CLAUDE_URL   = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-6"

# Read from environment or set directly here
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
DINNERLY_SECRET = os.environ.get("DINNERLY_SECRET", "")

# Processing settings
DPI              = 150    # Lower = faster; 150 is fine for card text
JPEG_QUALITY     = 0.82   # Match app's quality
MAX_WIDTH        = 1200   # Match app's crop output
MAX_HEIGHT       = 675    # 16:9
DELAY_BETWEEN    = 3      # Seconds between Claude API calls (rate limiting)

# ── HELPERS ───────────────────────────────────────────────────────────────────

def log(msg, also_print=True):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if also_print:
        print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def image_to_base64(img):
    """Convert PIL image to base64 JPEG string."""
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=int(JPEG_QUALITY * 100))
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def autocrop_16_9(img):
    """Crop image to centered 16:9 at MAX_WIDTH x MAX_HEIGHT."""
    from PIL import Image
    # Resize to fit within MAX_WIDTH maintaining aspect, then center-crop to 16:9
    w, h = img.size
    target_w, target_h = MAX_WIDTH, MAX_HEIGHT
    target_ratio = target_w / target_h

    # Scale so the image covers the target dimensions
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return img


def fuzzy_match(title_a, title_b):
    """≥60% word overlap — mirrors app's duplicate detection."""
    import re
    def words(s):
        s = re.sub(r"[^a-z0-9\s]", "", s.lower()).strip()
        return {w for w in s.split() if len(w) > 2}
    wa, wb = words(title_a), words(title_b)
    if not wa or not wb:
        return False
    overlap = len(wa & wb)
    return overlap / min(len(wa), len(wb)) >= 0.6


def call_claude(front_b64, back_b64):
    """Send front+back images to Claude, return parsed recipe dict."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
    }
    prompt = """This is the FRONT of a Dinnerly recipe card (title, photo, time, servings).
The second image is the BACK of the same card.
Extract these sections:
1. "What We Send" -- main ingredients with measurements
2. "What You Need" -- pantry staples
3. "Tools" -- kitchen utensils
4. Steps / instructions

Return ONLY valid JSON, no markdown:
{"title":"...","servings":4,"totalTime":"20 min",
"ingredientsSent":[{"name":"elbow macaroni","qty":0.5,"unit":"lb","display":"1/2 lb elbow macaroni"}],
"ingredientsNeeded":["kosher salt","olive oil"],
"tools":["medium saucepan"],
"steps":[{"title":"Cook pasta","body":"Full instruction."}],
"nutrition":{"calories":780,"protein":"46g","carbs":"71g","fat":"30g"}}
Rules: servings=integer; ingredientsSent only items with clear qty+unit; ingredientsNeeded=pantry+unmeasured; no "to taste" in ingredientsSent; each step needs short title+body."""

    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 2000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": front_b64}},
                {"type": "text",  "text": "This is the FRONT of a Dinnerly recipe card."},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": back_b64}},
                {"type": "text",  "text": prompt},
            ]
        }]
    }

    resp = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    clean = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def fetch_existing_recipes():
    """Fetch all recipes currently in KV."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_recipes(recipes):
    """POST full recipes array to KV."""
    headers = {
        "Content-Type": "application/json",
        "X-Dinnerly-Secret": DINNERLY_SECRET,
    }
    resp = requests.post(API_URL, headers=headers, json=recipes, timeout=30)
    resp.raise_for_status()


def prompt_user(msg):
    """Pause and ask user a yes/no question. Returns True for yes/skip, False for retry."""
    print(f"\n⚠️  {msg}")
    while True:
        choice = input("   [s] Skip this card  [r] Retry  [q] Quit: ").strip().lower()
        if choice == "s":
            return "skip"
        elif choice == "r":
            return "retry"
        elif choice == "q":
            return "quit"


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # Validate config
    if not ANTHROPIC_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Set as environment variable or edit batch-scan.py.")
        sys.exit(1)
    if not DINNERLY_SECRET:
        print("ERROR: DINNERLY_SECRET not set. Set as environment variable or edit batch-scan.py.")
        sys.exit(1)
    if not FRONTS_PDF.exists():
        print(f"ERROR: {FRONTS_PDF} not found.")
        sys.exit(1)
    if not BACKS_PDF.exists():
        print(f"ERROR: {BACKS_PDF} not found.")
        sys.exit(1)

    DONE_DIR.mkdir(parents=True, exist_ok=True)
    SCAN_INBOX.mkdir(parents=True, exist_ok=True)

    # Write log header
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Batch scan started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n")

    # Import pdf2image here so error is clear
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("ERROR: pdf2image not installed. Run: pip install pdf2image pillow")
        sys.exit(1)

    print("\n📄 Loading PDFs...")
    try:
        front_pages = convert_from_path(str(FRONTS_PDF), dpi=DPI)
        back_pages  = convert_from_path(str(BACKS_PDF),  dpi=DPI)
    except Exception as e:
        print(f"ERROR loading PDFs: {e}")
        print("Make sure Poppler is installed and on your PATH.")
        sys.exit(1)

    total = len(front_pages)
    if len(back_pages) != total:
        print(f"WARNING: fronts.pdf has {total} pages, backs.pdf has {len(back_pages)} pages.")
        total = min(total, len(back_pages))
        print(f"Processing {total} pairs only.\n")

    print(f"✅ Found {total} card pairs to process.\n")

    # Fetch existing recipes for duplicate checking
    print("☁️  Fetching existing recipes from KV...")
    try:
        existing = fetch_existing_recipes()
        print(f"   {len(existing)} recipes already in catalog.\n")
    except Exception as e:
        print(f"ERROR fetching existing recipes: {e}")
        sys.exit(1)

    # Track new recipes to add
    new_recipes = []
    stats = {"saved": 0, "skipped_dup": 0, "skipped_user": 0, "failed": 0}

    for i in range(total):
        card_num = i + 1
        print(f"[{card_num}/{total}] Processing card...", end=" ", flush=True)

        front_img = front_pages[i]
        back_img  = back_pages[i]

        # Auto-crop front to 16:9
        front_cropped = autocrop_16_9(front_img)
        front_b64 = image_to_base64(front_cropped)
        back_b64  = image_to_base64(back_img)

        attempt = 0
        while True:
            attempt += 1
            try:
                recipe = call_claude(front_b64, back_b64)
            except Exception as e:
                log(f"Card {card_num}: Claude API error — {e}", also_print=False)
                print(f"FAILED (API error: {e})")
                action = prompt_user(f"Card {card_num} — Claude API error: {e}")
                if action == "skip":
                    stats["failed"] += 1
                    log(f"Card {card_num}: SKIPPED after API error")
                    break
                elif action == "retry":
                    print(f"   Retrying card {card_num}...")
                    time.sleep(5)
                    continue
                else:
                    print("\nQuitting. Progress so far will be saved.")
                    _save_progress(existing, new_recipes, stats)
                    sys.exit(0)

            # Check for duplicate
            title = recipe.get("title", "").strip()
            all_titles = [r["title"] for r in existing] + [r["title"] for r in new_recipes]
            dup = next((t for t in all_titles if fuzzy_match(title, t)), None)

            if dup:
                print(f"DUPLICATE — "{title}" matches "{dup}"")
                log(f"Card {card_num}: DUPLICATE — "{title}" matches "{dup}"")
                stats["skipped_dup"] += 1
                break

            # Build full recipe object matching app schema
            full_recipe = {
                "id": int(datetime.now(timezone.utc).timestamp() * 1000) + i,
                "addedAt": datetime.now(timezone.utc).isoformat(),
                "title": title,
                "servings": recipe.get("servings", 4),
                "totalTime": recipe.get("totalTime", ""),
                "frontImage": f"data:image/jpeg;base64,{front_b64}",
                "ingredientsSent": recipe.get("ingredientsSent", []),
                "ingredients": recipe.get("ingredientsSent", []),  # legacy compat
                "ingredientsNeeded": recipe.get("ingredientsNeeded", []),
                "tools": recipe.get("tools", []),
                "steps": recipe.get("steps", []),
                "nutrition": recipe.get("nutrition", None),
                "category": None,  # app will auto-detect from title
                "favorite": False,
            }

            new_recipes.append(full_recipe)
            print(f"✓ "{title}"")
            log(f"Card {card_num}: SAVED — "{title}"")
            stats["saved"] += 1
            break

        # Save to KV every 10 cards as a checkpoint
        if len(new_recipes) > 0 and len(new_recipes) % 10 == 0:
            print(f"\n   💾 Checkpoint: saving {len(new_recipes)} new recipes to KV...")
            try:
                save_recipes(existing + new_recipes)
                print("   Saved.\n")
            except Exception as e:
                log(f"Checkpoint save failed: {e}")
                print(f"   WARNING: checkpoint save failed: {e}\n")

        # Rate limit
        if i < total - 1:
            time.sleep(DELAY_BETWEEN)

    # Final save
    _save_progress(existing, new_recipes, stats)


def _save_progress(existing, new_recipes, stats):
    if new_recipes:
        print(f"\n💾 Saving {len(new_recipes)} new recipes to KV...")
        try:
            save_recipes(existing + new_recipes)
            print("✅ Saved successfully.")
        except Exception as e:
            log(f"Final save failed: {e}")
            print(f"ERROR saving to KV: {e}")
            # Dump to local JSON as fallback
            fallback = Path(__file__).parent / "scan-inbox" / "unsaved-recipes.json"
            with open(fallback, "w", encoding="utf-8") as f:
                json.dump(new_recipes, f, indent=2)
            print(f"Recipes saved locally to {fallback} as fallback.")

    # Move processed PDFs to done/
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for pdf in [Path(__file__).parent / "scan-inbox" / "fronts.pdf",
                Path(__file__).parent / "scan-inbox" / "backs.pdf"]:
        if pdf.exists():
            dest = Path(__file__).parent / "scan-inbox" / "done" / f"{pdf.stem}_{ts}.pdf"
            pdf.rename(dest)

    summary = (
        f"\n{'='*60}\n"
        f"Batch complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Saved:           {stats['saved']}\n"
        f"  Duplicates skipped: {stats['skipped_dup']}\n"
        f"  User skipped:    {stats['skipped_user']}\n"
        f"  Failed:          {stats['failed']}\n"
        f"{'='*60}\n"
    )
    log(summary)
    print(summary)


if __name__ == "__main__":
    main()
