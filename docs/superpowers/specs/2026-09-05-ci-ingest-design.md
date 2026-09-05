# push を契機とした資料の自動ベクトル化（GitLab CI）設計書

作成日: 2026-09-05

## 1. 目的

ローカル GitLab の `root/source-archive` リポジトリに資料が push された時点で、
GitLab CI/CD が自動的に取り込み処理を走らせ、`local_llm/chroma_db` のベクトルデータを
最新の資料と一致させる。

現状は資料を差し替えたあと `python scripts/ingest_source.py` を手で実行しており、
実行を忘れるとチャットの回答が古い資料に基づいたまま黙って返る。DB の中身が
リポジトリの実態からいつ乖離したのか、事後には判別できない。**「push した資料が
検索対象になっている」ことを人間の記憶に依存させない**のが本設計の目的である。

本設計は `2026-09-04-local-gitlab-design.md`（以下「Phase 1 設計書」）の続きにあたるが、
その 8 節に書かれた Phase 2 の見取り図とは対象も executor も異なる。差異と理由は
2.4 節に記す。

## 2. 前提と制約

### 2.1 対象リポジトリと既存のクローン配置

資料は GitLab の `root/source-archive` で管理されている。**このリポジトリは GitLab が
正**であり、GitHub 側に対応するリポジトリは存在しない。この点で `local-llm-rag`
本体（GitHub が正、GitLab は従）とは主従関係が逆である。Phase 1 設計書 5.1 節の
remote 設計は本リポジトリには適用されない。

現在、同じリポジトリのクローンがホスト上に 2 つ存在する。

| パス | remote 名 | 役割 |
|---|---|---|
| `source_archive/source-archive` | `origin` | 資料を編集する作業用クローン |
| `local_llm/source` | `gitlab` | `ingest_source.py` の既定の入力ディレクトリ |

`local_llm/source` は `.gitignore` により `local-llm-rag` 本体の追跡対象から
外れている（「取り込み対象の原本（バイナリが大きく、内容も配布対象ではない）」）。

### 2.2 既存 ingest パイプラインの性質

本設計が依存する既存実装の性質を明示する。**これらは本設計で変更しない。**

- **入力は 1 ディレクトリ**。`ingest_source.py --source-dir` で切り替えられる。
- **差分判定はファイル内容の SHA-256（先頭 16 桁）**。同じ内容のファイルは再処理
  されない。ハッシュはチャンクのメタデータに持たせており、DB が唯一の情報源に
  なっている（`ingest/store.py` 冒頭のコメント）。
- **資料の識別子は入力ディレクトリからの相対パス**（`_source_key`、区切りは
  スラッシュに正規化）。
- **入力ディレクトリから消えた資料は DB からも消える**（`delete_orphans`）。ただし
  `--only-suffix` 指定時は行わない。
- **1 ファイル処理するごとに DB へ書き込む**。途中で失敗しても成功分は残り、
  再実行時にハッシュ判定でスキップされる。
- 全量処理は **38 ファイル・460 チャンクで約 24 分**（`ingest_source.py`
  docstring の実測値。OCR 23 ページを含む）。
- 書き込み先は `local_llm/chroma_db`、コレクション名は `local_docs_v2`。

識別子が入力ディレクトリからの相対パスである以上、`local_llm/source` を入力とした
既存の DB と、リポジトリのチェックアウトを入力とした DB は、**キー体系が完全に一致
する**（両者は同じリポジトリの内容だから）。したがって入力ディレクトリを切り替えても
全量再取り込みは発生しない。この一致は偶然ではなく、本設計が 3.4 節の案を却下して
リポジトリを直接入力にできる根拠そのものである。

### 2.3 メモリと Ollama の競合

Phase 1 設計書 2.3 節のとおり、本機は 16GB で GitLab（実測約 3.7GB）と Ollama が
メモリを取り合う。そのため **GitLab は必要なときだけ起動する**運用になっており、
`restart` ポリシーは `"no"`、Docker Desktop の起動にも追随しない。

