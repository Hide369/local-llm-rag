# GitHub からのドキュメント取り込み 設計書

**日付:** 2026-09-13
**目的:** C#・Go・Markdown・Mermaid の記法を、公式リポジトリの生 Markdown から
取り込む。`llms-full.txt` を公開していない対象へ届かせる。
**前提:** [2026-09-12-latest-docs-ingestion-design.md](2026-09-12-latest-docs-ingestion-design.md)

## 1. 背景

前回の設計で `docs_store.sqlite3` に6件のライブラリが入り、Streamlit の記法には
答えられるようになった。しかし取り込めた言語は実質 Python だけである。

コーパス全体のコードフェンスのタグを数えた実測（2026-09-13、別名は統合済み）:

| 言語 | 件数 | | 言語 | 件数 |
|---|---|---|---|---|
| Python | 2,658 | | Mermaid | 97 |
| シェル | 1,833 | | Java | 61 |
| TypeScript | 502 | | JavaScript | 56 |
| JSON | 435 | | Markdown | 27 |
| YAML | 152 | | Kotlin | 12 |
| TOML | 114 | | Go | 7 |

Go が7件、C# は0件である。しかもこれらは**ライブラリの資料であって言語の資料では
ない**。Java の61件は Spring の例であり、Java の文法を説明したものではない。

依頼は「Java・Go・C# を増強したい。GitHub から取り込めないか」であった。
前回の設計書2節は GitHub API からの取得を却下している。本設計はその判断を、
**言語そのものの文法**という範囲に限って見直す。

## 2. 決定事項

依頼者との確認で以下が確定した。

| 論点 | 決定 | 却下した案 |
|---|---|---|
| 取得の対象 | 言語自体の文法 | ライブラリ・フレームワークの資料 |
| Java | 今回は見送る | 含める |
| 取得の仕組み | `docs_sources.toml` に `kind` を足して `fetch_docs.py` を拡張 | 別スクリプト＋別設定、スパースチェックアウト |
| Go の言語仕様 | Markdown だけ取る（仕様は HTML なので対象外） | HTML 変換を足す、Go 自体を見送る |
| C# の `:::code` | 参照先の `.cs` を解決して本文へ差し込む | 参照行のまま取り込む、C# を見送る |
| 書き出しの粒度 | 1ページ1ファイル | 1ソース1ファイルへ結合 |

Java を見送ったのは、**公式の Markdown ドキュメントが GitHub に存在しない**ため
である（実測 2026-09-13: `dev-java/dev.java`、`java-tutorials/java-tutorials` は
いずれも 404）。Spring は実在するが AsciiDoc であり
（`spring-projects/spring-framework` 471ファイル/3.07MB、
`spring-projects/spring-boot` 218ファイル/1.77MB）、パーサーの追加が要るうえ、
それは言語の文法ではなくフレームワークの資料である。

## 3. 全体構成

前回の2段構成を保つ。取得の入口が1つ増えるだけで、**その後の経路は1行も変えない**。

```
[docs_sources.toml]  kind = "llms"（既定）と kind = "github"
        │
        ▼  scripts/fetch_docs.py（人が起動したときだけ走る）
   kind="llms"   → 従来どおり llms-full.txt を1本 GET
   kind="github" → Trees API で木を1回引く → raw で各ページを取得
        │           → :::code を解決（有効にしたソースのみ）
        ▼  docs_source/csharp/language-reference/builtin-types/record.md
        │           （1ページ1ファイル。従来の docs_source/streamlit.md と併存）
        ▼  scripts/ingest_source.py --source-dir docs_source --db docs_store.sqlite3
        ▼  docs_store.sqlite3
```

`scripts/ingest_source.py` は既に再帰する。`_target_files` がサブフォルダを走査し、
`_source_key` が `source_dir` からの相対パスをそのまま資料の識別子にする。
**取り込み側の変更は無い。**

## 4. 実測に基づく設計判断

本節の数値はすべて 2026-09-13 に実測した。推測には「推定」と書く。

### 4.1 `llms.txt` は Go・C#・Java・Rust に存在しない

| 言語 | `llms.txt` | 結果 |
|---|---|---|
| Go | `go.dev/llms.txt` | 404 |
| C# | `learn.microsoft.com/.../llms.txt` | 404 |
| Java | `dev.java/llms.txt` | 404 |
| Rust | `doc.rust-lang.org/llms.txt` | 404 |
| Kotlin | `kotlinlang.org/llms.txt` | 200（49KB、フェンス**0個**＝目次） |

