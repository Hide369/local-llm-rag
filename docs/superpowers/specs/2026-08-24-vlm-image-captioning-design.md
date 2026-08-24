# PDF/PPTX埋め込み画像のVLMキャプション化 設計書

作成日: 2026-08-24

## 1. 目的

PDF・PPTXに埋め込まれた図表・写真は、現状まったくテキスト化されずRAGの検索対象から
漏れている。取り込み時にVLM（Vision Language Model）で画像の内容を日本語の説明文に
変換し、周辺のテキストと同じチャンクに含めることで、図表・写真の内容についての質問にも
出典付きで答えられるようにする。

対象はPDFとPPTXのみ（ユーザーの要望どおり）。DOCXは対象外とする（「15. 今回やらないこと」参照）。

## 2. 前提: 過去の検討との違い

[2026-08-15-hybrid-retrieval-design.md](2026-08-15-hybrid-retrieval-design.md) の
「2.1 OCRは原因ではない」で、当時の症状（PPTXスライド11の内容が検索に出てこない）に対して
VLMへの置き換えは解決策にならないと結論づけている。ただしこれは
「**テキストが既に100%取れているスライド**を、VLMで撮り直しても同じ文字列が
得られるだけ」という意味であり、埋め込み画像そのものへの言及ではない。

今回のスコープは別物である。テキストボックスに文字が無く、図表・写真だけが
置かれている（あるいはPDFの本文ページに埋め込まれた図表・写真が本文の外に存在する）
箇所を対象にする。これらは現状、OCRにもテキスト抽出にも一切引っかからず、
100%取りこぼされている。

## 3. アーキテクチャ

新規 `ingest/vlm.py` を [ingest/embedder.py](../../../ingest/embedder.py) と同じ
パターン（`requests.Session` 注入・指数バックオフでの再試行・タイムアウト）で作り、
Ollamaの `/api/chat` にbase64画像を渡してキャプションを取得する。

`ingest/parsers/pdf_parser.py` と `ingest/parsers/pptx_parser.py` は、既存の
`ocr_page` 注入パターン（テストでの差し替え・実装からの分離のために使われている）を
踏襲し、`caption_image` という新しい注入可能パラメータを追加する。既定は `None`
（無効）とし、呼び出し側が実際の関数を渡したときだけ画像処理を行う。これにより
「取り込み時間を増やしたくない人は今までどおり」というオプトインが、新しいフラグや
条件分岐を増やさず自然に実現できる。

## 4. `ingest/vlm.py`（新規）

```python
VLM_MODEL = os.environ.get("OLLAMA_VLM_MODEL", "qwen2.5vl:7b")
```

- `caption_image(image_bytes: bytes, session=None) -> str`
  `POST {OLLAMA_HOST}/api/chat` に `{"model": VLM_MODEL, "messages": [{"role": "user",
  "content": CAPTION_PROMPT, "images": [base64...]}], "stream": False}` を送り、
  `response["message"]["content"]` を返す。失敗時の再試行・バックオフ・タイムアウトは
  `ingest/embedder.py` の `_post_batch` と同じ実装方針（最大4回、1→2→4秒）。
- `check_vlm(session=None) -> None`
  `GET /api/tags` で `VLM_MODEL` がpull済みか確認する。`embedder.check_ollama()` と
  同じ役割・同じ実装方針で、取り込み開始前に一度だけ呼ぶ。
- `VlmError(Exception)` — 呼び出し元はこれを捕まえて個々の画像を諦められるようにする。
- `CAPTION_PROMPT` は日本語で2〜3文の説明を求め、ロゴ等の装飾画像には
  「装飾画像」とだけ答えるよう指示する（本文への無意味な追記を防ぐ）。
- `OLLAMA_HOST` は `embedder.py` と同じ環境変数を読む（独自の接続経路を増やさない）。
  ColabのL4に接続している場合、VLM呼び出しも自動的にそちらのプロキシ経由になる。

## 5. `pdf_parser.py` の変更