CI を導入すると常駐プロセスが 1 つ増える。この方針に反しないよう、Runner も
GitLab と同じく「必要なときだけ起動する」（4.7 節）。

Embedding は `.env` の `OLLAMA_HOST` が指す Ollama で行う。これは Colab の L4 GPU を
指している場合があり、**そのセッションが切れていれば CI は Embedding できない**。

### 2.4 Phase 1 設計書 8 節（Phase 2 の見取り図）との差異

Phase 1 設計書 8 節は Phase 2 を「同じ compose に `gitlab-runner` サービスを追加し、
**docker executor** で既存の **pytest** を実行する」と想定していた。本設計はこれを
次の 2 点で置き換える。

1. **対象が pytest ではなく資料の ingest である。** pytest の CI 実行は「手元で
   `pytest` を叩けば同じ結果が即座に得られる」ため、自動化の価値が push 契機の
   ingest より小さい。ingest は忘れると DB が黙って古くなるのに対し、テストは
   忘れても壊れたことがすぐ分かる。
2. **executor が docker ではなく shell である。** 理由は 3.3 節に記す。

Phase 1 設計書 8 節は「Phase 1 の実測結果を見てから改めて設計・着手可否を判断する」と
していた。実測（同 7.2、`docs/gitlab-local.md`）でメモリ約 3.7GB・2 回目以降の起動
111 秒と判明し、Forgejo への方針転換は不要と判断できたため、本設計で着手する。

**pytest の CI 実行は本設計のスコープ外**（9 節）。

## 3. 検討した選択肢と却下理由

### 3.1 Webhook + 常駐受信サーバー（却下）

GitLab の Webhook をホスト上の小さな HTTP サーバー（Flask 等）で受け、pull と ingest を
実行する案。

却下理由は、**GitLab CI が既に提供している機能を自前で再実装することになる**ため。
実行履歴・ログの保存、失敗時の再実行、同時実行の抑制、認証はいずれも CI 側に
既にある。受信サーバーを書けばこれらを一つずつ自作することになり、しかも
Phase 1 設計書 8 節で導入を予定していた Runner は結局別に必要になる。

副次的に、Docker 内の GitLab からホストの受信サーバーへ到達させるために
`host.docker.internal` を使う必要があり、Phase 1 設計書 4.4 節が
`127.0.0.1` バインドで担保している「localhost からしかアクセスできない」という
前提の検証範囲が広がる。

### 3.2 手動コマンド / タスクスケジューラによる定期ポーリング（却下）

push 後に同期スクリプトを 1 つ叩く、あるいは定期実行する案。

手動実行は 1 節に書いた「実行を忘れる」問題をそのまま残すため、目的を満たさない。

定期ポーリングは、GitLab が停止している時間帯（本機では大半）に空振りし続ける。
また、資料を push してから DB に反映されるまでの遅延が実行間隔に依存し、**チャットで
古い回答が返ってきたときに「まだ反映前」なのか「取り込みに失敗した」のかを
利用者が区別できない**。

### 3.3 Docker executor（却下）

Phase 1 設計書 8 節が想定していた案。却下理由は 3 つある。

1. **書き込み先がホストのファイルである。** `chroma_db` はコンテナから
   バインドマウントする必要がある。Docker Desktop（WSL2 バックエンド）経由の
   Windows ホストパスのマウントは、SQLite のファイルロックの挙動が
   ネイティブファイルシステムと異なる。Chroma の実体は SQLite + HNSW ファイルであり、
   ここで問題が出た場合の切り分けは容易でない。
2. **依存の再インストールが重い。** `requirements.txt` には `onnxruntime`、
   `rapidocr`、`pymupdf` が含まれ、さらにリランカーと OCR のモデルは
   `huggingface_hub` 経由で実行時にダウンロードされる。ジョブごとにこれを
   繰り返せば、差分 1 ファイルの取り込みに数分の準備時間がかかる。イメージを
   自前でビルドして固めることは可能だが、そのイメージの保守がまるごと新しい仕事に
   なる。
