# Pogostuck Loot Mode オートスプリッター（スコアベース版）

> 🇺🇸 [English version available here](README.en.md)

Pogostuck の Loot Mode において、画面 OCR でスコアを読み取り、LiveSplit のタイマーを自動制御するスクリプトです。

## 概要

ゲーム画面左上に表示されるスコア部分（例: `@ 5 | 10000` の `10000` 部分）を 0.5 秒ごとキャプチャ・OCR し、スコアが `SPLIT_SCORE_INTERVAL` の倍数を超えるたびに LiveSplit へ `split` コマンドを送信します。

- 自身のスコアは黄色テキストで表示されるため、黄色ピクセルのみを抽出して認識します
- ゲームのログファイル（`acklog.txt`）を監視し、新しいランのシード生成を検知してタイマーを自動リセット＆再スタートします

## ファイルのダウンロード

1. ページ上部にある緑色の **「Code」** ボタンをクリック
2. **「Download ZIP」** をクリック
3. ダウンロードされた ZIP ファイルを任意のフォルダに展開する

> Git や clone は不要です。ZIP を展開するだけで使えます。

## ファイル構成

| ファイル | 説明 |
|---|---|
| `pogo_autosplit_score.py` | メインスクリプト。指定点数ごとにスプリット・acklog.txtのシード検知でリセット |
| `calibrate.py` | キャプチャ領域を確認するためのキャリブレーションツール |
| `sample_calibrate_check.png` | キャリブレーション成功時の参考画像 |
| `LiveSpilitLayout_LootScore.lsl` | LiveSplit レイアウトファイル |
| `Pogostuck Rage With Your Friends - Loot Score.lss` | LiveSplit スプリットファイル |

## 必要なもの（一覧）

| ツール／ライブラリ | 入手先 | 用途 |
|---|---|---|
| Python 3.10 以上 | https://www.python.org/downloads/ | スクリプトの実行環境 |
| Tesseract OCR | https://github.com/UB-Mannheim/tesseract/wiki | 画像から数字を読み取るエンジン |
| LiveSplit | https://livesplit.org/ | タイマー表示・スプリット管理 |
| mss / pytesseract / Pillow / numpy | `pip install` で導入（後述） | スクリプトが使用する Python ライブラリ |

## セットアップ手順

> 初めての方は **Step 1 〜 Step 7 を順番に** 行ってください。  
> 既に Python や Tesseract を導入済みの方は該当ステップを読み飛ばして構いません。

---

### Step 1：Python のインストール

