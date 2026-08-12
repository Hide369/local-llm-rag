# ローカル文書RAGチャット

PDF・PowerPoint・Word を完全ローカルでベクトルDBに取り込み、出典付きで回答するRAGチャット。
外部サービスへの送信は一切行わない。

## 必要なもの

- Python 3.13（`myvenv313`）
- Ollama（インストール直後の標準ポート `http://127.0.0.1:11434` で待ち受けていること）
- モデル: `ollama pull bge-m3` と `ollama pull llama3.1:8b`

### Ollamaの待ち受けポートについて

`ingest/embedder.py` の `DEFAULT_OLLAMA_HOST` はOllamaの標準ポート
`http://127.0.0.1:11434` に合わせてあるため、通常は何も設定せずに動く。
`ollama list` が応答すれば、そのOllamaに接続できる。

標準以外のポートで動かしている場合のみ、環境変数 `OLLAMA_HOST` で上書きする。
`http://` から書くこと（コードはこの値をそのままURLに埋め込む）。

```powershell
$env:OLLAMA_HOST="http://127.0.0.1:12000"
.\myvenv313\Scripts\python.exe -m scripts.ingest_source
```

`localhost` は使わないこと。Windowsでは先にIPv6の `::1` に解決され、
1リクエストあたり約2.1秒を浪費する（`127.0.0.1` なら約80ms）。

なお `udemy1.py`〜`udemy3.py` は教材オリジナルのコードで `http://localhost:12000` を
直接埋め込んでおり、環境変数を読まない。これらを動かす場合は12000番で待ち受ける
Ollamaインスタンスを別途用意する必要がある（例: `$env:OLLAMA_HOST="127.0.0.1:12000"; ollama serve` で
2つ目のインスタンスを起動する。モデルは共有される）。

## セットアップ

```powershell
.\myvenv313\Scripts\python.exe -m pip install pymupdf python-pptx python-docx rapidocr onnxruntime langchain-text-splitters chromadb streamlit openai requests pytest
```

## 使い方

取り込みたい資料を `source/` に置く（`.pdf` / `.pptx` / `.docx`）。

```powershell
# 初回の取り込み（実測 約13分。OCR 23ページと埋め込み279件を処理する。時間はほぼOCRが占める）
.\myvenv313\Scripts\python.exe -m scripts.ingest_source

# チャットを起動する
.\myvenv313\Scripts\streamlit.exe run rag_chat_app.py
```

2回目以降はファイルのハッシュを見て変更分だけを処理するため数秒で終わる。
UIサイドバーの「差分を取り込む」も同じ処理を呼ぶ。

## 構成

| パス | 役割 |
|---|---|
| `ingest/` | 取り込みパイプライン（UIに依存しない） |
| `scripts/ingest_source.py` | 取り込みCLI |
| `scripts/check_retrieval.py` | 関連度しきい値を決めるための距離実測 |
| `rag_chat_app.py` | Streamlit UI |
| `udemy1.py` 〜 `udemy3.py` | 教材の各段階。`local_docs` コレクションを使い続ける |

このプロジェクトのコレクション（`local_docs_v2`、bge-m3 / 1024次元）は、教材が使う
`local_docs`（nomic-embed-text / 768次元）とは別名で `chroma_db/` 内に共存している。
次元が異なるベクトルを混在させないよう、意図的に別コレクションにしている
（`ingest/store.py` 参照）。現在 `local_docs_v2` は `source/` の8ファイルから279チャンク、
`local_docs` は21チャンクを保持している（`chromadb` で `list_collections()` して実測）。

## 設計定数

主要な定数は測定に基づいて決めており、根拠は各ファイルのコメントに書いてある。
値を変えるときはコメントの実測条件を読んでから判断すること。

| 定数 | 値 | 定義場所 |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 100 | `ingest/chunker.py` |
| `MIN_CHUNK_CHARS` | 10 | `ingest/chunker.py` |
| `OCR_MIN_CHARS` | 30 | `ingest/parsers/pdf_parser.py` |
| `OCR_DPI` | 200 | `ingest/ocr.py` |
| `EMBED_BATCH_SIZE` | 8 | `ingest/embedder.py` |
| `DEFAULT_OLLAMA_HOST` | `http://127.0.0.1:11434` | `ingest/embedder.py` |
| `RELEVANCE_THRESHOLD` | 0.50 | `ingest/retrieval.py` |

## テスト

```powershell
.\myvenv313\Scripts\python.exe -m pytest            # 通常のテスト
.\myvenv313\Scripts\python.exe -m pytest -m integration  # 実機のOCRを使う低速なテスト
```

## 既知の制約

- **しきい値は「関連する質問」と「圏外の質問」しか分離できない。** `scripts/check_retrieval.py`
  の実測では、関連する質問の最大距離が0.459、圏外の質問の最小距離が0.549であり、間に
  `RELEVANCE_THRESHOLD = 0.50` を置くことで両者はきれいに分離できている。しかし
  「こんにちは」のような意味的に空な挨拶は、これとは切り分けられない（実測距離
  0.412、コーパスの重心付近に埋め込まれるため1件ヒットしてしまう）。これは構造的な
  限界であり、しきい値の調整では解決しない。代わりに `ingest/prompting.py` の
  プロンプトが、検索結果が質問に無関係なら回答に使わず「社内文書からは回答できない」
  旨を伝えるようモデルに明示的に指示することで対処している。
- **資料を入れ替えたら `scripts/check_retrieval.py` で再調整すること。** 上記の2つの
  距離はコーパスの中身に依存する。資料構成が変わったら実行して分離が保たれているか
  確認し、実測値の間に `RELEVANCE_THRESHOLD` を設定し直す。
- **画像PDFのOCR結果には認識誤りが残る。** 唯一の画像PDF
  （`Claude_Code_法人導入ガイド_スライド.pdf`）から抽出した日本語には
  「デ プT」「口一カル」のような誤認識が含まれる。ベクトル検索自体はこの程度の
  ノイズを吸収して機能するが、OCR由来のチャンクを出典として引用する際は元のテキストが
  完全に正確ではないことを踏まえること。UI上ではOCR由来の出典に「（OCR）」と
  マークして区別している。
- このPCはGPUを使えないため、OCRを連続実行すると熱により約2.5倍遅くなる

## 設計資料

- 設計書: `docs/superpowers/specs/2026-08-11-document-ingestion-design.md`
- 実装計画: `docs/superpowers/plans/2026-08-11-document-ingestion.md`
