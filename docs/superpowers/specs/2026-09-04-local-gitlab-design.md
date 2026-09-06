# ローカルGitLab（GitLab CE）の導入 設計書

作成日: 2026-09-04

## 1. 目的

GitHub（`Hide369/local-llm-rag`）で管理している本リポジトリを、ローカル環境の
GitLab CE にもミラーし、手元にもう一つの完全な複製を持つ。あわせて GitLab CI/CD を
段階的に導入し、既存の pytest をローカル Runner で回せる状態を目指す。

GitHub が**正**であり、ローカル GitLab は**従**である。この主従関係は本設計全体を
通じて動かさない。GitLab 側のデータが失われても、GitHub から再インポートすれば
復旧できる状態を維持する。

本設計は **Phase 1（GitLab CE 本体のみ）** を対象とする。Phase 2（Runner と CI/CD）は
8節に見取り図のみを示し、Phase 1 の実測結果を見てから改めて設計・着手可否を判断する。

## 2. 前提と制約

### 2.1 ハードウェア

- CPU: **Intel Core i5-1240P**（Pコア4＋Eコア8、28W）、**GPUなし**
- メモリ: 16GB（実測 15.7GB）
- Cドライブ空き: 168GB
- 連続負荷で熱により約2.5倍遅くなる（README「既知の制約」）

この CPU 特性は本設計に直接影響する。GitLab CE (Omnibus) の初回起動は
`gitlab-ctl reconfigure` が全サービスを構成するため CPU バウンドであり、
**サーマルスロットリングの影響を最も受ける工程**である。所要時間は 7.2 節で実測する。

### 2.2 ソフトウェア

- Windows 11 Home / Docker Desktop 20.10.21 / Docker Compose v2.13.0
- WSL2（Ubuntu-24.04、docker-desktop）
- Docker Desktop は現在停止中であり、常時起動していない

### 2.3 メモリ競合と Colab L4

本プロジェクトは `OLLAMA_HOST` を差し替えることで、生成・埋め込みを Google Colab の
L4 GPU に逃がせる（README「ColabのL4 GPUに接続する」）。この経路を使っている間は
ローカルで Ollama が動かないため、GitLab CE に割ける空きメモリが生まれる。

ただし README に自ら記したとおり **Colab のランタイムはアイドルや時間経過で切断される**。
ローカル Ollama に戻る時間帯は必ず残るため、「Colab を使うから常時起動してよい」とは
結論しない。**必要時のみ起動**という運用を基本とし、Colab 接続中は上げっぱなしにできる、
という位置づけにとどめる。

### 2.4 GitLab CE のライセンス上の制約

**pull mirroring（外部 → GitLab の自動取り込み）は GitLab Premium 以上の機能であり、
CE では使えない。** CE で無料に使えるのは push mirroring（GitLab → 外部）のみ。

したがって「GitHub に push すれば自動でローカルに同期される」という形は CE では
組めない。同期はローカルからの明示的な push で行う（5節）。

## 3. 検討した選択肢と却下理由

### 3.1 Forgejo / Gitea（却下）

メモリ 200〜500MB、起動数秒、**pull mirror が無料**。本用途への適合度は客観的には
GitLab CE より高い。

却下理由は、GitLab CI/CD の運用そのものを学ぶことが導入目的に含まれるため。
機能要件だけを見れば Forgejo が最適だが、目的が一致しない。

### 3.2 Colab L4 上で GitLab を動かす（却下）

却下理由は 3 つ。

1. Colab ランタイムは揮発性で、切断時にディスクごと消える。バックアップ先が消えるのは
   目的と正反対
2. GitLab は CPU・RAM・ディスク I/O 律速であり、L4 の GPU は一切使われない
3. 常時稼働の受け口にするには ngrok を張り続ける必要があり、README の注意書き
   （URL と API キーを共有しないこと）と同じ懸念がリポジトリ全体に及ぶ

### 3.3 GitLab CE + Runner を一括導入（却下）

Phase 1 と Phase 2 を同時に立ち上げる案。却下理由は、GitLab CE がこのハードウェアで
実用に耐えるかが未知数であり、本体と Runner を同時に入れると問題の切り分けが
難しくなるため。Phase 2 は compose へのサービス追加が中心で差分が小さく、後回しにする
コストが低いことも判断材料とした。

## 4. 構成

### 4.1 ファイル配置

| ファイル | 役割 |
|---|---|
| `infra/gitlab/docker-compose.yml` | GitLab CE 単体の定義（新規） |
| `infra/gitlab/.env.example` | root パスワード等のテンプレート（新規） |
| `run_gitlab.ps1` | 起動 / 停止 / 同期のヘルパー（新規・ルート配置） |
| `docs/gitlab-local.md` | セットアップと運用手順（新規） |
| `README.md` | 上記へのリンクを1行追加 |
| `.gitignore` | コメント文のみ更新（後述） |