3. **ホストには既に動作実績のある環境がある。** `myvenv313` は現に手元の ingest が
   通っている環境そのものである。

再現性という docker executor の利点は、**このジョブが常に同一の 1 台でしか
実行されない**以上、得るものが小さい。

トレードオフとして、shell executor は push された `.gitlab-ci.yml` をホスト上で
無制限に実行する（7.2 節）。この前提が崩れる場合は docker executor へ切り替える。

### 3.4 `local_llm/source` を pull してから ingest（却下）

ジョブが `local_llm/source` を `gitlab/main` に同期してから、既定の入力ディレクトリで
ingest する案。手元の資料ディレクトリも常に最新になる利点がある。

却下理由は、**CI が開発者の作業ツリーを書き換えることになる**ため。同期には
`git reset --hard` 相当が必要で、`local_llm/source` に未コミットの変更があれば
それを消す。しかも実行するのは人間ではなく push を契機とした無人ジョブであり、
**消えたことに気づく機会がない**。

2.2 節のとおり Runner のチェックアウトを直接入力にしても DB のキー体系は変わらない
ため、この危険を負う理由がない。

なお本案を却下した結果、`local_llm/source` は CI の経路から外れ、手動 ingest の
入力としてのみ残る（4.8 節）。

## 4. 構成

### 4.1 データフロー

```
[任意のクローンで資料を編集] --git push--> [GitLab root/source-archive]
                                                    |
                                          パイプライン生成
                                                    v
                                  [gitlab-runner (shell) / Windows ホスト]
                                                    |
                          $CI_PROJECT_DIR にチェックアウト済みの資料を入力
                                                    v
              [local_llm/scripts/ci_ingest.ps1 → ingest_source.py --source-dir]
                                                    |
                            .env の OLLAMA_HOST が指す Ollama で Embedding
                                                    v
                                     [local_llm/chroma_db] を更新
```

**GitLab のリポジトリを唯一の入力とする。** Runner のチェックアウトは push された
コミットの内容そのものなので、「DB に入っているのは push された資料である」という
関係が構成上保証される。

### 4.2 ファイル配置

`source-archive` リポジトリ:

| パス | 新規/変更 | 内容 |
|---|---|---|
| `.gitlab-ci.yml` | 新規 | `main` への push でホスト側の入口スクリプトを呼ぶ |

`local-llm-rag` リポジトリ:

| パス | 新規/変更 | 内容 |
|---|---|---|
| `scripts/ci_ingest.ps1` | 新規 | CI から呼ばれる入口。ガード → venv → ingest |
| `run_gitlab.ps1` | 変更 | `up`/`down`/`status` に Runner を連動 |
| `infra/runner/config.toml.example` | 新規 | Runner 設定の雛形（実ファイルは追跡しない） |
| `docs/gitlab-ci-ingest.md` | 新規 | 登録手順・運用・実測値 |

`infra/runner/config.toml` は登録トークンを含むため `.gitignore` に追加する
（6.1 節）。

### 4.3 `.gitlab-ci.yml` の設計

```yaml
ingest:
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - powershell -File "$env:LOCAL_LLM_DIR\scripts\ci_ingest.ps1" -SourceDir "$env:CI_PROJECT_DIR"
```

**`C:\Users\...` のような絶対パスをリポジトリに書かない。** local_llm の場所は
Runner の `config.toml` の `environment` で `LOCAL_LLM_DIR` として渡す（4.6 節）。
資料リポジトリがホストのディレクトリ構成を知らずに済み、配置を変えても
`.gitlab-ci.yml` を触らなくてよい。資料リポジトリは資料だけを持つべきで、
取り込み側の実装の詳細を持つべきではない。

