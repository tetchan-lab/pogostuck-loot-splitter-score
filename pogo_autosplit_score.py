import mss
import pytesseract
from PIL import Image
import socket
import time
import re

# === 設定 ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# @ の後の数字が表示されている領域（座標はキャリブレーション後に調整）
# top, left はウィンドウタイトルバー含む絶対座標
# 複数人ロビー対応版: 自分のテキストは黄色、他プレイヤーは白色
# → 黄色マスクにより自分の行だけが認識される
# height を広げてスコア上位に関係なく全プレイヤー行をカバー（約20px/行 × 4人 + 余裕）
# ※ height は実際の行間隔に応じて調整してください（calibrate.py で確認推奨）
CAPTURE_REGION = {"top": 73, "left": 245, "width": 350, "height": 150}

# LiveSplit Server設定
LIVESPLIT_HOST = "localhost"
LIVESPLIT_PORT = 16834

MAX_LEVEL = 30    # 監視するレベル範囲
STABLE_COUNT = 2  # 同じ値がN回連続で出たら確定（誤認識フィルタ）
SPLIT_SCORE_INTERVAL = 10000  # スプリット間隔（点）← ここを変えるだけ（例: 1000, 5000, 10000）

# デバッグ用：OCR前処理画像を保存する（True で debug_ocr.png に保存）
DEBUG_SAVE_OCR_IMAGE = True

# ===========================

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

def get_game_state(sct, last_split_level: int = 0) -> tuple[int, int] | None:
    """ゲームの現在の状態（レベルとスコア）を取得
    
    Args:
        sct: mssのスクリーンショットオブジェクト
        last_split_level: 現在のスプリットレベル（フォールバック制限用）
    
    Returns:
        tuple[int, int] | None: (level, score) のタプル、取得失敗時は None
    """
    screenshot = sct.grab(CAPTURE_REGION)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

    # ★ 黄色テキストだけを白に、それ以外を黒にマスク
    # 自分のプレイヤー行テキストのみ黄色なので、他プレイヤー（白色）は黒くマスクされる
    import numpy as np
    arr = np.array(img)
    # ゲームUIの黄色: バランス調整（テキストを残しつつ背景ノイズを除外）
    # 黄色 = R高, G高, B低 かつ R-B差が大きい
    yellow_mask = (
        (arr[:,:,0] > 190) &  # R > 190
        (arr[:,:,1] > 170) &  # G > 170
        (arr[:,:,2] < 70) &   # B < 70
        ((arr[:,:,0] - arr[:,:,2]) > 140)  # R-B差が大きい（黄色の特徴）
    )
    masked = np.zeros_like(arr)
    masked[yellow_mask] = [255, 255, 255]  # 黄色 → 白
    img = Image.fromarray(masked.astype(np.uint8), 'RGB')

    # 拡大してOCR精度UP
    img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    # デバッグ用：OCR前の画像を保存
    if DEBUG_SAVE_OCR_IMAGE:
        img.save("debug_ocr.png")

    # psm 11: まばらなテキストモード
    # height 拡大により自分の行は画像内の任意のY位置に出現するため、
    # 単行モード(psm 7)より位置に依存しない psm 11 を使用
    text = pytesseract.image_to_string(
        img,
        config="--psm 11 -c tessedit_char_whitelist=0123456789@| "
    )

    print(f"[OCR raw] '{text.strip()}'")

    # ★ @ あり: "@ 1 | 0" の形式でレベルとスコアを抽出
    # スコア部分はオプショナル（認識できない場合は0として扱う）
    match = re.search(r'@\s*(\d{1,2})\s*\|(?:\s*(\d+))?', text)
    if match:
        level = int(match.group(1))
        score = int(match.group(2)) if match.group(2) else 0
        if 1 <= level <= MAX_LEVEL + 2:
            return (level, score)

    # ★ @ なし fallback: "数字 | 数字" の形式
    # ただし行頭の "1)" の "1" を拾わないよう | の直前を優先
    # スコア部分もオプショナル
    match2 = re.search(r'(\d{1,2})\s*\|(?:\s*(\d+))?', text)
    if match2:
        level_str = match2.group(1)
        score = int(match2.group(2)) if match2.group(2) else 0
        
        # まず通常のレベルとして試す
        level = int(level_str)
        if 1 <= level <= MAX_LEVEL + 2:
            return (level, score)
        
        # 範囲外の2桁数字の場合、下1桁をレベルとして試す（@との癒着対策）
        # 例: "45" → "5" (@ と 5 が癒着して 45 と認識された場合)
        if len(level_str) == 2:
            level = int(level_str[1])  # 下1桁
            if 1 <= level <= MAX_LEVEL + 2:
                print(f"  → 癒着修正: '{level_str}' → Level={level}, Score={score}")
                return (level, score)

    # ★ 最終フォールバック: "| 数字" または "|" のみ → Level1と仮定
    # @とレベル番号が認識できない場合の救済措置
    # 誤判定防止: Level1付近(last_split_level <= 1)でのみ使用
    if last_split_level <= 1:
        match3 = re.search(r'\|\s*(\d+)?', text)
        if match3:
            level = 1  # Level1と仮定
            score = int(match3.group(1)) if match3.group(1) else 0
            print(f"  → フォールバック: Level={level}(仮定), Score={score}")
            return (level, score)

    return None

