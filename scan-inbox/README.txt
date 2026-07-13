Dinnerly Batch Scanner — Inbox
==============================

SETUP (one time):
  pip install pdf2image pillow requests
  Install Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
  Add Poppler's bin folder to your PATH.

  Set environment variables (or edit the top of batch-scan.py directly):
    ANTHROPIC_API_KEY=sk-ant-...
    DINNERLY_SECRET=your-shared-password

SCANNING PROCESS:
  1. Load ALL front-side cards into your scanner's sheet feeder
  2. Scan → save as:  scan-inbox\fronts.pdf
  3. Flip the physical stack to maintain the SAME ORDER
  4. Load ALL back-side cards into the sheet feeder
  5. Scan → save as:  scan-inbox\backs.pdf
  6. Run from the project folder:  python batch-scan.py

WHAT HAPPENS:
  - Each page of fronts.pdf is paired with the same-numbered page of backs.pdf
  - Front image is auto-cropped to 16:9 centered
  - Claude extracts title, ingredients, steps, nutrition from each pair
  - Duplicates (matched against your existing catalog) are skipped automatically
  - New recipes are saved to Cloudflare KV every 10 cards (checkpoint)
  - On failure: script pauses and asks you to skip, retry, or quit
  - Processed PDFs are moved to scan-inbox\done\ when finished
  - Full log written to scan-inbox\scan-log.txt

AFTER SCANNING:
  - Open the app and check your catalog
  - Any cards with bad auto-crop: tap the photo on the Detail screen → Replace → CropModal
  - Any cards with wrong category: tap "Change" on the Detail screen
