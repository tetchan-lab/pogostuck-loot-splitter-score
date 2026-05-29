import mss
from PIL import Image

# ゲームを起動した状態で実行してください
# 左上スコア表示（「| 数字」部分）を確認する用途
# calibrate_check.png を開いて「|」以降の数字だけが入るよう座標を調整してください
# 座標を確定したら pogo_autosplit_score.py の LEFT_* 定数に反映させてください
with mss.mss() as sct:
    # 左上の「| 数字」領域をキャプチャ
    # まずは広めに取って、数字がはみ出ないように座標を絞り込む
    region = {
        "top": 70,
        "left": 325,   # 「|」の少し右から開始（調整ポイント）
        "width": 200,  # 数字全体を覆う幅（調整ポイント）
        "height": 150,  # 左上の1行分の高さ
    }
    print(f"キャプチャ領域: top={region['top']}, left={region['left']}, width={region['width']}, height={region['height']}")

    screenshot = sct.grab(region)
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    # 3倍拡大して細部を確認しやすくする
    img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
    img.save("calibrate_check.png")
    print("calibrate_check.png を保存しました。")
    print("画像を開いて「|」以降の数字部分だけが入っているか確認してください。")
    print("左に「|」が見える場合は left を少し大きくしてください。")
    print("数字が右にはみ出る場合は width を大きくしてください。")