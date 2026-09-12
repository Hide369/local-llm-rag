# 画像資料の取り込みとアップロードUIの改善 設計書

日付: 2026-09-11
対象: `ingest/image_text.py`（新規）, `ingest/ocr.py`, `ingest/parsers/`（image・drawio 新規、md・xlsx・docx・pdf・pptx 変更）,
`ingest/models.py`, `ingest/retrieval.py`, `scripts/ingest_source.py`, `rag_chat_app.py`

## 1. 目的

利用者から5件の要望が出た。すべて「画像の中の情報が索引に入らない」か、その周辺のUIである。

| # | 要望 | 現状 |
|---|---|---|
| 2 | `.drawio` `.png` `.jpeg` を取り込めるようにする | `SUPPORTED_SUFFIXES` は6形式のみ。未対応拡張子は `UnsupportedFormatError` |
| 3 | Markdown の `![alt](image.png)` が指す画像も取り込む | リンク記法が本文にそのまま残るだけ |
| 4 | アップロード済み一覧をボックス内に入れ、右にスクロールバーを出す | 一覧がダイアログへ直に積まれ、件数が増えるほどダイアログが縦に伸びる |
| 5 | 「閉じる」ボタンを一覧の上に置く | 一覧の下にあり、件数が増えると画面外へ流れる |
| 6 | Excel に貼ったスクリーンショットの内容を読む | `xlsx_parser` は `read_only=True` で開いており、このモードでは画像が一切見えない |

当初は別の要望として「回答にプログラム例を出すときの『参考：〜』を消す」があったが、
依頼者が取り下げた。本設計書は扱わない。

設計のレビューを受けて **docx の埋め込み画像**を範囲に加えた（10節）。要望6と同じ
「貼り付けた画像の中身が索引に入らない」問題であり、`source/` にある議事録5件がすべて
docx である以上、Excel だけを直しても同じ質問に答えられない。

## 2. 中心にある問題

画像からテキストを作る手立ては2つあり、どちらも既にこのリポジトリにある。

- `ingest/ocr.py` — RapidOCR。画像の中の**文字**を読む。
- `ingest/vlm.py` — Ollama の qwen2.5vl。画像の**意味**を説明する。

しかし結線が形式ごとにばらばらである。

- OCR は `ocr_page(page)` という署名で、PyMuPDF の page オブジェクトしか受け取れない。
  PDF 以外からは呼べない。
- VLM は bytes を受け取るが、呼んでいるのは `pdf_parser` と `pptx_parser` だけである。
- 「装飾画像なら捨てる」判定と `[図の説明] ` という接頭辞が、その2つのパーサーに写して書かれている。

新しい形式を4つ足し、既存の3形式にも広げるたびにこの判断を写すのは持たない。**バイト列を受け取ってテキストを返す
1つのモジュール**を作り、全パーサーがそこを通る形にする。

## 3. アーキテクチャ

```
                        ┌──────────────────────────────┐
  image bytes ─────────▶│ ingest/image_text.py          │
                        │   describe_image(bytes, cap)  │
                        │     ├ vlm  → [図の説明] …      │
                        │     └ ocr  → [画像内の文字] …  │
                        └───────────────┬──────────────┘
                                        │ str | None
   ┌──────────┬──────────┬────────┼────────┬──────────┬──────────┐
   │          │          │        │        │          │          │
image_parser drawio_p. md_parser xlsx_p. docx_parser pdf_parser pptx_parser
(.png/.jpg) (ラベルは  (![](…))  (_images) (a:blip)   (埋め込み)  (PICTURE)
             XMLから)
```

`drawio_parser` だけが `describe_image` を通らない。XML にラベル文字が構造化された
まま入っており、画像化して読み直す理由が無いためである（7.1）。

`describe_image` は `caption_image` を引数で受ける。`vlm.caption_image` を直接 import
しない理由は既存のパーサーと同じで、テストが Ollama を必要としないようにするためである。

