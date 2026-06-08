import mss
import pytesseract
from PIL import Image
import numpy as np
import socket
import time
import re
import os

# ============================================================
# ★ 設定ここから ★  ← ここだけ変更すれば動作を調整できます
# ============================================================

# Tesseract-OCR の実行ファイルパス
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# キャプチャ領域（calibrate.py で「|」以降の数字部分の座標を確認して設定）
LEFT_CAPTURE_TOP    = 70   # 左上スコア行の上端（px）
LEFT_CAPTURE_LEFT   = 325  # 「|」の少し右から開始（px）
LEFT_CAPTURE_WIDTH  = 200  # 数字全体を覆う幅（px）
LEFT_CAPTURE_HEIGHT = 150  # ロビー順位に関係なく全プレイヤー行をカバー（約30px/行 × 4人 + 余裕）

# acklog.txt のパス（リセット検知用）
LOG_FILE = r"C:\Program Files (x86)\Steam\steamapps\common\Pogostuck\acklog.txt"

# LiveSplit Server 設定
LIVESPLIT_HOST = "localhost"
LIVESPLIT_PORT = 16834

# スプリット間隔（点）
SPLIT_SCORE_INTERVAL = 3000  # 何点ごとにスプリットするか（例: 1000, 3000, 5000, 10000）

# 許容する最大スコア減少量（点）
# ルートモードでは弾を撃つたびに1点減るため、小さな減少は正常
# これを超える急減は誤認識として拒否する（例: 47820→4782 は拒否、47820→47800 は許容）
MAX_SCORE_DROP = 500

# 認識安定化：同じ値がN回連続して出たときに「確定」と見なす
STABLE_COUNT = 3

# デバッグ用：True にすると OCR直前の画像を debug_ocr.png に保存する
DEBUG_SAVE_OCR_IMAGE = True

# ============================================================
# ★ 設定ここまで ★
# ============================================================

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def send_livesplit(command: str):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)  # 1秒のタイムアウト設定
            s.connect((LIVESPLIT_HOST, LIVESPLIT_PORT))
            s.sendall((command + "\r\n").encode())
            # レスポンスはオプショナル（タイムアウトする場合あり）
            try:
                response = s.recv(1024).decode().strip()
                if response:
                    print(f"  → LiveSplit送信: {command} | 応答: {response}")
                else:
                    print(f"  → LiveSplit送信: {command}")
            except socket.timeout:
                print(f"  → LiveSplit送信: {command} (応答なし)")
    except Exception as e:
        print(f"[LiveSplit接続エラー] {e}")

def get_score_left(sct) -> int | None:
    """左上の「| 数字」部分をOCRで読み取る（黄色テキスト、グラデーションなし）

    Returns:
        int | None: 読み取ったスコア。認識失敗時は None
    """
    region = {
        "top":    LEFT_CAPTURE_TOP,
        "left":   LEFT_CAPTURE_LEFT,
        "width":  LEFT_CAPTURE_WIDTH,
        "height": LEFT_CAPTURE_HEIGHT,
    }

    screenshot = sct.grab(region)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

    # 左上スコアは黄色テキスト（グラデーションなし・均一な黄色）
    # 右上より閾値を厳しめにしてノイズを抑える
    arr = np.array(img)
    yellow_mask = (
        (arr[:,:,0] > 180) &   # R > 180
        (arr[:,:,1] > 160) &   # G > 160
        (arr[:,:,2] < 80) &    # B < 80
        ((arr[:,:,0].astype(int) - arr[:,:,2].astype(int)) > 120)  # R-B差
    )
    masked = np.zeros_like(arr)
    masked[yellow_mask] = [255, 255, 255]
    img = Image.fromarray(masked.astype(np.uint8), 'RGB')

    # 3倍拡大でOCR精度UP
    img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    # 余白追加（Tesseractが端の文字を見落としにくくなる）
    from PIL import ImageOps
    img = ImageOps.expand(img, border=20, fill='black')

    if DEBUG_SAVE_OCR_IMAGE:
        img.save("debug_ocr.png")

    # 黄色マスク後は自分のスコア1行のみ残るため --psm 7（単一行）固定
    text = pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()

    print(f"[OCR raw LEFT] '{text}'")

    digits = re.sub(r'\D', '', text)
    if digits:
        return int(digits)

    return None


def do_reset_start():
    """タイマーをリセットして再スタート"""
    print("[ACTION] タイマーリセット＆スタート")
    send_livesplit("reset")
    time.sleep(0.1)
    send_livesplit("starttimer")