`run_gitlab.ps1` をルートに置くのは既存の `run_streamlit.ps1` と揃えるため。
`scripts/` は `__init__.py` を持ち pytest から import される Python パッケージなので、
PowerShell スクリプトは置かない。

`.gitignore` に**新しい除外パターンを足す必要はない**。既存の `.env` パターンは
スラッシュを含まないため gitignore の仕様上あらゆる階層に一致し、`infra/gitlab/.env` も
自動的に除外される。変更するのは、現在 Colab 用途だけを説明しているコメント文を
GitLab にも言及する形に書き直す一点のみで、除外規則そのものは変えない。

### 4.2 docker-compose の設計

サービスは `gitlab` の1つのみ。永続化は named volume 3つ（`gitlab_config` /
`gitlab_logs` / `gitlab_data`）で、Omnibus が永続化を要求する `/etc/gitlab`・
`/var/log/gitlab`・`/var/opt/gitlab` にそれぞれ対応させる。

イメージは `gitlab/gitlab-ce:<バージョン>-ce.0` の形で**バージョンを固定する**。
具体的なバージョン番号は実装時に Docker Hub で最新の安定版を確認して決定する
（本設計書で記憶を頼りに書くと、存在しない tag や古い版を指す恐れがあるため確定させない）。

`shm_size` は 256m を指定する（PostgreSQL が既定の 64m で警告を出すため）。

### 4.3 メモリ抑制

デフォルトの GitLab CE は 4〜6GB を消費する。`GITLAB_OMNIBUS_CONFIG` で以下を絞る。

- `prometheus_monitoring['enable'] = false` — 自己監視スタック（Prometheus、各種
  exporter、Grafana 相当）を丸ごと停止する。単一利用者のローカル環境では監視対象が
  自分しかおらず、削減効果が最も大きい
- `puma['worker_processes'] = 2` — 既定は CPU コア数に依存して増える。同時利用者が
  1人であれば 2 で足りる
- `sidekiq['max_concurrency']` を既定より下げる — 非同期ジョブの並列数。CI を回さない
  Phase 1 ではジョブ自体が少ない

**削減後の数値は見込みを書かない。** 導入後に実測し、7.2 節の手順で
`docs/gitlab-local.md` に記録する。既存の設計書（reranker 等）が実測値を記録する
書き方をしているため、それに揃える。

### 4.4 ポート

| ポート | 用途 | 備考 |
|---|---|---|
| 8929 | HTTP（Web UI・git over http） | `external_url 'http://localhost:8929'` |
| 2224 | SSH（git over ssh） | `gitlab_rails['gitlab_shell_ssh_port'] = 2224` |

80/443 は Windows 上で他プロセスと衝突しやすいため避ける。既存プロセスの
Streamlit（8501）、Ollama（11434）とは衝突しない。

### 4.5 restart ポリシー

**`restart: "no"` とする。** これは意図的な判断である。

`unless-stopped` や `always` にすると Docker Desktop の起動に追随して GitLab も
自動的に立ち上がり、2.3 節で定めた「必要時のみ起動」という運用と正面から矛盾する。
起動は `run_gitlab.ps1` を明示的に叩いたときだけに限定する。

### 4.6 WSL2 のメモリ上限

Docker Desktop の WSL2 バックエンドは既定でホスト RAM の約 50% まで確保しうる。
`%USERPROFILE%\.wslconfig` にメモリ上限を明示し、GitLab が Ollama や Streamlit を
圧迫しないようにする。

これはリポジトリ外のユーザー設定ファイルであるためコミットしない。設定手順を
`docs/gitlab-local.md` に記載する。

## 5. GitHub との同期運用

### 5.1 remote 設計

`origin`（GitHub）は**変更しない**。`gitlab` という別 remote を追加する。

```
git remote add gitlab http://localhost:8929/<user>/local-llm-rag.git
git push gitlab master
```

`git remote set-url --add --push` で「1回の `git push` で GitHub と GitLab の両方へ
送る」構成も可能だが、**採用しない**。GitLab は必要時のみ起動する前提であり、停止中の
`git push` が毎回接続エラーで失敗して GitHub への push まで巻き込むためである。
GitHub が主・GitLab が従という位置づけとも、明示的な remote のほうが素直に一致する。

### 5.2 同期コマンド

`run_gitlab.ps1` に以下のサブコマンドを持たせる。

| サブコマンド | 動作 |
|---|---|
| `up` | `docker compose up -d` → ヘルスチェックが通るまで待機 → URL を表示 |
| `down` | `docker compose down`（volume は残す） |
| `sync` | `git push --all gitlab` と `git push --tags gitlab` |
| `status` | コンテナの状態とヘルスチェック結果を表示 |

`sync` を `--all` / `--tags` にするのは、全ブランチ・全タグが一度に揃い、手で
ブランチ名を打つより取りこぼしが起きないため。現在 origin には master 以外に
feature / fix ブランチが6本あり、これらも複製対象とする。