OCR の扱いは VLM と非対称になる。`ocr_bytes` を省略したときは `ingest.ocr` を
**遅延 import して既定で OCR を行う**。VLM と違い OCR は外部サービスを必要とせず、
疎通確認も要らないためで、呼び出し側が毎回渡す理由がない。これは `pdf_parser` が
`ocr_page` を省略時に自分で import しているのと同じ形である。テストは引数で
フェイクを渡し、RapidOCR のエンジン生成（実測4.8秒）を避ける。

## 4. `ingest/image_text.py`（新規）

```python
CAPTION_PREFIX = "[図の説明] "
OCR_PREFIX = "[画像内の文字] "
DECORATION = "装飾画像"
MIN_OCR_CHARS_FOR_DECORATION = 10

def describe_image(image_bytes, caption_image=None, ocr_bytes=None, label="") -> str | None
def is_image_block(text: str) -> bool
```

### 4.1 出力の組み立て

VLM の説明を先に、OCR の文字を後に置く。読み手（および回答を組み立てる LLM）が
「何の図か」を先に掴んでから細部を読むほうが、逆より辿りやすいためである。

```
[図の説明] 受注から出荷までの業務フローを示した図です。…
[画像内の文字] 受注登録 在庫引当 出荷指示 … 承認者 部長
```

### 4.2 どちらかが欠けたとき

| VLM | OCR | 結果 |
|---|---|---|
| 説明あり | 文字あり | 2行とも入れる |
| 説明あり | 0文字 | 説明だけ |
| 失敗・未設定 | 文字あり | 文字だけ |
| 「装飾画像」 | 10文字未満 | `None`（ブロックごと捨てる） |
| 「装飾画像」 | 10文字以上 | 文字だけ入れる |
| 失敗・未設定 | 0文字 | `None` |

「装飾画像」かつ OCR が短いときに捨てるのは、ロゴに含まれる社名の断片のような
数文字が全資料に散らばるのを防ぐためである。全チャンクに現れる語は順位を決める力を
持たず、ベクトルを一様に濁らせる（`pptx_parser._clean` がフッタを落とすのと同じ理由）。
10文字は未実測の仮値であり、実データを入れてから調整する前提とする。

### 4.3 失敗の扱い

1枚の画像の失敗が本文を道連れにしない。`pdf_parser._describe_images` の既存方針を
そのまま引き継ぎ、例外は握って `stderr` に警告を出す。`label` 引数は
その警告に出す位置情報（`"モデル就業規則.pdf p.12"` など）である。

VLM と OCR は**別々に握る**。片方が失敗しても、もう片方の結果はそのまま使う。
両方が失敗（または両方が空）だったときだけ `None` を返す。まとめて1つの `try` に
入れると、VLM が落ちているだけで OCR の読めた文字まで捨てることになる。

### 4.4 `is_image_block`

`pptx_parser._split_title` は「先頭ブロックが画像キャプションかどうか」を
`startswith(_CAPTION_PREFIX)` で判定している。OCR だけが取れた画像は `[画像内の文字]`
で始まるため、この判定を2つの接頭辞の両方に対応させる必要がある。判定を
`image_text` 側に置き、接頭辞の定義と使用箇所を離さない。

## 5. `ingest/ocr.py` の変更

```python
def ocr_bytes(data: bytes) -> str:   # 新規。エンジンの遅延生成はここへ移す
def ocr_page(page) -> str:           # 既存。ocr_bytes(page.get_pixmap(...).tobytes("png")) を呼ぶだけ
```

RapidOCR には現状も PNG のバイト列を渡している（`page.get_pixmap(dpi=OCR_DPI).tobytes("png")`）。
したがってエンジンの扱いも `reset_engine()` も変えずに済む。`ocr_page` を残すのは
`pdf_parser` が DPI 指定つきのラスタライズを必要とするためで、この責務は PDF 側にある。

## 6. `ingest/parsers/image_parser.py`（新規）

`.png` `.jpg` `.jpeg` を 1ファイル = 1ユニット（`location_type=DOCUMENT`）にする。
画像1枚には見出しもページも無く、書き手が引いた境界が存在しない（`txt_parser` と同じ判断）。

```python
def parse_image(path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]
```

- 本文は `describe_image(path.read_bytes(), caption_image, label=path.name)` の結果そのもの。
- `None` なら空リストを返す。読めない画像を空チャンクとして DB に入れると、
  どの質問にも弱く一致する（`xlsx_parser` が空シートを飛ばすのと同じ理由）。