Kotlin だけ 200 を返すが中身は目次であり、前回の設計書4.1節が記録した
`llms.txt` の性質そのままである。**GitHub 以外に経路が無い。**

### 4.2 Trees API は1リポジトリ1回で足り、認証も要らない

`GET api.github.com/repos/{repo}/git/trees/{ref}?recursive=1` を未認証で叩いた結果:

| リポジトリ | HTTP | エントリ | 応答 | `truncated` |
|---|---|---|---|---|
| dotnet/docs | 200 | 28,268 | 9,265,802 B | false |
| github/docs | 200 | 14,945 | 4,751,220 B | false |
| golang/website | 200 | 3,644 | 1,089,707 B | false |
| mermaid-js/mermaid | 200 | 3,518 | 1,153,176 B | false |

必要な呼び出しは**リポジトリにつき1回、計4回**。未認証枠は60回/時なので
**トークンは要らない**。本文は `raw.githubusercontent.com` から取る。こちらは CDN で
API のレート制限の対象外である。

`golang/website` の既定ブランチは `master` であり `main` ではない（`main` は 404）。
`mermaid-js/mermaid` は `develop` である。`ref` は設定に明示させる。

### 4.3 対象にするサブパスと規模

| ソース | リポジトリ | ref | サブパス | `.md` | バイト |
|---|---|---|---|---|---|
| csharp | dotnet/docs | main | `docs/csharp/` の10サブパス | 581 | 4,063,315 |
| go | golang/website | master | `_content/doc`、`_content/ref` | 96 | 1,826,518 |
| mermaid | mermaid-js/mermaid | develop | `packages/mermaid/src/docs` | 65 | 698,968 |
| markdown | github/docs | main | `content/get-started/writing-on-github` | 27 | 99,326 |
| | | | **合計** | **769** | **6,688,127** |

除外したものと理由:

- **`docs/csharp/misc`（409ファイル）** — コンパイラのエラー番号ごとのページ
  （`cs0003.md`、`cs0004.md`…）。文法の説明ではなく、量だけが多い。
- **`_content/blog`（339ファイル）、`_content/solutions`（42ファイル）** — 読み物と
  事例であり文法ではない。
- **CommonMark 仕様（`commonmark/commonmark-spec` の `spec.txt`、206,108 B）** —
  仕様書の例は独自の区切り文字で書かれておりコードフェンスではない。現在の
  チャンカーは扱えない。実務で書くのは GitHub Flavored Markdown なので
  `github/docs` で足りると判断した。

### 4.4 Go の言語仕様は HTML であって Markdown ではない

`golang/website` の `_content/doc` は大半が `.html` と `.go` であり、`_content/ref`
には `index.md` と `mod.md` しかない。**Go の言語仕様（`spec.html`）と Effective Go
は HTML である。**

Markdown で取れる96ファイルの中身は、各版のリリースノート（`go1.1.md`〜）、FAQ、
modules リファレンス、security、database ガイド、tutorial である。

HTML 変換は足さない。理由は2つある。

1. 直前の PR（#37）で「HTML を掴んだら `NotDocumentationError` で止める」歯止めを
   入れたばかりである。Go のためだけに例外を開けると、その歯止めが弱くなる。
2. 新しい依存と新しい壊れ方が増える。

**代わりに期待値を下げる。** Go は文法の網羅ではなく「各版で何が増えたか」に
答える資料として入れる。リリースノートは新構文を説明しているので、目的
（最新の文法で答える）に対しては外れていない。この限界は
`docs/コーディング対応ライブラリ.md` に明記する。

### 4.5 C# のコード例は本文に入っていない

MS Learn 形式のドキュメントは、コード例を `:::code` で**外部ファイルへ参照**する。

```
:::code language="csharp" source="snippets/shared/Program.cs" id="Snippet1":::
```

Markdown には参照行しか無い。各サブディレクトリで標本を取って数えた実測
（標本は最大25件）:

