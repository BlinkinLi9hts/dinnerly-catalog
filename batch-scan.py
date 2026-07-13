#!/usr/bin/env python3
"""
Dinnerly Batch Scanner
======================
Pairs pages from fronts.pdf and backs.pdf, sends each pair to Claude,
and saves extracted recipes to Cloudflare KV.

Setup:
    pip install pdf2image pillow requests
    Install Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
    Add Poppler bin folder to PATH (e.g. C:/poppler/Library/bin)

Usage:
    1. Place fronts.pdf and backs.pdf in the scan-inbox folder
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

# Load .env file if present
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# -- CONFIG -------------------------------------------------------------------

SCAN_INBOX    = Path(__file__).parent / "scan-inbox"
FRONTS_PDF    = SCAN_INBOX / "fronts.pdf"
BACKS_PDF     = SCAN_INBOX / "backs.pdf"
DONE_DIR      = SCAN_INBOX / "done"
LOG_FILE      = SCAN_INBOX / "scan-log.txt"

API_URL       = "https://dinnerly-catalog.pages.dev/api/recipes"
CLAUDE_URL    = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL  = "claude-sonnet-4-6"

# Read from environment or set directly here
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
DINNERLY_SECRET = os.environ.get("DINNERLY_SECRET", "")

# Processing settings
DPI           = 150    # Lower = faster; 150 is fine for card text
JPEG_QUALITY  = 82     # Match app quality (0-100)
MAX_WIDTH     = 1200   # Match app crop output
MAX_HEIGHT    = 675    # 16:9
DELAY_BETWEEN = 3      # Seconds between Claude API calls (rate limiting)

# -- HELPERS ------------------------------------------------------------------

def log(msg, also_print=True):
    ts = datetime.now().strftime("%H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    if also_print:
        print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def image_to_base64(img):
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def autocrop_16_9(img):
    from PIL import Image
    w, h = img.size
    scale = max(MAX_WIDTH / w, MAX_HEIGHT / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - MAX_WIDTH) // 2
    top  = (new_h - MAX_HEIGHT) // 2
    return img.crop((left, top, left + MAX_WIDTH, top + MAX_HEIGHT))


def fuzzy_match(title_a, title_b):
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
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
    }
    prompt = (
        "This is the FRONT of a Dinnerly recipe card (title, photo, time, servings). "
        "The second image is the BACK of the same card.\n"
        "Extract these sections:\n"
        "1. What We Send -- main ingredients with measurements\n"
        "2. What You Need -- pantry staples\n"
        "3. Tools -- kitchen utensils\n"
        "4. Steps / instructions\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        '{"title":"...","servings":4,"totalTime":"20 min",'
        '"ingredientsSent":[{"name":"elbow macaroni","qty":0.5,"unit":"lb","display":"1/2 lb elbow macaroni"}],'
        '"ingredientsNeeded":["kosher salt","olive oil"],'
        '"tools":["medium saucepan"],'
        '"steps":[{"title":"Cook pasta","body":"Full instruction."}],'
        '"nutrition":{"calories":780,"protein":"46g","carbs":"71g","fat":"30g"}}\n'
        "Rules: servings=integer; ingredientsSent only items with clear qty+unit; "
        "ingredientsNeeded=pantry+unmeasured; no to taste in ingredientsSent; "
        "each step needs short title+body."
    )
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
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_recipes(recipes):
    headers = {
        "Content-Type": "application/json",
        "X-Dinnerly-Secret": DINNERLY_SECRET,
    }
    resp = requests.post(API_URL, headers=headers, json=recipes, timeout=30)
    resp.raise_for_status()


def prompt_user(card_num, err):
    print("\n  Card {} failed: {}".format(card_num, err))
    while True:
        choice = input("  [s] Skip  [r] Retry  [q] Quit: ").strip().lower()
        if choice in ("s", "r", "q"):
            return choice


# -- MAIN ---------------------------------------------------------------------

def main():
    if not ANTHROPIC_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    if not DINNERLY_SECRET:
        print("ERROR: DINNERLY_SECRET not set.")
        sys.exit(1)
    if not FRONTS_PDF.exists():
        print("ERROR: {} not found.".format(FRONTS_PDF))
        sys.exit(1)
    if not BACKS_PDF.exists():
        print("ERROR: {} not found.".format(BACKS_PDF))
        sys.exit(1)

    DONE_DIR.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "="*60 + "\n")
        f.write("Batch scan started: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("="*60 + "\n")

    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("ERROR: pdf2image not installed. Run: pip install pdf2image pillow")
        sys.exit(1)

    print("\nLoading PDFs...")
    try:
        front_pages = convert_from_path(str(FRONTS_PDF), dpi=DPI)
        back_pages  = convert_from_path(str(BACKS_PDF),  dpi=DPI)
    except Exception as e:
        print("ERROR loading PDFs: {}".format(e))
        print("Make sure Poppler is installed and on your PATH.")
        sys.exit(1)

    total = len(front_pages)
    if len(back_pages) != total:
        print("WARNING: fronts.pdf has {} pages, backs.pdf has {} pages.".format(total, len(back_pages)))
        total = min(total, len(back_pages))
        print("Processing {} pairs only.".format(total))

    print("Found {} card pairs to process.\n".format(total))

    print("Fetching existing recipes from KV...")
    try:
        existing = fetch_existing_recipes()
        print("  {} recipes already in catalog.\n".format(len(existing)))
    except Exception as e:
        print("ERROR fetching existing recipes: {}".format(e))
        sys.exit(1)

    new_recipes = []
    stats = {"saved": 0, "skipped_dup": 0, "skipped_user": 0, "failed": 0}

    for i in range(total):
        card_num = i + 1
        print("[{}/{}] Processing...".format(card_num, total), end=" ", flush=True)

        front_cropped = autocrop_16_9(front_pages[i])
        front_b64 = image_to_base64(front_cropped)
        back_b64  = image_to_base64(back_pages[i])

        while True:
            try:
                recipe = call_claude(front_b64, back_b64)
            except Exception as e:
                log("Card {}: API error -- {}".format(card_num, e), also_print=False)
                print("FAILED")
                action = prompt_user(card_num, e)
                if action == "s":
                    stats["failed"] += 1
                    log("Card {}: SKIPPED after error".format(card_num))
                    break
                elif action == "r":
                    print("  Retrying...")
                    time.sleep(5)
                    continue
                else:
                    print("\nQuitting. Saving progress...")
                    _save_progress(existing, new_recipes, stats)
                    sys.exit(0)

            title = recipe.get("title", "").strip()
            all_titles = [r["title"] for r in existing] + [r["title"] for r in new_recipes]
            dup = next((t for t in all_titles if fuzzy_match(title, t)), None)

            if dup:
                msg = 'Card {}: DUPLICATE -- "{}" matches "{}"'.format(card_num, title, dup)
                print('DUPLICATE -- matches "{}"'.format(dup))
                log(msg, also_print=False)
                stats["skipped_dup"] += 1
                break

            full_recipe = {
                "id": int(datetime.now(timezone.utc).timestamp() * 1000) + i,
                "addedAt": datetime.now(timezone.utc).isoformat(),
                "title": title,
                "servings": recipe.get("servings", 4),
                "totalTime": recipe.get("totalTime", ""),
                "frontImage": "data:image/jpeg;base64," + front_b64,
                "ingredientsSent": recipe.get("ingredientsSent", []),
                "ingredients": recipe.get("ingredientsSent", []),
                "ingredientsNeeded": recipe.get("ingredientsNeeded", []),
                "tools": recipe.get("tools", []),
                "steps": recipe.get("steps", []),
                "nutrition": recipe.get("nutrition", None),
                "category": None,
                "favorite": False,
            }

            new_recipes.append(full_recipe)
            print('OK -- "{}"'.format(title))
            log('Card {}: SAVED -- "{}"'.format(card_num, title), also_print=False)
            stats["saved"] += 1
            break

        # Checkpoint every 10 cards
        if new_recipes and len(new_recipes) % 10 == 0:
            print("\n  Checkpoint: saving {} recipes to KV...".format(len(new_recipes)), end=" ")
            try:
                save_recipes(existing + new_recipes)
                print("done.\n")
            except Exception as e:
                print("WARNING: checkpoint failed: {}\n".format(e))

        if i < total - 1:
            time.sleep(DELAY_BETWEEN)

    _save_progress(existing, new_recipes, stats)


def _save_progress(existing, new_recipes, stats):
    if new_recipes:
        print("\nSaving {} new recipes to KV...".format(len(new_recipes)), end=" ")
        try:
            save_recipes(existing + new_recipes)
            print("done.")
        except Exception as e:
            log("Final save failed: {}".format(e))
            print("ERROR: {}".format(e))
            fallback = SCAN_INBOX / "unsaved-recipes.json"
            with open(fallback, "w", encoding="utf-8") as f:
                json.dump(new_recipes, f, indent=2)
            print("Recipes saved locally to {} as fallback.".format(fallback))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for pdf in [FRONTS_PDF, BACKS_PDF]:
        if pdf.exists():
            pdf.rename(DONE_DIR / "{}_{}.pdf".format(pdf.stem, ts))

    summary = (
        "\n" + "="*60 + "\n"
        "Batch complete: {}\n"
        "  Saved:              {}\n"
        "  Duplicates skipped: {}\n"
        "  User skipped:       {}\n"
        "  Failed:             {}\n"
        + "="*60 + "\n"
    ).format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        stats["saved"], stats["skipped_dup"], stats["skipped_user"], stats["failed"]
    )
    log(summary)


if __name__ == "__main__":
    main()