- `ParsedUnit.ocr` は OCR 由来の行があるとき、`.vlm` は VLM 由来の行があるときに立てる。
  出典の `（OCR）` 表示と、後からどの経路で入ったかを追えるようにするため。
- `.drawio.png`（XML を埋め込んだ PNG）はこの経路に入り、画像として読まれる。
  埋め込み XML の取り出しは今回やらない（15節）。

## 7. `ingest/parsers/drawio_parser.py`（新規）

### 7.1 なぜ OCR/VLM ではなくラベル抽出か

`.drawio` は mxGraph の XML であり、図形のラベル文字が**構造化されたテキストとして
ファイルの中にある**。画像化して読み直すのは、手元にある正解を捨てて推測し直すのと同じで、
OCR の誤認識を新たに持ち込む。加えて画像化には draw.io デスクトップ版の CLI が要り、
サーバー環境へ外部バイナリを1つ増やすことになる。依頼者と合意のうえラベル抽出を採る。

失うのは「図の見た目の説明」だけである。矢印の向きや囲みの入れ子は取れない。

### 7.2 読み方

1ファイルには `<diagram>` が複数入りうる（draw.io のページ）。**1ページ = 1ユニット**とする。
ページは書き手が引いた区切りそのものであり、PDF のページ・PPTX のスライド・
Excel のシートと同じ扱いにする。

```
<mxfile>
  <diagram name="業務フロー" id="…">  ← base64(raw deflate(urlencode(XML))) または生のXML
```

展開は `base64.b64decode` → `zlib.decompress(data, -15)` → `urllib.parse.unquote` の順。
`-15` は raw deflate（zlib ヘッダ無し）を意味し、これを省くと必ず `zlib.error` になる。
中身が `<` で始まるときは非圧縮なのでそのまま使う。draw.io は設定で圧縮を切れるため、
両方を受ける必要がある。

ラベルは `mxCell/@value` と `object/@label` の2箇所にある。後者は draw.io が
カスタムプロパティ付きの図形に使う形式で、片方だけを見ると図の半分が黙って消える。

### 7.3 並び順とラベルの整形

`mxGeometry` の `y` を主・`x` を副にして並べる。XML 上の並び順は作成順であり、
図を読む順とは一致しない（`pptx_parser._position` と同じ問題・同じ解き方）。
`mxGeometry` を持たない要素（辺のラベル等）は末尾へ置く。

ラベルには HTML が入る（実測: `<b>受注</b><br>登録`）。タグを落とし、`<br>` は空白にする。
落とさないとタグの文字列がそのまま索引され、Streamlit の Markdown にも文字として出る
（`answer_text.strip_html_tags` が回答側で同じ問題を扱っている）。

### 7.4 出典

`ingest/models.py` に `DIAGRAM = "diagram"` を足す。表示は `構成図.drawio 図「業務フロー」`。
`location` は通し番号、`heading` にページ名を入れる。ページ名の重複でチャンクIDが
衝突しないよう位置の一意性を通し番号に持たせるのは、`md_parser`・`xlsx_parser` と同じ。
ページ名が無い `<diagram>` はファイル名だけを出典にする。

変更箇所は `Hit._one_citation()`（`ingest/retrieval.py`）と `_POSITION_LABELS`
（`scripts/ingest_source.py`）の2箇所。

## 8. `ingest/parsers/md_parser.py` の変更

### 8.1 対象

コードフェンスの**外**にある `![alt](path)` だけを処理する。フェンス内はコード例であり、
そこに書かれたリンクは資料そのものではない。フェンスの開閉は `parse_md` が既に
追跡している（`in_fence`）ので、その判定を画像の抽出にも使う。

`http://` `https://` `data:` で始まる参照は対象外とする。前者はネットワークへ出ることに
なり（`AGENTS.md` の「外部へ出る通信」の方針に反する）、後者はこの資料群に現れない。

### 8.2 差し替え

リンク記法を、その場で説明文に置き換える。