ジョブを `main` に限定するのは、資料の検討途中のブランチで DB を書き換えないため。
`chroma_db` は 1 つしかなく、ブランチごとに分けられない。

**`script` の中では CI 変数を `$CI_PROJECT_DIR` ではなく `$env:CI_PROJECT_DIR` と
書く。** `script` の各行を展開するのは GitLab ではなく実行シェルであり、
PowerShell で `$CI_PROJECT_DIR` と書いても未定義の変数として空になる。一方
`rules` の `if` は GitLab 自身が評価するため、そちらは `$CI_COMMIT_BRANCH` と書く。
**同じファイルの中で 2 つの記法が混在するのは誤りではない**ので、揃えようとしないこと。

### 4.4 `ci_ingest.ps1` の設計

処理順は次のとおり。**重い処理の前に、失敗する条件をすべて確認しておく**という
方針で並べている。ingest は全量なら 24 分かかるため、20 分走ってから
「Streamlit が起動していました」と言われても遅い。

1. `-SourceDir` の存在確認
2. **`-SourceDir` が資料リポジトリのチェックアウトであることの確認**（4.4.1 節）
3. **Streamlit 稼働ガード**（5 節）
4. venv（`myvenv313`）の Python の存在確認
5. `ingest_source.py --source-dir <SourceDir>` を実行
6. 終了コードをそのまま返す

`ingest_source.py` は自身の冒頭で `load_dotenv()` と `embedder.check_ollama()` を
行うため、Ollama の疎通確認と `.env` の読み込みは本スクリプトでは行わない。
**同じ確認を 2 か所に書くと、片方だけが更新されて食い違う。**

`--with-vlm` は指定しない。VLM による画像説明は「取り込みが大幅に遅くなる」と
既存のヘルプに明記されており、無人実行するジョブに載せる処理ではない。必要な
ときは手動 CLI で実行する。

#### 4.4.1 入力ディレクトリの検証（DB 全消しの防止）

`ingest_source.py` は入力ディレクトリに存在しない資料を DB から削除する
（2.2 節の `delete_orphans`）。**これは入力がリポジトリ全体であることを前提とした
挙動である。** 誤って小さなディレクトリを `-SourceDir` に渡すと、そこに無い資料が
すべて孤児と判定され、`chroma_db` の中身がほぼ全部消える。復旧は全量 24 分の
再取り込みになる。

CI の正常経路では `$CI_PROJECT_DIR` が常にリポジトリ全体を指すためこの事故は
起きない。**危険なのは人間が手で叩くとき**で、本設計は 8.1 節で
`ci_ingest.ps1` を手動実行する動作確認を要求している以上、この経路を無防備に
残せない。

そこで `-SourceDir` が資料リポジトリのチェックアウトであることを、Embedding を
始める前に確認する。

```powershell
$remoteUrl = git -C $SourceDir remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or $remoteUrl -notlike "*source-archive*") { <失敗> }
```

- **remote が無い（`.git` が無い）ディレクトリは拒否する。** テンポラリに作った
  作業用ディレクトリは必ずここで止まる。
- Runner のチェックアウトには `.git` が残る（`GIT_STRATEGY` の既定は `fetch`）ため、
  CI の正常経路はこの検証を通る。
- **remote 名が `origin` 以外の場合がある。** `local_llm/source` の remote 名は
  `gitlab` である（2.1 節）。手動実行でそのディレクトリを渡す経路も塞がないため、
  検証は `origin` に限定せず、**いずれかの remote が `source-archive` を指していれば
  通す**実装にする（`git -C $SourceDir remote -v` の全行を見る）。

この検証は URL に `source-archive` が含まれるかしか見ない。厳密な同一性検証では
ないが、**防ぎたいのは悪意ではなく手滑りである**。同名の別リポジトリを用意して
まで誤らせる状況は想定しない。

### 4.5 venv の扱い