| サブパス | 全件 | 埋込ブロック | 外部参照 | 外部の割合 | フェンス0件 |
|---|---|---|---|---|---|
| language-reference | 328 | 47 | 50 | 52% | 7/25 |
| programming-guide | 82 | 29 | 71 | 71% | 14/25 |
| fundamentals | 68 | 18 | 159 | 90% | 18/25 |
| advanced-topics | 33 | 40 | 134 | 77% | 13/25 |
| linq | 25 | 15 | 203 | 93% | 19/25 |
| whats-new | 14 | 40 | 31 | 44% | 4/14 |
| tour-of-csharp | 13 | 29 | 14 | 33% | 3/13 |
| asynchronous-programming | 9 | 33 | 42 | 56% | 1/9 |
| tutorials | 7 | 35 | 37 | 51% | 0/7 |
| how-to | 2 | 1 | 0 | 0% | 1/2 |

**逃げ場が無い。** どのサブパスも3割〜9割が外部参照であり、「ここだけ取れば埋込が
多い」という区画は存在しない。このまま取り込むと、検索は当たるのにコードが書けない
状態になる。これは `llms.txt` を掴んだときとまったく同じ壊れ方である
（前回の設計書4.1節）。

参照先の実体は `docs/csharp/**/snippets/` に **686ファイル / 1,479,786バイト**
あり、すべて同じリポジトリの木の中にある。解決すれば C# は実用になる。

### 4.6 他の3件に同じ問題は無い

標本40件（Markdown は全27件）での実測:

| ソース | 文字数 | 埋込フェンス | 外部参照 | Liquid | フェンス0件 |
|---|---|---|---|---|---|
| mermaid | 419,020 | 1,307 | 0 | 0 | 5/40 |
| go | 637,198 | 196 | 0 | 0 | 22/40 |
| markdown | 99,290 | 106 | 0 | 215 | 19/27 |
| csharp | 281,451 | 80 | 85 | 0 | 25/40 |

**Mermaid が最も密度が高い。** 40ファイルで1,307のフェンスがあり、フェンス0件は
5件しかない。今回いちばん効く見込みが立つのはここである。

`github/docs` には Liquid のテンプレート記法（`{% data reusables… %}`）が215箇所
ある。取り込む前に除去する（5.3節）。

### 4.7 規模の推定

取り込み量は Markdown 6.69MB に、差し込むコード 1.48MB を足して **約8.2MB**。

既存コーパスの実測比（13.5MB → 29,844チャンク）から**推定**すると
**約18,000チャンク・埋め込み約24分**（NVIDIA L4、ngrok 経由）。これは推定であり
実測ではない。実測は取り込み後に `docs/コーディング対応ライブラリ.md` へ記録する。

## 5. 作るもの

### 5.1 `docs_sources.toml` に `kind` を足す

```toml
[[source]]
name = "csharp"
kind = "github"
repo = "dotnet/docs"
ref  = "main"
paths = [
  "docs/csharp/language-reference",
  "docs/csharp/programming-guide",
  "docs/csharp/fundamentals",
  "docs/csharp/tour-of-csharp",
  "docs/csharp/whats-new",
  "docs/csharp/advanced-topics",
  "docs/csharp/linq",
  "docs/csharp/asynchronous-programming",
  "docs/csharp/tutorials",
  "docs/csharp/how-to",
]
resolve_code_refs = true
version = "0.0.0"
```

`kind` の既定は `"llms"`。**既存の6件は1行も変えない。**
`resolve_code_refs` の既定は `false`。

`kind = "llms"` に `repo` や `paths` を書いた設定、`kind = "github"` に `url` を
書いた設定は、読み込み時に `ValueError` で弾く。黙って無視すると、設定を直した
つもりの人が直っていないことに気付けない。

### 5.2 `scripts/fetch_docs.py` に GitHub 取得を足す

`DocSource` を分ける。`LlmsSource(name, url, version)` と
`GitHubSource(name, repo, ref, paths, version, resolve_code_refs)`。
`load_sources()` は `kind` を見てどちらかを返す。

`run()` はソースごとに分岐する。既存の `FetchReport`、SHA-256 による差分検知、
「1件が失敗しても残りを続ける」方針はそのまま使う。

GitHub 取得の流れ:

1. `GET api.github.com/repos/{repo}/git/trees/{ref}?recursive=1`
2. `truncated` が真なら `TreeTruncatedError` を投げ、**そのソース全体を失敗**にする。
   部分的な木で取り込むと一部のページだけが静かに欠ける。これは今回いちばん
   避けたい壊れ方であり、実測で4リポジトリとも偽だったからといって黙って続けない。