```
入力:  手順は以下の画面で行う。
       ![管理画面](images/admin.png)
       権限は管理者のみ。

本文:  手順は以下の画面で行う。
       [図の説明] 管理画面のユーザー一覧が表示されている。…
       [画像内の文字] ユーザー管理 権限 管理者 一般 追加 削除
       権限は管理者のみ。
```

行ごと消して末尾へ集めるのではなく**その場**で置き換えるのは、画像が前後の文と
一緒に1つのセクション（＝1チャンク）に入るようにするためである。`## 見出し` ごとに
ユニットを作るこのパーサーでは、位置を保てば文脈も保たれる。

`describe_image` が `None` を返した画像はリンク記法ごと削除する。`![](…)` を本文に
残しても検索の役に立たず、回答へ引き写されると存在しない画像を指すことになる。

### 8.3 画像が見つからないとき

パスは md ファイルのあるディレクトリからの相対で解決する。見つからなければ
**警告を出して本文だけ取り込む**（依頼者の選択）。画面から md だけをアップロードした
場合は必ずこの経路に入る。警告は `stderr` と、`IngestReport` 経由で画面にも出す。

`IngestReport` に `missing_images: dict[str, list[str]]`（資料キー → 見つからなかった
参照先）を足し、`prompting.format_report()` と CLI の結果表示に1行足す。件数だけでは
どの画像が抜けたのか追えず、`dropped` を件数ではなく現物で持っているのと同じ理由である。

```
画像が見つかりません 手順書.md: images/admin.png、images/list.png
```

パーサーから報告までの経路は**コールバックで渡す**。`parse()` が
`on_missing_image=None` を受け、`_ingest_one` が資料キーごとの収集関数を渡す。

```python
def parse(path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]
```

戻り値へ相乗りさせない理由は、見つからない画像が**ユニットを1つも生まない
セクションにも現れうる**ためである。`list[ParsedUnit]` に載せる場所がない。
モジュール変数へ溜めるのも採らない。取り込みは1ファイルずつ進むが、状態が
呼び出しの外に残ると、テストの実行順で結果が変わる。`ingest_directory` が
`notify` を引数で受け取っているのと同じ形にする。

`caption_image` と同じく、**全パーサーがこの引数を受ける署名に揃える**。
使うのは `md_parser` だけで、他は受け取って捨てる。使う側だけに足すと、
ディスパッチャが拡張子ごとに引数を出し分けることになり、11節で消したばかりの
`if` が別の形で戻ってくる。

パスの解決では `..` を辿って資料の置かれたディレクトリの外へ出る参照を拒む。資料が
指定した文字列をそのままファイルシステムへ渡す唯一の箇所であり、外部入力の検証が要る。

## 9. `ingest/parsers/xlsx_parser.py` の変更

### 9.1 なぜ2回開くのか

本文の抽出は `read_only=True` のままにする。このモードは行を逐次読むためメモリを
食わず、大きなブックでも通る。しかし `read_only=True` では `Worksheet._images` が
空のままであり、画像は一切見えない（これが要望6の原因である）。

`caption_image` が渡されたときだけ、画像取得のために2回目のロードを行う。
渡されていないときは1回で済み、既存の取り込み時間は変わらない。

### 9.2 画像の取り出し

実測（openpyxl 3.1.5）で `load_workbook(path)` の後、`sheet._images[i].ref` が
`BytesIO` になることを確認した。ブックを組み立てた直後は `ref` がパスや PIL の
Image になりうるため、`getvalue()` を持つかで分岐して両方を受ける。

`_images` は openpyxl の私的 API である。公開 API に画像を取り出す口が無く、代替は
`zipfile` で `xl/media/` と `xl/drawings/*.rels` を辿ってシートとの対応を自力で
組み立てる案だが、コード量が大きく増える。私的 API への依存は `requirements.txt` で
バージョンを固定していること、および実装の最初にこの1点を実データで確かめることで
受け入れる。壊れた場合の退避先（zipfile 案）をこの節に記録しておく。

### 9.3 並びと本文への入れ方

画像はシート本文の末尾に置く。`anchor._from.row` → `.col` の順に並べ、セルの
読み順に揃える。行の途中へ差し込まないのは、`_row_text` が作る「セル | セル」の
1行構造を壊さないためである。