`myvenv313\Scripts\Activate.ps1` は呼ばず、`myvenv313\Scripts\python.exe` を
直接実行する。有効化スクリプトは実行ポリシーの影響を受け、Runner のサービス
コンテキストでは対話シェルと異なる挙動になりうる。**インタプリタを直接指定すれば
有効化そのものが不要**であり、失敗する余地が 1 つ減る。

### 4.6 Runner の登録と `config.toml`

```toml
concurrent = 1

[[runners]]
  name = "local-ingest"
  url = "http://localhost:8929"
  token = "（登録時に発行される。このファイルは追跡しない）"
  executor = "shell"
  shell = "powershell"
  environment = ["LOCAL_LLM_DIR=C:\\path\\to\\local_llm"]
```

- **`concurrent = 1`。** ingest は `chroma_db` に書き込む。同時に 2 つ走れば
  同じ SQLite と HNSW ファイルを 2 プロセスが書くことになり、5 節で防ごうと
  している事象を CI 自身が起こす。連続で push された場合は直列に実行される。
- **`shell = "powershell"`。** 新しい gitlab-runner は Windows の既定シェルを
  `pwsh`（PowerShell Core）にしており、本機に入っているのは Windows PowerShell 5.1
  である。既定のままだと `pwsh` が見つからずジョブが起動しない。明示する。
- `url` は `http://localhost:8929`。Runner はホスト上で動くため、Phase 1 設計書
  4.4 節の `127.0.0.1` バインドの内側から接続できる。

Runner のバージョンは、GitLab 本体（19.3.1）と同様に**固定する**。`latest` を
使わない理由は Phase 1 設計書と同じ。具体的な値は 10 節（未確定事項）。

### 4.7 `run_gitlab.ps1` との連動

2.3 節の方針に従い、Runner も常駐させない。既存のコマンドに次を追加する。

| コマンド | 追加する動作 |
|---|---|
| `up` | GitLab がサインイン画面を返せる状態になった**あと**に Runner を起動する |
| `down` | GitLab を停止する**前**に Runner を停止する |
| `status` | Runner の稼働状態も併せて表示する |

**順序に意味がある。** GitLab が応答する前に Runner を起動すると、Runner は
接続できない GitLab をポーリングし続けてログにエラーを書く。停止時に Runner を
先に止めるのは、ジョブ実行中に GitLab を落とすとジョブが中途半端な状態で
打ち切られるため。

Runner が停止している間に push された場合、パイプラインは GitLab 側に `pending` の
まま残り、次に `up` した時点で拾われる。**これは意図した挙動であり、
取りこぼしではない。**

### 4.8 `local_llm/source` の位置づけ

CI の経路から外れるため、内容は自動では更新されなくなる。手動 ingest（VLM 付き
実行など）の入力としては残すが、**CI が正であり、`local_llm/source` は放っておくと
古くなる**ことをドキュメントに明記する。

削除しないのは、`--with-vlm` を付けた手動実行の経路が現に必要だからである。

## 5. 排他制御（Streamlit 稼働ガード）

`rag_chat_app.py` は `@st.cache_resource` で `PersistentClient` をプロセス内に保持し、
BM25 インデックスも起動時に一度だけ全チャンクから構築する（`store.all_documents`）。
このため、**アプリの稼働中に別プロセスが `chroma_db` へ書き込むと 2 つの問題が
起きる。**

1. Chroma の実体は SQLite と HNSW ファイルであり、後者はプロセス内メモリに
   読み込まれている。外部プロセスによる変更と整合しない。
2. 仮に破損しなくても、更新はアプリを再起動するまで反映されない。BM25 インデックスも
   古いままになる。

したがって `ci_ingest.ps1` は、**Embedding を 1 つも実行する前に** Streamlit の
待ち受けを検知し、稼働中なら明示的なメッセージを出して `exit 1` する。

```powershell
$portSpec = if ($env:STREAMLIT_PORTS) { $env:STREAMLIT_PORTS } else { "8501,8503" }
$ports = $portSpec -split "," | ForEach-Object { [int]$_.Trim() }
$listening = Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue
```

