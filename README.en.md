# Pogostuck Loot Mode Auto Splitter (Score-Based)

A script that captures and OCR-reads the score on screen during Pogostuck's Loot Mode and automatically controls the LiveSplit timer.

> 🇯🇵 [日本語版はこちら](README.md)

## Overview

Every 0.5 seconds, the script captures the score area displayed in the upper-left of the game screen (e.g., the `10000` part of `@ 5 | 10000`), runs OCR on it, and sends a `split` command to LiveSplit each time the score crosses a multiple of `SPLIT_SCORE_INTERVAL`.

- Your own score is displayed in yellow text, so only yellow pixels are extracted for recognition.
- When the score returns to 0, the timer is automatically reset and restarted.

## Downloading the Files

1. Click the green **"Code"** button at the top of the page
2. Click **"Download ZIP"**
3. Extract the downloaded ZIP file to any folder

> No Git or clone required. Just extract the ZIP and you're ready.

## File Structure

| File | Description |
|---|---|
| `pogo_autosplit_score.py` | Main script. Splits at specified score intervals and detects score-0 resets |
| `calibrate.py` | Calibration tool to verify the capture region |
| `sample_calibrate_check.png` | Reference image showing a successful calibration |
| `LiveSpilitLayout_LootScore.lsl` | LiveSplit layout file |
| `Pogostuck Rage With Your Friends - Loot Score.lss` | LiveSplit splits file |

## Requirements

| Tool / Library | Source | Purpose |
|---|---|---|
| Python 3.10+ | https://www.python.org/downloads/ | Script runtime |
| Tesseract OCR | https://github.com/UB-Mannheim/tesseract/wiki | OCR engine for reading numbers from images |
| LiveSplit | https://livesplit.org/ | Timer display and split management |
| mss / pytesseract / Pillow / numpy | Install via `pip` (see below) | Python libraries used by the script |

## Setup

> If this is your first time, follow **Steps 1 through 7 in order**.  
> If you already have Python or Tesseract installed, feel free to skip those steps.

---

### Step 1: Install Python

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Click **"Download Python 3.x.x"** to download the installer
3. Run the downloaded file
4. On the installer screen, **check "Add Python to PATH"** (important)
5. Click **"Install Now"** and wait for completion

> ✅ To verify: after installation, open Command Prompt and type `python --version`. You should see `Python 3.x.x`.

---

### Step 2: Install Tesseract OCR