```
報告
件名 | 2026年9月度 障害報告
発生日 | 2026-09-03
[図の説明] エラーダイアログのスクリーンショット。…
[画像内の文字] エラー コード 0x80070005 アクセスが拒否されました
```

画像しか無いシート（本文が1行も無い）はユニットを作る。現状は空シートを飛ばしているが、
それは「中身が無い」ためであって、画像だけのシートには中身がある。

## 10. `ingest/parsers/docx_parser.py` の変更

### 10.1 現状

```python
text = "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
```

段落のテキストだけを読み、文書全体を1ユニットにしている。画像は一切見ていない。
議事録の docx が5件あり、そこに貼られた画面写真は索引に入っていない。

### 10.2 読み順の取り方

1ユニットにまとめる形式なので、画像を本文のどの位置へ入れるかがそのまま読みやすさに
なる。段落を走査し、その段落に画像があればその場に差し込む。

実測（python-docx 1.2.0）で、段落の要素に対する XPath が読み順どおりの関係IDを返し、
関係IDから画像のバイト列が取れることを確認した。

```python
for paragraph in document.paragraphs:
    for rid in paragraph._p.xpath(".//a:blip/@r:embed"):
        blob = document.part.related_parts[rid].blob
```

`._p` は python-docx の私的属性である。公開 API に段落中の画像を辿る口が無い。
`xlsx_parser` の `ws._images` と同じ扱いで、バージョンを固定していること、および
テストが画像1枚を検出することで壊れたら気づけることをもって受け入れる。

### 10.3 段落に現れない画像

**同じ実測で、表のセルに入れた画像は `document.paragraphs` に現れなかった**
（関係IDは存在するが、どの段落の XPath にも出てこない）。浮動配置の画像も
同様に取りこぼす。

> 訂正（レビュー指摘、実装後）: 当初はヘッダー・フッターの画像も「同様に
> 取りこぼすが末尾には付く」と書いていたが誤りだった。ヘッダー・フッターは
> `document.part` とは別のパートであり、そこに埋め込まれた画像は
> `document.part.related_parts` に現れない（現れるのはヘッダー/フッターパート
> 自身であり、`content_type.startswith("image/")` では弾かれる）。したがって
> 下記の「末尾へ付ける」処理で拾えるのは表のセル・浮動配置の画像だけで、
> ヘッダー・フッターの画像はそもそも見えていない。

段落の走査を終えたあと、`document.part.related_parts` の中で **まだ見ていない画像**を
本文の末尾へ付ける。表の中まで辿る実装を書くより短く、取りこぼしを構造的に無くせる。
位置は失うが、位置を失うのは「本文のどこにも紐づかない画像」だけである。

```
障害報告
発生日: 2026-09-03
[図の説明] エラーダイアログのスクリーンショット。…      ← 段落の位置に差し込み
[画像内の文字] エラー コード 0x80070005
上記のダイアログが表示された。
[図の説明] 組織図。…                                    ← 表の中の画像は末尾へ
```

### 10.4 本文が空の docx

画像だけの docx はユニットを作る。現状は `if not text.strip(): return []` で
空リストを返しているが、その判断は「中身が無い」ことを根拠にしており、
画像があるなら中身はある（`xlsx_parser` の画像だけのシートと同じ判断）。

## 11. `pdf_parser.py` / `pptx_parser.py` の変更

埋め込み画像を `describe_image` に通す。**VLM だけだった経路に OCR が加わる**。

依頼者と合意のうえこうする。スライドや PDF に貼られたスクリーンショットの文字が
読めないという要望6と同じ問題が、この2形式にも等しく存在する。同じ「埋め込み画像」に
2つの規則を残すと、どちらが適用されたのかコードを読まないと分からなくなる。

影響:

- `_CAPTION_PREFIX` と「装飾画像」判定は `image_text` へ移し、両パーサーから消す。
- `pptx_parser._split_title` は `image_text.is_image_block()` を使う。
- 取り込み時間が伸びる。画像1枚あたり OCR が数百ミリ秒（RapidOCR、CPU）加わる。
- **既存資料の再取り込みが要る。** ファイルの内容が変わらないため差分取り込みでは
  拾われない。`python -m scripts.ingest_source --force` を1回流す必要があり、
  README の運用手順にこれを書く。