def main():
    print("=== Pogostuck オートスプリッター起動 ===")
    print(f"スプリット間隔: {SPLIT_SCORE_INTERVAL}点ごと")
    print("LiveSplit を起動して TCP Server を開始してください。")
    print("acklog.txt の新シード検知でタイマーを自動リセット＆再スタートします。")
    print("Ctrl+C で終了\n")

    confirmed_score = None   # 直近に「確定」したスコア
    candidate_score = None   # 安定化中のスコア候補
    candidate_count = 0      # 候補が連続して出た回数
    last_split_milestone = 0 # 直近にスプリットしたマイルストーン番号（例: 3 = 3×interval 点でスプリット済み）
    started = False          # タイマーが動いているか
    # 起動時点のファイル末尾から監視開始（既存の古いシードを無視する）
    last_log_pos = os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0
    current_seed = None      # 現在のランのシード値
    is_paused    = False     # ポーズ中かどうか

    with mss.mss() as sct:
        while True:
            # ── acklog.txt でリセット（新ラン開始）を検知 ──
            try:
                if os.path.exists(LOG_FILE):
                    stat = os.stat(LOG_FILE)
                    # ファイルが縮小した場合 → ゲームが再起動して新しいログになった
                    if stat.st_size < last_log_pos:
                        last_log_pos = 0
                        current_seed = None
                        is_paused    = False
                    if stat.st_size > last_log_pos:
                        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(last_log_pos)
                            chunk = f.read()
                        last_log_pos = stat.st_size
                        # ---------------------------------------------------
                        # ポーズ開始: " ~~~~~~ open menu frame XXX"
                        # ---------------------------------------------------
                        if current_seed is not None and not is_paused:
                            if re.search(r" ~~~~~~ open menu frame \d+", chunk):
                                is_paused = True
                                print("\n[ポーズ] → pause")
                                send_livesplit("pause")

                        # ---------------------------------------------------
                        # ポーズ解除: menu_close() または close menu now
                        # ---------------------------------------------------
                        if current_seed is not None and is_paused:
                            if re.search(r"menu_item_function_default: menu_close\(\)|close menu now at frame \d+", chunk):
                                is_paused = False
                                print("\n[再開] → resume")
                                send_livesplit("resume")

                        for m in re.finditer(
                            r"dungeonSetInitialSeed\(1\) at frame \d+ -> lvl\(0\) seed\((\d+)\)",
                            chunk
                        ):
                            new_seed = m.group(1)
                            if new_seed != current_seed:
                                current_seed = new_seed
                                is_paused    = False
                                print(f"\n[新ラン検知] seed={new_seed} → タイマーリセット＆スタート")
                                do_reset_start()
                                last_split_milestone = 0
                                confirmed_score = None
                                candidate_score = None
                                candidate_count = 0
                                started = True
            except Exception as e:
                print(f"[ログ読み込みエラー] {e}")

            # ポーズ中はOCR処理をスキップ
            if is_paused:
                time.sleep(0.5)
                continue

            raw_score = get_score_left(sct)

            # 認識失敗は無視
            if raw_score is None:
                time.sleep(0.5)
                continue

            # --- 急増フィルタ（誤認識ノイズ除去）---
            # 確定済みスコアから異常に大きい値はノイズとして捨てる
            # 例: confirmed=419 のときに 900419 が来たら拒否
            # スコアは単調増加なので、前回の3倍+インターバル10個分を超えたら誤認識と判断
            if confirmed_score is not None and confirmed_score > 0:
                max_reasonable = confirmed_score * 3 + SPLIT_SCORE_INTERVAL * 10
                if raw_score > max_reasonable:
                    print(f"  → 急増スキップ: {confirmed_score} → {raw_score} (上限 {max_reasonable})")
                    candidate_score = None
                    candidate_count = 0
                    time.sleep(0.5)
                    continue

            # --- 減少フィルタ（誤認識ノイズ除去）---
            # ルートモードでは弾を撃つと1点ずつ減るため小さな減少は正常
            # MAX_SCORE_DROP を超える急減（例: 47820→4782）は誤認識として拒否
            if confirmed_score is not None and raw_score > 0 and raw_score < confirmed_score - MAX_SCORE_DROP:
                print(f"  → 急減スキップ: {confirmed_score} → {raw_score} (許容下限 {confirmed_score - MAX_SCORE_DROP})")
                candidate_score = None
                candidate_count = 0
                time.sleep(0.5)
                continue

            # --- 安定化フィルタ ---
            # 同じ値が STABLE_COUNT 回連続で出たときだけ「確定」とする
            if raw_score == candidate_score:
                candidate_count += 1
            else:
                candidate_score = raw_score
                candidate_count = 1

            if candidate_count < STABLE_COUNT:
                time.sleep(0.5)
                continue

            # 前回と同じ確定値なら何もしない
            if candidate_score == confirmed_score:
                time.sleep(0.5)
                continue

            prev_score = confirmed_score
            confirmed_score = candidate_score
            print(f"[確定] スコア: {prev_score} → {confirmed_score}")

            # ── 初回確定（スクリプト途中起動時） ──
            if not started:
                # 途中からスクリプト起動（スコアが既に非ゼロ・acklog未検知）
                # タイマー操作はせず、現在のマイルストーンから監視開始
                last_split_milestone = confirmed_score // SPLIT_SCORE_INTERVAL
                print(f"  → 途中参加: マイルストーン {last_split_milestone} から監視開始")
                started = True
                time.sleep(0.5)
                continue

            # ── スプリット ──
            current_milestone = confirmed_score // SPLIT_SCORE_INTERVAL
            while current_milestone > last_split_milestone:
                last_split_milestone += 1
                print(f"[ACTION] Split! {last_split_milestone * SPLIT_SCORE_INTERVAL}点到達")
                send_livesplit("split")

            time.sleep(0.5)

if __name__ == "__main__":
    main()