待ち受けが 1 つも無いときの `Get-NetTCPConnection` はエラーを投げるため
`-ErrorAction SilentlyContinue` が必要である（`$listening` が空になるのが正常系）。

**監視ポートの既定を 8501 だけにしてはいけない。** 過去の作業ログに 8503 での
起動実績がある（`.superpowers/sdd/2026-08-12-markdown-ingestion/streamlit-8503.log`）。
既定を 1 つに絞ると、別ポートで起動しているアプリを素通りさせる。`STREAMLIT_PORTS`
で上書きできるようにする。

**ロックファイルによる待機は採らない。** チャットアプリは長時間立ち上げっぱなしに
なるのが通常の使い方であり、待たせればジョブがタイムアウトまでブロックする。
待った末に失敗するより、即座に理由を示して失敗するほうが復旧が早い。

この検知は「Streamlit かどうか」ではなく「そのポートが待ち受け中か」しか見ない。
無関係なプロセスが同じポートを使っていれば誤検知するが、**誤検知の代償（ジョブを
再実行する）は見逃しの代償（DB の破損）より小さい**ため、この非対称性を受け入れる。

## 6. 秘密情報とセキュリティ

### 6.1 秘密情報

| 情報 | 置き場所 | 追跡 |
|---|---|---|
| `OLLAMA_HOST` / `OLLAMA_API_KEY` | `local_llm/.env` | 追跡しない（既存） |
| Runner の登録トークン | `infra/runner/config.toml` | **追跡しない（本設計で `.gitignore` に追加）** |

GitLab CI/CD Variables は使わない。Embedding 先の情報は既に `.env` にあり、
ジョブはホスト上でそれを読む。**同じ値を 2 か所に置けば必ず食い違う。**

### 6.2 shell executor のリスク（明示）

shell executor は、push された `.gitlab-ci.yml` の内容を**ホスト上でそのまま実行
する**。リポジトリに push できる者は、このマシン上で任意のコマンドを実行できる。

現状は単一ユーザーの localhost 環境（Phase 1 設計書 4.4 節により `127.0.0.1` に
のみバインド）であり、この権限は既に持っている権限と変わらないため許容する。

**この前提が崩れる場合 —— 他者にこのリポジトリの push 権限を与える、または
GitLab を LAN に公開する場合 —— は、docker executor への切り替えが必須である。**
Phase 1 設計書 4.4 節が「bind を広げる前に TLS を先に導入すること」としているのと
同じ性質の条件であり、両方を同時に満たす必要がある。

## 7. エラーハンドリング

| 事象 | 振る舞い | 復旧 |
|---|---|---|
| `-SourceDir` が資料リポジトリでない | 検証で即 `exit 1`（4.4.1 節） | 正しいディレクトリを渡す |
| Streamlit 稼働中 | ガードで即 `exit 1`（5 節） | アプリを停止し GitLab UI から再実行 |
| Ollama 未疎通 | `check_ollama()` が処理前に失敗（既存） | Colab セッションを復帰させ再実行 |
| venv が見つからない | `ci_ingest.ps1` が即失敗 | 環境を復旧して再実行 |
| 一部ファイルの解析失敗 | 当該ファイルのみ記録して続行、最後に `exit 1`（既存） | 再実行で成功分はハッシュスキップされ、失敗分だけやり直る |
| Runner 停止中に push | パイプラインは `pending` で残る | `run_gitlab.ps1 up` で拾われる（4.7 節） |
| GitLab 停止中に push | push 自体ができない | `up` してから push |

**再実行が常に安全である**ことが、この表全体の前提になっている。差分判定が
ファイル内容のハッシュであり（2.2 節）、書き込みがファイル単位であるため、
失敗したジョブをそのまま再実行すれば成功済みの資料は再処理されない。したがって
本設計では自動リトライを入れない。