PDF の画像ページ（OCR フォールバック）の判断は変えない。VLM の説明が1件でも得られた
ページは今までどおり説明文で置き換える。そのうえで、埋め込み画像ごとの OCR が
`describe_image` の中で走るため、結果として文字も残る。

## 12. `ingest/parsers/__init__.py` の変更

```python
_PARSERS = {
    ".pdf": parse_pdf, ".docx": parse_docx, ".pptx": parse_pptx,
    ".md": parse_md, ".txt": parse_txt, ".xlsx": parse_xlsx,
    ".png": parse_image, ".jpg": parse_image, ".jpeg": parse_image,
    ".drawio": parse_drawio,
}

def parse(path, caption_image=None, on_missing_image=None):
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(
        path, caption_image=caption_image, on_missing_image=on_missing_image
    )
```

現行の `if path.suffix.lower() in (".pdf", ".pptx")` という分岐を消す。全パーサーが
`(path, caption_image=None, on_missing_image=None)` の署名に揃う。拡張子ごとの
例外をディスパッチャに残すと、形式を足すたびにこの `if` が伸びる。

| パーサー | `caption_image` | `on_missing_image` |
|---|---|---|
| pdf / pptx / docx / xlsx / image | 使う | 捨てる |
| md | 使う | 使う |
| txt / drawio | 捨てる | 捨てる |

受け取って捨てる引数があるのは承知のうえである。使う側だけに足すと、
ディスパッチャが拡張子を見て引数を出し分けることになり、消したはずの分岐が戻る。

`SUPPORTED_SUFFIXES` が増えることで、`scripts/ingest_source._target_files()` の走査対象と
`rag_chat_app` の `st.file_uploader(type=…)` は自動的に追従する。どちらも
`SUPPORTED_SUFFIXES` から組んでいるためで、変更は要らない。

## 13. `rag_chat_app.py` の変更（要望4・5）

`upload_dialog` の並びを変える。

```
説明キャプション
ファイル選択（file_uploader）
[取り込む]
────────── divider
[閉じる]                      ← 一覧の上へ
アップロード済みの資料
┌─────────────────────┬─┐
│ ファイル名    [削除]   │▓│  ← st.container(height=240, border=True)
│ ファイル名    [削除]   │ │     高さを固定するとStreamlitが縦スクロールを出す
└─────────────────────┴─┘
```

- 「閉じる」を一覧の上へ移す。今は一覧の下にあり、資料が増えるとダイアログの
  外へ流れて押せなくなる。
- 一覧を `st.container(height=240, border=True)` に入れる。`height` を渡した
  コンテナは内容がはみ出すと縦スクロールを出す（Streamlit 1.31 以降。本プロジェクトは 1.61.1）。
- 240px は5〜6行が見える高さ。ダイアログ全体が縦に伸びない範囲で選ぶ。
- 一覧が空のときはコンテナごと出さない。空の箱だけが残るのを避ける。

ダイアログ本体のロジック（削除・`st.rerun()`・`upload_dialog_open` フラグ）は変えない。

## 14. データフローとエラー処理

```
scripts/ingest_source._ingest_one
  └ parsers.parse(path, caption_image)
       └ 各パーサー
            └ image_text.describe_image(bytes, caption_image, ocr_bytes, label)
                 ├ caption_image 例外 → 警告して VLM 部分だけ諦める
                 └ ocr_bytes 例外   → 警告して OCR 部分だけ諦める
```

- `caption_image` が `None`（VLM 未接続）でも取り込みは通る。既存の
  `caption_image_or_reason()` の方針をそのまま使う。
- OCR エンジンの生成に失敗したとき（onnxruntime の異常等）も同様に警告のみ。
  OCR は取り込みが成立する条件ではない。
- 片方が失敗しても、もう片方の結果は使う。両方失敗した画像だけが `None` になる。
- 1ファイルの失敗が全体を止めないのは既存どおり（`_ingest_one` の `except Exception`）。

## 15. 今回やらないこと

- **`.drawio.png` / `.drawio.svg` に埋め込まれた XML の取り出し。** 画像として読む。
  必要になったら PNG の `tEXt` チャンクから取り出す実装を足せる。