`parse_pdf(path, ocr_page=None, caption_image=None)` にパラメータを追加する。

各ページで `page.get_images(full=True)` を呼び、返る `(xref, ..., width, height, ...)`
から画像を取り出す。`MIN_IMAGE_WIDTH = 150` / `MIN_IMAGE_HEIGHT = 150`（px、仮値）
未満の画像はロゴ・アイコン等の装飾とみなして除外する。この閾値は実データでの
実測が済んでいないため、実装時に `source/` 内の実ファイルで画像サイズの分布を
確認し、必要なら調整する（`OCR_MIN_CHARS` が実測30字で決まったのと同じ方法）。

残った画像は `doc.extract_image(xref)` でバイト列を取り出し、`caption_image` が
渡されていれば呼び出し、結果をそのページのテキストへ
`"\n\n[図の説明] " + caption` として追記する。`caption_image` が `None`（既定）の
場合、この処理は一切実行されない＝現状と完全に同じ挙動になる。

既存の「テキスト30字未満ならページ全体をOCRする」パスとは独立に動く。ページ全体が
1枚の画像として埋め込まれているスキャンページでは、OCRが文字を、VLMキャプションが
図表の視覚的な意味（例:「棒グラフでA社の売上が最も高い」）を補い、役割が重複しない。

## 6. `pptx_parser.py` の変更

`parse_pptx(path, caption_image=None)` にパラメータを追加する。

`_walk()` の対象を「`has_text_frame` のシェイプ」から「`has_text_frame` または
`shape_type == MSO_SHAPE_TYPE.PICTURE` のシェイプ」に広げる。画像シェイプは
`shape.width` / `shape.height`（EMU）をインチに換算し、`MIN_PICTURE_INCHES = 1.0`
（仮値、PDF同様に実測で調整）未満なら除外する。PDFの画素サイズと異なり、PPTXでは
「スライド上に配置された大きさ」で判定できる（小さく配置された高解像度画像を
誤って採用しない）。

残った画像は `shape.image.blob` で取り出し、`caption_image` が渡されていれば呼び出し、
結果を `f"[図の説明] {caption}"` という1つのブロックとして `_blocks()` の返り値に、
他のテキストブロックと同じ `_position()` の読み順で混ぜ込む。以降の `_group()` は
変更しない（テキストブロックと同列に扱われ、既存のグルーピングロジックがそのまま働く）。

## 7. `ingest/parsers/__init__.py` の変更

```python
def parse(path: Path, caption_image=None) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    if path.suffix.lower() in (".pdf", ".pptx"):
        return parser(path, caption_image=caption_image)
    return parser(path)
```

docx/mdは今回対象外のため、`caption_image` を渡さず現状のシグネチャのまま呼ぶ。

## 8. `scripts/ingest_source.py` の変更

`--with-vlm` フラグを追加する（既存の `--force` / `--only-suffix` と同じ形）。
指定時のみ `vlm.check_vlm()` で事前確認してから `ingest_directory(..., caption_image=
vlm.caption_image)` を渡す。未指定時は `caption_image=None` のままで、コードパスは
このリリース前とまったく同じになる。

`ingest_directory()` のシグネチャにも `caption_image=None` を追加し、`parse(path,
caption_image=caption_image)` へ橋渡しする。

## 9. `ingest/models.py` / `ingest/chunker.py` の変更

`ParsedUnit` に `vlm: bool = False` を追加する。画像キャプションを1つでも含めた
ユニットは `vlm=True` にする。`chunker.py` の `RESERVED_METADATA_KEYS` に `"vlm"` を
追加し、`ocr` と同様にChunkメタデータへ複写する。

UIでの表示は今回変更しない。既存の `ocr` フラグも現状は保存されるだけで
`rag_chat_app.py` 側の表示には使われておらず、それに合わせる（将来、検索結果に
「🖼️ 画像の説明を含む」等を出したくなったときのための下地）。

## 10. データフロー