3. `paths` のいずれかに前方一致する `.md` の blob を選ぶ
4. 各 blob を `raw.githubusercontent.com/{repo}/{ref}/{path}` から取る。並列4。
5. **1ページの取得失敗はそのページを飛ばして続ける**。件数を `FetchReport` に載せる。
   土台（木）は取れているので、残りのページは使えるためである。

木の取得は1回で、`GitHubSource` の処理中だけ結果を持つ。永続化はしない
（`ingest/retrieval.py` の `build_index` と同じ理由で、DBとファイルの二重管理を
作らない）。

### 5.3 書き出しは1ページ1ファイル

`docs_source/{name}/{リポジトリ内の相対パス}` に書く。例:

```
docs_source/csharp/language-reference/builtin-types/record.md
docs_source/mermaid/syntax/flowchart.md
```

元ファイルの YAML フロントマターは捨て、自前のものに置き換える。

```markdown
---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534...
source_path: docs/csharp/language-reference/builtin-types/record.md
title: Records
version: 0.0.0
fetched_at: 2026-09-13
---
```

こうする理由は3つある。

- **出典が実際のページ名になる。** `_source_key` は相対パスをそのまま識別子に
  するので、画面の「参考にした情報」に `csharp/language-reference/…/record.md`
  と出る。結合すると全部が `csharp.md` になる。
- **差分がページ単位で効く。** 1ページ直っても再埋め込みは1ページ分で済む。
- **`parse_md` の作りに合う。** `parse_md` は最初の `# ` だけを `title` として拾い、
  全セクションの先頭に付ける。結合すると4MBのファイル全体に1つの title しか
  付かず、意味を失う。

`commit` は Trees API の応答が返すルートの SHA を入れる。`llms-full.txt` では
取れない再現性が、ここでは取れる。

`{% … %}` の Liquid 記法はここで除去する。

書き出し先が `docs_source/` の外を指さないことは、既存の `write_if_changed` と
同じ検査で守る（`..` を弾く）。`name` だけでなく、**GitHub から来るパスにも同じ
検査を通す**。木の内容は設定ファイルと違ってバージョン管理下に無い入力である。

### 5.4 `:::code` の解決（新規）

```python
def resolve_code_references(text, source_path, blob_paths, fetch) -> tuple[str, int]:
    """`:::code` を参照先のコードに置き換える。置換した件数も返す。"""
```

扱う形式は3つ:

| 書式 | 意味 |
|---|---|
| `source="x.cs"` のみ | ファイル全体 |
| `source="x.cs" id="Snippet1"` | `.cs` 側の `#region Snippet1` 〜 `#endregion` |
| `source="x.cs" range="12-24"` | 行範囲（1始まり、両端を含む） |

`source` は `.md` のあるディレクトリからの相対パスとして解決する。解決した本文は
` ```csharp ` のフェンスに入れて差し込む（`language=` の値をタグにする）。

**`AGENTS.md` の約束との関係。** 現行は「設定に書かれたURLしか取りに行かない。
ページ内のリンクは辿らない。クローラーにはしない」と書いてある。`:::code` を
追うのは字義どおりリンクを辿る行為なので、歯止めを2つ置いて限定する。

1. **`resolve_code_refs = true` を書いたソースでだけ走る。** 既定は無効。
2. **解決先は同じリポジトリ・同じ `ref` の木にある blob に限る。** 呼び出し側から
   渡した `blob_paths`（2節で取った木）に無いパスは取りに行かず、警告を出して
   参照行をそのまま残す。**外部 URL は絶対に辿らない。**

解決できなかった参照は `FetchReport` に件数を載せる。黙って落とすと、コードの
入っていないページが混ざったことに気付けない。

### 5.5 `AGENTS.md` の更新

「外部ドキュメントの参照」の3本目（`scripts/fetch_docs.py`）の記述を書き換える。
追加する宛先は `api.github.com` と `raw.githubusercontent.com`。送るのは要求だけで
社内資料の内容も検索語も含まないこと、`:::code` の解決は同一リポジトリの木の中に
閉じており外部リンクは辿らないこと、人が明示的に起動したときだけ走ることを明記する。

### 5.6 触らないもの

- `scripts/ingest_source.py` — 既にサブフォルダを再帰し、相対パスを識別子にする
- `ingest/chunker.py` — `--keep-code-blocks` がそのまま効く
- `ingest/retrieval.py`、`ingest/query_translation.py`、`rag_chat_app.py`
- `vector_store.sqlite3`（社内資料）

## 6. 移植性

**取り込みは GitHub API もサイトへのログインも要らない。**

- ログインは元から不要である。`fetch_docs.py` も本設計の GitHub 取得も認証しない。
  Trees API は未認証で 200 を返す（4.2節）。
- **取り込み側は外部サイトに触らない。** `scripts/ingest_source.py` が import
  するのは `embedder` `navigation` `store` `vlm` `chunker` `parsers` だけで、
  `ingest/` 配下で外へ出る宛先は `{OLLAMA_HOST}`（`/api/embed`、`/api/chat`）
  だけである。GitHub への依存は取得側に閉じている。
- 既定は `DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"`。移植先のローカル
  Ollama に `bge-m3` があれば、**外部通信ゼロで取り込める**。