- **draw.io CLI による図の画像化。** 外部バイナリへの依存を増やさない（7.1）。
- **`.gif` `.bmp` `.webp` `.tiff` への対応。** 要望に無く、実データにも無い。
  対応するときは `image_parser` の登録を1行増やすだけで済む。
- **md と画像をまとめた zip のアップロード。** 依頼者が「警告を出して本文だけ」を選んだ。
- **画像の重複検出。** 同じロゴが全ページに入っている資料では同じ説明文が繰り返される。
  既存のチャンク畳み込み（`ingest/store.py`）が本文単位で吸収する範囲に任せる。
- **docx の表のセルに書かれた「文字」。** 現行の `docx_parser` は段落しか読んでおらず、
  表の本文は元から索引に入っていない。今回入るのは表の中の「画像」だけである（10.3）。
  文字のほうは今回の要望と別の欠落であり、直すなら単独の変更として扱う。

## 16. テスト方針

ネットワークもモデルも使わない。`caption_image` と `ocr_bytes` は差し替え可能な
引数なので、既存の `test_parser_pdf.py` / `test_parsers_office.py` と同じくフェイクを渡す。
画像は Pillow でその場で生成する（`pillow==12.3.0` は既に `requirements.txt` にある）。

| ファイル | 主な検証 |
|---|---|
| `tests/test_image_text.py`（新規） | 4.2 の表の6通り。片方が例外でももう片方の結果を返すこと |
| `tests/test_parser_image.py`（新規） | 1ファイル1ユニット。読めない画像は0ユニット。`ocr`/`vlm` フラグ |
| `tests/test_parser_drawio.py`（新規） | 圧縮・非圧縮の両方。複数ページ。`object/@label`。HTMLタグ除去。y→x の並び |
| `tests/test_parser_md.py` | 画像参照の差し替え位置。フェンス内は対象外。http は対象外。不明画像の警告。`..` での脱出拒否 |
| `tests/test_parser_xlsx.py` | 画像がシート末尾に付く。画像だけのシートがユニットになる。`caption_image=None` なら2回目のロードをしない |
| `tests/test_parsers_office.py` | docx: 段落の位置に画像が差し込まれる。表の中の画像が末尾に付く。画像だけの docx がユニットになる |
| `tests/test_parser_pdf.py` / `test_parsers_office.py` | OCR が加わっても既存の期待が壊れないこと |
| `tests/test_ocr.py` | `ocr_page` が `ocr_bytes` に委譲すること |
| `tests/test_retrieval.py` | `diagram` 種別の出典文字列 |
| `tests/test_rag_chat_app.py` | ダイアログの要素順（閉じるが一覧より前） |
| `tests/test_ingest_source.py` | `missing_images` が報告に載ること |

## 17. ドキュメントの更新

- `README.md` — 対応形式の一覧、`--force` での再取り込みが要ること、
  drawio がラベル抽出であること（＝矢印や入れ子は取れないこと）を「既知の制約」に。
- `docs/処理箇所マップ.md` — 新モジュールと新パーサーの行を追加。
- `docs/依存関係一覧.md` — 新しい依存は無い。`pillow` の用途欄に
  「テストの画像生成」に加えて「xlsx 埋め込み画像の読み出し（openpyxl 経由）」を足す。

## 18. 残るリスク

- **`ws._images`（openpyxl）と `paragraph._p`（python-docx）は私的 API である。**
  上げたときに黙って空リストになりうる。どちらもバージョンは固定してあり、
  テストが画像1枚を検出することで検知できる（9.2 / 10.2）。
- **OCR を全埋め込み画像に広げると取り込みが遅くなる。** 実測してから README の
  所要時間を書き直す。極端に遅ければ画像の最小サイズの閾値（`MIN_IMAGE_WIDTH` 等）で
  絞る余地がある。
- **10文字という装飾画像の閾値は未実測である。** 実データを入れてから調整する。
- **drawio のラベル順は座標に依存する。** 自動整列されていない図では読み順が
  直感と合わないことがある。図の構造そのものは取れないという 7.1 の制約の一部である。