### 5.3 初回の取り込み

GitLab の Web UI から「Import project → Repository by URL」に GitHub の URL を
指定する。本リポジトリは公開リポジトリのため認証情報は不要。

インポート後に 5.1 の remote を追加し、以降は 5.2 の `sync` で更新する。

> **【実装時の追記 / 2026-09-05】この 5.3 の手順は実装中に破棄された。**
> GitLab 19.3.1 では「Repository by URL」インポートが機能せず（Admin Area で
> インポート元を有効化し接続確認まで成功させても「Create project」ボタンが
> disabled のまま解除されないフロントエンドの不具合に遭遇）、代わりに
> 「ブランクプロジェクトを作成してから `sync` で全ブランチ・全タグを push する」
> 手順を採用した。実際に機能する手順は
> [`docs/gitlab-local.md`](../../gitlab-local.md) の「4. GitHubからインポートする」
> を参照すること。上の本文は当初の設計判断の記録としてそのまま残している。
> 6.3 節が「5.3 の手順で再インポートすれば復旧できる」としている箇所も、
> 同様にこの新しい手順に読み替える。

## 6. 秘密情報とデータ永続化

### 6.1 秘密情報

root の初期パスワードは `infra/gitlab/.env` の `GITLAB_ROOT_PASSWORD` から渡す。
`.env` は gitignore 済みでコミットされない。`.env.example` にはプレースホルダのみを
置き、実値は書かない。

### 6.2 データ永続化

named volume を使う。Windows のパスへ bind mount すると GitLab はパーミッションと
I/O 性能の両面で問題を起こしやすいため、bind mount は採用しない。

### 6.3 GitLab 自体のバックアップ（スコープ外）

**Phase 1 のスコープ外とする。** これは意図的な割り切りである。

GitLab はあくまでバックアップ「先」であり、正は GitHub にある。volume が壊れても
5.3 の手順で再インポートすれば復旧できるため、バックアップのバックアップを持つ
必要がない。この判断理由を `docs/gitlab-local.md` にも記載し、将来 GitLab を主に
切り替える場合はバックアップ設計が必須になることを明記する。

## 7. 検証方法

インフラ構成であり pytest では検証できない。`docs/gitlab-local.md` に手順を記載し、
**実際に一通り実行して結果を確認するまでを完了条件とする**。

### 7.1 動作確認シナリオ

1. `run_gitlab.ps1 up` で起動し、ヘルスチェックが通ること
2. `http://localhost:8929` に root でログインできること
3. GitHub からのインポートが成功し、コミット履歴が GitHub と一致すること
4. `run_gitlab.ps1 sync` で全ブランチ・全タグが GitLab に反映されること
5. `run_gitlab.ps1 down` で停止すること
6. **再度 `up` してデータが残っていること**（named volume の永続化確認）
7. Docker Desktop を再起動しても GitLab が自動起動しないこと（4.5 の確認）

### 7.2 実測して記録する項目

`docs/gitlab-local.md` に数値として記録する。

| 項目 | 測定方法 |
|---|---|
| 初回起動（reconfigure 含む）の所要時間 | `up` からヘルスチェック通過まで |
| 2回目以降の起動時間 | 同上 |
| 定常時のメモリ使用量 | `docker stats` |
| ディスク使用量 | `docker system df -v` |

2.1 節のとおり本機はサーマルスロットリングの影響が大きいため、初回起動時間は
一般的な目安より延びる可能性がある。**目安値を先に書かず、実測値のみを記録する。**

## 8. Phase 2 の見取り図（本設計のスコープ外）

同じ compose に `gitlab-runner` サービスを追加し、docker executor で既存の pytest を
`.gitlab-ci.yml` から実行する。executor は DinD ではなく Docker socket マウントを
予定する（軽量なため）。

**Phase 1 の 7.2 の実測結果を見てから、改めて設計・着手可否を判断する。** 起動時間や
メモリ消費が実用に耐えないと判明した場合は、3.1 の Forgejo への方針転換も含めて
再検討する。

## 9. スコープ外（YAGNI）

以下は本設計に含めない。

- GitLab 自体のバックアップ（6.3 の理由による）
- HTTPS / TLS 証明書（localhost からのアクセスのみのため）
- GitLab Container Registry、Pages、Wiki などの追加機能
- GitHub の Issue / PR 履歴の GitLab への移行（GitHub が正であり、二重管理を避ける）
- LAN 内の他端末からのアクセス（現時点で要件がない）

## 10. 未確定事項

実装時に確定させる項目。

- `gitlab/gitlab-ce` の固定バージョン（4.2）
- `puma['worker_processes']` と `sidekiq['max_concurrency']` の最終値（4.3）
  — 起動を確認しながら調整する
- `.wslconfig` のメモリ上限値（4.6）— GitLab の実測値が出てから決める