```
scripts.ingest_source --with-vlm
  → vlm.check_vlm() で事前確認（qwen2.5vl:7bがpull済みか）
  → 各PDF/PPTXについて parse(path, caption_image=vlm.caption_image)
      → 埋め込み画像をサイズでふるい落とす
      → 残った画像をbase64化して {OLLAMA_HOST}/api/chat に渡す
      → 返ってきたキャプションをユニットのテキストへ追記
  → 以降は既存のchunker → embedder → store にそのまま流れる（コード変更なし）
```

## 11. エラー処理

- 起動前: `--with-vlm` 指定時に `vlm.check_vlm()` が失敗したら取り込み全体を
  開始せず中断する（`embedder.check_ollama()` と同じ考え方）。
- 個々の画像: ネットワーク一時失敗は `embedder.py` と同じ指数バックオフで再試行。
  最終的に失敗したら `VlmError` を送出し、呼び出し側（パーサー）はその画像の
  キャプションだけを諦めて警告を標準エラーに出し、ページ/スライドの他のテキストは
  失わずに処理を続ける。1ファイル単位で処理を続ける既存方針（取り込みCLIの
  docstring参照）を画像単位にも広げる形になる。

## 12. テスト方針

- `tests/test_vlm.py`（新規）: `tests/test_embedder.py` と同じ `_FakeSession`
  パターンで、リトライ・バックオフ・最終失敗時に `VlmError` を投げることを検証する。
- `tests/test_parser_pdf.py`: `caption_image` を渡さない場合は画像処理が一切
  呼ばれないこと、閾値未満の画像は `caption_image` に渡らないこと、閾値以上の画像は
  キャプションがページ本文に追記されることを、既存の `ocr_page=_fail` と同じ
  パターン（呼ばれたら失敗させるダミー関数）で検証する。
- `tests/test_parsers_office.py`: 同様に、`caption_image` の有無・サイズ閾値・
  読み順への混ざり方（他のテキストブロックとの順序）を検証する。
- `scripts/ingest_source.py` の `--with-vlm` 配線自体は、既存の `--force` /
  `--only-suffix` と同様にCLI結合テストの対象外とする（単体テストは
  `ingest_directory()` と `parse()` の橋渡し部分でカバーする）。

## 13. 取り込み時間への影響

現状の初回取り込みは約24分（OCR 23ページが大半）。VLMキャプションは画像1枚あたり
数秒〜十数秒かかる見込みで、画像点数の多い資料では取り込み時間が大きく伸びる。
`--with-vlm` を明示指定した場合のみ有効になるため、既定の取り込み時間には影響しない。
実際の所要時間はデータでの実測が必要（実装時に記録する）。

## 14. 今回やらないこと

- DOCXの画像対応（ユーザーの要望がPDF/PPTXに限定されているため）。
- ローカルOllama側での自動モデルpull（`README.md` の「モデル: ollama pull ...」と
  同じ運用で、ユーザーが事前に `ollama pull qwen2.5vl:7b` する前提）。
- 検索結果・チャットUIでのVLMキャプション表示の作り込み（`vlm` フラグの保存まで。
  `ocr` フラグの現状の扱いに合わせる）。
- 画像サイズ閾値の自動キャリブレーション（固定の仮値を置き、実データでの
  手動調整に留める）。

## 15. 残るリスク

- **幻覚**: VLMが実際には存在しない内容を説明文に含める可能性がある。検索結果の
  出典として提示されるテキストの一部になるため、誤った説明文がそのまま回答の
  根拠になり得る。緩和策は用意しない（プロンプトで簡潔さを求める程度）。今後
  実運用で問題が出れば別途対応する。
- **しきい値の誤判定**: 150px / 1インチという仮の閾値は未実測。小さくても
  重要な図（例: 数式や記号のみの図）を取りこぼす、または大きい装飾画像を
  拾ってしまう可能性がある。
- **取り込み時間の増大**: 画像点数の多い資料では大幅に伸びる可能性があり、
  実測するまで正確な見積りができない。