ジョブのタイムアウトは GitLab の既定（1 時間）を使う。全量 24 分・VLM なしなら
収まる。

## 8. 検証方法

### 8.1 動作確認シナリオ

PowerShell のテスト基盤は本プロジェクトに無く、本設計のために導入もしない
（9 節）。`docs/gitlab-local.md` と同じく、**実施した確認とその結果を表で記録
する**方式を取る。ingest 本体は既存の pytest（`tests/test_ingest_source.py`）が
カバーしており、`--source-dir` は既存機能のため新規のテストは書かない。

| # | 項目 |
|---|---|
| 1 | `run_gitlab.ps1 up` で GitLab に続いて Runner が起動すること |
| 2 | `main` への push でパイプラインが自動生成され、成功すること |
| 3 | 資料 1 件だけを変更した push で、その 1 件だけが取り込まれること（他がスキップされること） |
| 4 | 資料を削除した push で、DB から該当チャンクが消えること（孤児削除） |
| 5 | Streamlit 稼働中の push でジョブが失敗し、理由がログから分かること |
| 6 | Ollama 停止中の push で、Embedding 開始前に失敗すること |
| 7 | Runner 停止中の push が `pending` で残り、`up` 後に実行されること |
| 8 | `run_gitlab.ps1 down` で Runner が先に停止すること |
| 9 | 資料リポジトリでないディレクトリを `-SourceDir` に渡すと、DB を変更せずに失敗すること（4.4.1） |

3 と 4 は、本設計が「入力ディレクトリを切り替えても既存 DB と整合する」と
主張している 2.2 節の検証にあたる。**もし 3 で全ファイルが再取り込みされたら、
その前提が誤っている**ことになるので、チャンク総数と所要時間を記録する。

### 8.2 実測して記録する項目

Phase 1 設計書 7.2 節と同じく、目安値は書かず実測値のみを `docs/gitlab-ci-ingest.md`
に残す。

| 項目 | 測り方 |
|---|---|
| Runner 常駐時の追加メモリ | WSL2 ではなくホストのプロセス。タスクマネージャの実測 |
| 差分 1 ファイルのジョブ所要時間 | GitLab のジョブ画面の表示 |
| `up` に Runner 起動が追加する時間 | `run_gitlab.ps1 up` の出力 |

## 9. スコープ外（YAGNI）

- **pytest の CI 実行**（2.4 節）。手元で即座に実行できるため、自動化の価値が低い。
- **VLM 付き取り込みの CI 実行**（4.4 節）。無人実行に載せる処理ではない。
- **PowerShell のテスト基盤（Pester 等）の導入。** スクリプト 1 本のために
  テストフレームワークを追加しない。
- **マージリクエストやブランチでのパイプライン。** `chroma_db` は 1 つしかなく、
  ブランチごとに分離できない（4.3 節）。
- **ジョブ失敗の通知（メール等）。** GitLab の UI で確認する。
- **`local_llm/source` の自動同期**（3.4 節で却下）。
- **`local-llm-rag` 本体リポジトリへの CI 導入。** 本設計は `source-archive` のみを
  対象とする。

## 10. 未確定事項

実装時に確定させる。

- **gitlab-runner の固定バージョン**（4.6）。GitLab 19.3.1 と組み合わせて動作する
  ことを確認したうえで固定する。
- **Runner のインストール先と実行方式**（4.6、4.7）。Windows サービスとして登録した
  うえで `run_gitlab.ps1` から起動・停止するのか、サービス登録せずプロセスとして
  起動するのか。サービス登録すると既定で自動起動になり、2.3 節の方針と衝突する
  ため、自動起動を無効にできるかを確認して決める。
- **Runner のビルドディレクトリのパス長**（4.6）。既定の
  `builds\<token>\0\root\source-archive\...` に日本語のサブディレクトリが重なる。
  Windows のパス長上限に触れる場合は `core.longpaths` の設定かビルドディレクトリの
  変更で対処する。実際にチェックアウトして確認する。