def do_start(last_split_level, current_level=1):
    """タイマーをリセットして開始
    
    Args:
        last_split_level: 現在のスプリットレベル
        current_level: 開始時のレベル（デフォルト：1）
    
    Returns:
        int: 新しいlast_split_level
    """
    print("[ACTION] タイマー開始")
    send_livesplit("reset")
    time.sleep(0.1)
    send_livesplit("starttimer")
    return current_level  # 現在のレベルを返す

def main():
    print("=== Pogostuck Loot Mode オートスプリッター起動（スコア1万点スプリット版）===")
    print("LiveSplitを起動してTCP Serverを開始してください。")
    print("ゲームを開始したら自動でスプリットが始まります。")
    print("1万点ごとにスプリット、スコア0検知によるリセットも検知します。")
    print("自分のテキストが黄色であることを確認してください。")
    print("Ctrl+C で終了\n")

    confirmed_level = None
    confirmed_score = None
    candidate_state = None  # (level, score) のタプル
    candidate_count = 0
    last_split_level = 0
    last_confirmed_score = 0
    last_split_milestone = 0  # 直近にスプリットした1万点単位の数（例: 3 = 3万点でスプリット済み）

    with mss.MSS() as sct:
        while True:
            raw_state = get_game_state(sct, last_split_level)

            # ★ None は無視（揺れの原因なのでスキップ）
            if raw_state is None:
                time.sleep(0.5)
                continue

            raw_level, raw_score = raw_state

            # --- 安定化フィルタ ---
            if raw_state == candidate_state:
                candidate_count += 1
            else:
                candidate_state = raw_state
                candidate_count = 1

            if candidate_count >= STABLE_COUNT and candidate_state != (confirmed_level, confirmed_score):
                prev_level = confirmed_level
                prev_score = confirmed_score
                confirmed_level, confirmed_score = candidate_state
                print(f"[確定] レベル: {prev_level} → {confirmed_level}, スコア: {prev_score} → {confirmed_score}")

                # ── ゲーム開始（初回）──
                # last_split_level == 0 の時は初回起動と判断（どのレベルから始まってもOK）
                if last_split_level == 0:
                    last_split_level = do_start(last_split_level, confirmed_level)
                    last_split_milestone = 0
                    last_confirmed_score = confirmed_score

                # ── リセット検知1: Level1に戻ってきた ──
                elif confirmed_level == 1 and last_split_level > 1:
                    print("[ACTION] リセット検知（Level変化） → タイマーリセット＆再スタート")
                    last_split_level = do_start(last_split_level)
                    last_split_milestone = 0
                    last_confirmed_score = confirmed_score

                # ── リセット検知2: スコアが0に戻った（Level1中のリセット）──
                elif (confirmed_score == 0 and last_confirmed_score > 0 and 
                      confirmed_level == 1 and last_split_level >= 1):
                    print("[ACTION] リセット検知（スコア0） → タイマーリセット＆再スタート")
                    last_split_level = do_start(last_split_level)
                    last_split_milestone = 0
                    last_confirmed_score = confirmed_score

                # ── 1万点ごとのスプリット ──
                else:
                    current_milestone = confirmed_score // SPLIT_SCORE_INTERVAL
                    while current_milestone > last_split_milestone:
                        last_split_milestone += 1
                        print(f"[ACTION] Split! {last_split_milestone * SPLIT_SCORE_INTERVAL}点到達")
                        send_livesplit("split")
                    last_split_level = confirmed_level
                    last_confirmed_score = confirmed_score

            time.sleep(0.5)

if __name__ == "__main__":
    main()