移植先へ持っていくものは2通りある。

| 運ぶもの | サイズ | 移植先で要るもの |
|---|---|---|
| `docs_source/` | 現13.5MB ＋ 今回分 約8.2MB | Ollama。取り込みを1回走らせる |
| `docs_store.sqlite3` | 現129MB | 取り込み不要 |

**`docs_source/` は `.gitignore` 済みである。** clone しただけでは付いてこない
ので、GitHub API が使えない環境へ持ち込むならファイルとして別に運ぶ。

`:::code` の解決は取得時に走ってコードを本文へ差し込むため、`docs_source/` の
時点で完結したファイルになる。移植先で解決し直す必要はない。

なお検索側には外部通信が1本残る。`ingest/reranker.py` の `check_reranker()` は
`hf_hub_download` を呼ぶので、モデルが手元の HF キャッシュに無ければ
huggingface.co へ出る（`AGENTS.md` に既記載）。完全なオフライン環境では事前に
取得しておくこと。これは取り込みではなく検索の話であり、本設計の変更とは無関係
である。

## 7. テスト

**ネットワークに触るテストは1つも書かない。** すべて偽のセッションで閉じる。

| 対象 | 確かめること |
|---|---|
| `load_sources` | `kind` 省略で `LlmsSource`、`"github"` で `GitHubSource` |
| `load_sources` | `kind="llms"` に `repo`、`kind="github"` に `url` は `ValueError` |
| 木の選別 | `paths` に前方一致する `.md` だけを選ぶ。`.cs` や他のサブパスは選ばない |
| 木の選別 | `paths` の値が別のパスの接頭辞になっていても誤って拾わない |
| `truncated` | 真ならそのソースが失敗になり、他のソースの取得は続く |
| 1ページ失敗 | 1件が落ちても残りのページが書かれ、件数が報告される |
| `resolve_code_references` | `source` のみ／`id=`／`range=` の3形式 |
| `resolve_code_references` | `blob_paths` に無い参照は取りに行かず、参照行が残り、件数が報告される |
| `resolve_code_references` | `resolve_code_refs = false` のソースでは走らない |
| Liquid 除去 | `{% … %}` が消え、本文中の `{` は残る |
| フロントマター | 元の YAML が捨てられ、`commit` と `source_path` が入る |
| 書き出し先 | `..` を含むパスは `ValueError`（`docs_source/` の外へ書かせない） |
| 差分検知 | 本文が同じなら書き換えない（`fetched_at` の差で誤検知しない） |

## 8. 受け入れ条件

1. `python -m scripts.fetch_docs` で `docs_source/` に csharp・go・mermaid・
   markdown の4ソースが書かれ、既存6件は「変更なし」でスキップされる
2. C# のページで `:::code` の参照行が残っていない（解決できなかったものは
   報告されている）
3. `python -m scripts.ingest_source --source-dir docs_source --db docs_store.sqlite3
   --keep-code-blocks` が完走し、追加されたチャンク数が報告される
4. 出典が `csharp/language-reference/…` のようにページ単位で出る
5. `vector_store.sqlite3`（社内資料）のバイト数が変わっていない
6. 既存のテストが1つも壊れていない
7. `docs/コーディング対応ライブラリ.md` に実測値が記録されている

## 9. 範囲外

- Java（2節）。AsciiDoc のパーサーは作らない
- Go の言語仕様と Effective Go（4.4節）。HTML 変換は足さない
- CommonMark / GFM の仕様書（4.3節）
- `docs/csharp/misc` のコンパイラエラーページ（4.3節）
- 定期実行。人が起動したときだけ走る方針は変えない
- GitHub のトークン対応。未認証で足りることを実測した（4.2節）