1. Go to [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Download **"tesseract-ocr-w64-setup-x.x.x.exe"** (64-bit version)
3. Run the downloaded file
4. Leave the install location as the default `C:\Program Files\Tesseract-OCR\` (if changed, the script will need to be updated)
5. Wait for the installation to complete

---

### Step 3: Install LiveSplit

1. Go to [https://livesplit.org/](https://livesplit.org/)
2. Download the ZIP from the **"Download"** button and extract it to any folder
3. Launch `LiveSplit.exe`
4. Right-click the LiveSplit window → **"Settings"** → under "Startup Behavior:", select **"Start TCP Server"**

> ✅ The default server port is 16834.

Loading the included `.lss` / `.lsl` files will let you use the split configuration and layout as-is.

> ※1 Edit the `.lss` splits file manually to match your desired number of splits (align `SPLIT_SCORE_INTERVAL` with the number of segments in LiveSplit).  
> ※2 The `.lsl` layout file has a magenta background for chroma-key transparency in OBS. Feel free to change it to your liking.

---

### Step 4: Install Python Libraries

**How to open Command Prompt:**

1. Press **Windows key + R**
2. Type `cmd` in the "Run" dialog and press **Enter**
3. A black window (Command Prompt) will open

**Install the libraries:**

Paste the following into Command Prompt and press **Enter**:

```
pip install mss pytesseract Pillow numpy
```

When you see `Successfully installed ...`, the installation is complete.

---

### Step 5: Place the Script Files

1. Open the folder where you extracted this repository's ZIP
2. Type `cmd` in the folder's address bar and press **Enter** (this opens Command Prompt in that folder)

---

### Step 6: Calibration (First Run / After Resolution Change)

With the game running, execute:

```
python calibrate.py
```

A file called `calibrate_check.png` will be generated. Open it and confirm that **only the score digits after `|` appear white**.  
The included `sample_calibrate_check.png` is a reference image of a successful calibration.

If digits are cut off or overflow, adjust the constants at the top of **`calibrate.py`** using a text editor:

```python
LEFT_CAPTURE_TOP    = 70   # Top edge of the score row (px)
LEFT_CAPTURE_LEFT   = 325  # Start slightly to the right of "|" (px)
LEFT_CAPTURE_WIDTH  = 200  # Width to cover all digits (px)
LEFT_CAPTURE_HEIGHT = 150  # Height to cover all player rows (px)
```

Once you've determined the values, apply the same values to the matching constants at the top of **`pogo_autosplit_score.py`**.

---

### Step 7: Run the Script

With LiveSplit's Server running, type the following in Command Prompt:

```
python pogo_autosplit_score.py
```

Once the script is running, start the game — the timer will automatically start the moment your score begins moving from 0.

## How It Works

```
① Capture the "| score" region in the upper-left every 0.5 seconds
      ↓
② Use numpy to convert only yellow pixels to white (isolate your own score row)
      ↓
③ Upscale the image 3x (improves OCR accuracy)
      ↓
④ Run Tesseract OCR to recognize digits (whitelist: 0123456789)
      ↓
⑤ Apply spike-up / spike-down filters to reject misread values
      ↓
⑥ Confirm the value once the same result appears STABLE_COUNT times in a row
      ↓
⑦ Score exceeds a multiple of SPLIT_SCORE_INTERVAL → send "split" to LiveSplit
   Score returns to 0 → send "reset" + "starttimer" to LiveSplit
```

## Configuration

Adjust behavior in the `★ Settings Start ★` block at the top of the script.

| Constant | Default | Description |
|---|---|---|
| `TESSERACT_CMD` | `C:\...\tesseract.exe` | Path to the Tesseract executable |
| `LEFT_CAPTURE_TOP` | `70` | Top edge of the capture region (px) |
| `LEFT_CAPTURE_LEFT` | `325` | Left edge of the capture region (px). Start to the right of `\|` |
| `LEFT_CAPTURE_WIDTH` | `200` | Capture width (px) |
| `LEFT_CAPTURE_HEIGHT` | `150` | Capture height (px) |
| `SPLIT_SCORE_INTERVAL` | `3000` | Score interval for each split (e.g., 1000, 5000, 10000) |
| `MAX_SCORE_DROP` | `500` | Maximum allowed score decrease. Larger drops are treated as misreads |
| `STABLE_COUNT` | `3` | Number of consecutive matches required to confirm a value (misread filter) |
| `DEBUG_SAVE_OCR_IMAGE` | `True` | Save the pre-OCR image as `debug_ocr.png` |
| `LIVESPLIT_HOST` | `localhost` | LiveSplit Server host |
| `LIVESPLIT_PORT` | `16834` | LiveSplit Server TCP port |

## Debugging

When `DEBUG_SAVE_OCR_IMAGE = True`, the image passed to OCR is saved as `debug_ocr.png`. Use it to confirm that the yellow text is being correctly extracted as white.

The console will show output like:

```
[OCR raw LEFT] '10000'
[Confirmed] Score: 9500 → 10000
[ACTION] Split! Reached 10000 pts
  → Sent to LiveSplit: split
```

## Reset Detection Logic

| Detection Condition | Action |
|---|---|
| `confirmed_score == 0` and previous score was greater than 0 | Score returned to 0 → Reset timer and restart |

## Misread Filters

| Filter | Condition | Purpose |
|---|---|---|
| Spike-up filter | `raw > confirmed × 3 + interval × 10` | Reject digit-appending misreads (e.g., 419 → 900419) |
| Spike-down filter | `raw < confirmed - MAX_SCORE_DROP` and `raw > 0` | Reject digit-dropping misreads (e.g., 47820 → 4782) |
| Stability filter | Value must appear `STABLE_COUNT` times consecutively to be confirmed | Reject single-frame noise |
