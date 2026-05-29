import mss
from PIL import Image

# ============================================================
# ★ 調整ポイント ★
# ゲームを起動した状態で python calibrate.py を実行してください。
# 生成された calibrate_check.png を開き、
# 「|」以降のスコア数字だけが白く写っていれば OK です。
# はみ出たり欠けたりする場合はここの値を変更してください。
# 確定したら pogo_autosplit_score.py の同名の定数にも同じ値を設定してください。
# ============================================================
LEFT_CAPTURE_TOP    = 70   # スコア行の上端（px）
LEFT_CAPTURE_LEFT   = 325  # 「|」の少し右から開始（px）
LEFT_CAPTURE_WIDTH  = 200  # 数字全体を覆う幅（px）
LEFT_CAPTURE_HEIGHT = 150  # 全プレイヤー行をカバーする高さ（px）
# ============================================================

with mss.mss() as sct:
    region = {
        "top":    LEFT_CAPTURE_TOP,
        "left":   LEFT_CAPTURE_LEFT,
        "width":  LEFT_CAPTURE_WIDTH,
        "height": LEFT_CAPTURE_HEIGHT,
    }
    print(f"キャプチャ領域: TOP={LEFT_CAPTURE_TOP}, LEFT={LEFT_CAPTURE_LEFT}, WIDTH={LEFT_CAPTURE_WIDTH}, HEIGHT={LEFT_CAPTURE_HEIGHT}")

    screenshot = sct.grab(region)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    # 3倍拡大して細部を確認しやすくする
    img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
    img.save("calibrate_check.png")
    print("calibrate_check.png を保存しました。")
    print("画像を開いて「|」以降の数字部分だけが白く写っているか確認してください。")
    print("左に「|」が見える場合は LEFT_CAPTURE_LEFT を少し大きくしてください。")
    print("数字が右にはみ出る場合は LEFT_CAPTURE_WIDTH を大きくしてください。")
    print("値が決まったら pogo_autosplit_score.py の同名定数にも同じ値を設定してください。")