1. [https://www.python.org/downloads/](https://www.python.org/downloads/) を開く
2. **「Download Python 3.x.x」** ボタンをクリックしてインストーラーをダウンロード
3. ダウンロードしたファイルを実行する
4. インストール画面で **「Add Python to PATH」にチェックを入れる**（重要）
5. **「Install Now」** をクリックして完了まで待つ

> ✅ 確認方法：インストール後にコマンドプロンプト（後述）で `python --version` と入力して `Python 3.x.x` と表示されればOKです。

---

### Step 2：Tesseract OCR のインストール

1. [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) を開く
2. **「tesseract-ocr-w64-setup-x.x.x.exe」**（64ビット版）をダウンロード
3. ダウンロードしたファイルを実行する
4. インストール先はデフォルトの `C:\Program Files\Tesseract-OCR\` のままにする（変更した場合はスクリプトの修正が必要）
5. 完了まで待つ

---

### Step 3：LiveSplit のインストール

1. [https://livesplit.org/](https://livesplit.org/) を開く
2. **「Download」** ボタンからZIPをダウンロードし、任意のフォルダに展開する
3. `LiveSplit.exe` を起動する
4. LiveSplit ウィンドウを右クリック → **「Settings」** → 「Startup Behavior:」項目で **「Start TCP Server」** を選択する


> ✅ Server Portはデフォルトで16834になっています。

付属の `.lss` / `.lsl` ファイルを読み込むと、スプリット設定とレイアウトをそのまま利用できます。

> ※1 `.lss` スプリットファイルはスプリット数に合わせて手動で編集してください（`SPLIT_SCORE_INTERVAL` と LiveSplit のセグメント数を揃えること）。  
> ※2 `.lsl` レイアウトファイルは OBS の配信上に乗せるため、背景をマゼンタにして透過してあります。お好みで変更してください。

---

### Step 4：Python ライブラリのインストール

**コマンドプロンプトの開き方：**

1. キーボードの **Windows キー + R** を押す
2. 「ファイル名を指定して実行」に `cmd` と入力して **Enter**
3. 黒いウィンドウ（コマンドプロンプト）が開く

**ライブラリのインストール：**

コマンドプロンプトに以下を貼り付けて **Enter**：

```
pip install mss pytesseract Pillow numpy
```

`Successfully installed ...` と表示されればインストール完了です。

---

### Step 5：スクリプトの配置

1. このリポジトリの ZIP を展開したフォルダを開く
2. フォルダのアドレスバーに `cmd` と入力して **Enter**（そのフォルダでコマンドプロンプトが開く）

---

### Step 6：キャリブレーション（初回・解像度変更時）

ゲームを起動した状態で以下を実行します。

```
python calibrate.py
```

`calibrate_check.png` が生成されます。ファイルを開いて **`| スコア` の数字部分だけが白く写っている** ことを確認してください。  
同梱の `sample_calibrate_check.png` が正常時の参考画像です。

数字がはみ出たり欠ける場合は、**`calibrate.py`** の先頭にある以下の定数をメモ帳などで調整してください。

```python
LEFT_CAPTURE_TOP    = 70   # スコア行の上端（px）
LEFT_CAPTURE_LEFT   = 325  # 「|」の少し右から開始（px）
LEFT_CAPTURE_WIDTH  = 200  # 数字全体を覆う幅（px）
LEFT_CAPTURE_HEIGHT = 150  # 全プレイヤー行をカバーする高さ（px）
```

値が決まったら、**`pogo_autosplit_score.py`** の先頭にある同名の定数にも同じ値を設定してください。

---

### Step 7：スクリプトの起動

LiveSplit の Server が起動済みの状態で、コマンドプロンプトに以下を入力します。

```
python pogo_autosplit_score.py
```

起動後にゲームを始めると、新しいランのシードが生成された瞬間にタイマーが自動リセット＆スタートします。

> ⚠️ **注意：** スクリプト起動前にゲームがすでに動いていた場合（古い `acklog.txt` が存在する場合）でも、スクリプト起動**後**に書き込まれた新シードのみを検知するため、誤動作しません。

## 動作フロー

```
① 0.5秒ごとに画面左上の「| スコア」領域をキャプチャ
      ↓
② numpy で黄色ピクセルのみを白に変換（自身のスコア行のみ抽出）
      ↓
③ 画像を3倍に拡大（OCR 精度向上）
      ↓
④ Tesseract OCR で数字を認識（whitelist: 0123456789）
      ↓
⑤ 急増・急減フィルタで誤認識値を除外
      ↓
⑥ 同じ値が STABLE_COUNT 回連続で出たら確定
      ↓
⑦ スコアが SPLIT_SCORE_INTERVAL の倍数を超えた → LiveSplit へ "split" 送信
   acklog.txt に新シードが書き込まれた → LiveSplit へ "reset" + "starttimer" 送信
```

## 設定値

スクリプト冒頭の `★ 設定ここから ★` ブロックで動作を調整できます。

| 定数 | デフォルト | 説明 |
|---|---|---|
| `TESSERACT_CMD` | `C:\...\tesseract.exe` | Tesseract の実行ファイルパス |
| `LOG_FILE` | `C:\...\acklog.txt` | Pogostuck のログファイルパス（リセット検知に使用） |
| `LEFT_CAPTURE_TOP` | `70` | キャプチャ領域の上端（px） |
| `LEFT_CAPTURE_LEFT` | `325` | キャプチャ領域の左端（px）。`\|` の右側から開始 |
| `LEFT_CAPTURE_WIDTH` | `200` | キャプチャ幅（px） |
| `LEFT_CAPTURE_HEIGHT` | `150` | キャプチャ高さ（px） |
| `SPLIT_SCORE_INTERVAL` | `3000` | スプリットする点数間隔（例: 1000, 5000, 10000） |
| `MAX_SCORE_DROP` | `500` | 許容する最大スコア減少量。これを超える急減は誤認識として無視 |
| `STABLE_COUNT` | `3` | 確定に必要な連続一致回数（誤認識フィルタ） |
| `DEBUG_SAVE_OCR_IMAGE` | `True` | OCR 前処理画像を `debug_ocr.png` として保存 |
| `LIVESPLIT_HOST` | `localhost` | LiveSplit Server のホスト |
| `LIVESPLIT_PORT` | `16834` | LiveSplit Server の TCP ポート |

## デバッグ

`DEBUG_SAVE_OCR_IMAGE = True` にすると、OCR に渡す直前の画像が `debug_ocr.png` として保存されます。黄色テキストが白く抽出されているかを確認してください。

コンソールには以下のような出力が表示されます。

```
[OCR raw LEFT] '10000'
[確定] スコア: 9500 → 10000
[ACTION] Split! 10000点到達
  → LiveSplit送信: split
```

## リセット検知ロジック

| 検知条件 | 動作 |
|---|---|
| `acklog.txt` に `dungeonSetInitialSeed(1) ... lvl(0) seed(N)` が書き込まれ、シード値 `N` が前回と異なる | 新ランが開始された → タイマーリセット＆再スタート |

スクリプト起動時点の `acklog.txt` 末尾位置を記録し、それ以降の新規書き込みのみを監視します。ゲーム未起動状態でスクリプトを先に起動しても、古いシードには反応しません。

## 誤認識フィルタ

| フィルタ | 条件 | 目的 |
|---|---|---|
| 急増フィルタ | `raw > confirmed × 3 + interval × 10` | 桁追加系の誤認識を除外（例: 419 → 900419）|
| 急減フィルタ | `raw < confirmed - MAX_SCORE_DROP` かつ `raw > 0` | 桁落ち系の誤認識を除外（例: 47820 → 4782）|
| 安定化フィルタ | 同じ値が `STABLE_COUNT` 回連続しないと確定しない | 単発ノイズを除外 |
