# ローカルGitLabにミラーする

GitHub（`Hide369/local-llm-rag`）を正としたまま、手元のGitLab CEに全ブランチ・
全タグの複製を持つための手順。設計の根拠は
[設計書](superpowers/specs/2026-09-04-local-gitlab-design.md) を参照。

**GitLabは必要なときだけ起動する。** 常時起動するとOllamaとメモリを取り合うため、
`restart` ポリシーは `"no"` にしてありDocker Desktopの起動にも追随しない。

## セットアップ

### 1. WSL2のメモリ上限を設定する

`%USERPROFILE%\.wslconfig` に以下を書く（リポジトリには含まれない）。

```ini
[wsl2]
# ローカルGitLab CEの実測メモリ使用量（約3.7GB、本ファイルの「実測値」参照）に
# 2GBの余裕を足した値。残りをWindows本体・Streamlit・ローカルOllamaに残す。
memory=6GB
swap=2GB
```

3.7GB + 2GBの余裕 = 5.7GBを1GB単位で切り上げて6GBとした。設定後は
`wsl --shutdown` してDocker Desktopを起動し直す。

### 2. `.env` を用意する

```powershell
Copy-Item infra\gitlab\.env.example infra\gitlab\.env
```

作成した `infra\gitlab\.env` に以下を設定する。

- `GITLAB_VERSION`: `19.3.1`（実際に採用したGitLab CEのバージョン。`latest` は使わない）
- `GITLAB_ROOT_PASSWORD`: 8文字以上の任意の文字列（GitLabの要件。実値はここには書かない）

### 3. 起動する

```powershell
.\run_gitlab.ps1 up
```

初回はGitLab内部でreconfigure（Chefによる設定適用）とデータベースマイグレーションが
走るため時間がかかる。実際にかかった時間は下の「実測値」を参照。2回目以降は
reconfigureが走らないため大幅に短くなる（これも「実測値」参照）。

### 4. GitHubからインポートする

**「Repository by URL」インポートは使わないこと。** GitLab 19.3.1では既定で
インポート元が無効化されており、Admin Areaで有効化してURLと接続確認（Check
connection）まで成功させても、「Create project」ボタンがdisabledのまま解除されない
フロントエンドの不具合に実際に遭遇した（原因未特定・GitLab側のバグと判断）。
この経路を追いかけて時間を浪費しないこと。

代わりに、以下の**ブランクプロジェクト作成 + `sync`** が実際に機能する正式な手順。

1. `http://localhost:8929/projects/new` を開き、「Create blank project」を選ぶ。
   - Project name: `local-llm-rag`
   - Visibility: Private
   - 「Initialize repository with a README」はチェックしない（空のリポジトリにする）
2. 作成されたプロジェクトのクローンURL（例:
   `http://localhost:8929/root/local-llm-rag.git`）を使い、`gitlab` remoteを追加する。

   ```powershell
   git remote add gitlab http://localhost:8929/root/local-llm-rag.git
   ```

   `origin`（GitHub）はこの操作では一切変更しない。
3. 下記「Git認証を設定する」でHTTP認証を済ませた上で、`.\run_gitlab.ps1 sync` を
   実行する（下の「日常の運用」参照）。全ブランチ・全タグがこの1回の `sync` で
   GitLabに反映される。

### 5. Git認証を設定する

GitLabへHTTP経由でpushすると、認証情報が無い状態ではGit Credential Manager
（GCM）のGUIダイアログが毎回ポップアップする。これを避けるため、Personal Access
Token（PAT）を発行し、資格情報ストアに事前登録しておく。

1. `root` でサインインし、`http://localhost:8929/-/user_settings/personal_access_tokens`
   でPATを発行する。
   - Token name: `local-mirror-sync`
   - Scopes: `write_repository`
2. 発行されたトークンの値を、以下のコマンドで資格情報ストアに登録する
   （`<PAT>` の部分にのみ実際のトークン値を入力する。**トークンの値はこのファイルにも
   会話ログにもコミットにも一切書かないこと**）。

   ```powershell
   git credential approve
   protocol=http
   host=localhost:8929
   username=root
   password=<PAT>

   ```
   （最後に空行を入れて入力を終える）

登録後は `sync` 実行時にダイアログが出ず、資格情報ストアから自動的に認証される。
トークンを再発行した場合は、上記の `git credential approve` をもう一度実行すれば
上書きされる。

## 日常の運用

| コマンド | 動作 |
|---|---|
| `.\run_gitlab.ps1 up` | 起動し、healthyになるまで待つ |
| `.\run_gitlab.ps1 sync` | 全ブランチ・全タグを gitlab へ push する |
| `.\run_gitlab.ps1 down` | 停止する（データはvolumeに残る） |
| `.\run_gitlab.ps1 status` | 現在の状態を表示する |

`origin`（GitHub）は変更していないので、普段の `git push` はこれまでどおり
GitHubに送られる。GitLabへの反映は `sync` を明示的に実行したときだけ行われる。
**1回の `git push` で両方に送る設定にしていないのは、GitLabが停止中のとき
`git push` が毎回失敗し、GitHubへのpushまで巻き込むため。**

**`sync` は「ローカルにチェックアウトしたブランチ」ではなく「originの実態」を
ミラーする。** `git push --all` だけを使う素朴な実装は、ローカルに存在するブランチ
しか送らない。実際にTask 4でこれを試したところ、GitHub上の8ブランチ中6本
（ローカルにチェックアウトしていなかったfeature/fixブランチ）が**無言で**同期から
漏れた。そのため `sync` は内部で次の順に処理する。

1. `git fetch origin --prune` でGitHubの最新状態を取り込む
2. `origin` のリモート追跡ブランチ（`refs/remotes/origin/*`。symbolic refである
   `origin/HEAD` は除く）を、実ブランチ名で明示的に `gitlab` へpushする
3. ローカルにしかまだ存在しないブランチ（作業ブランチ等）を `git push --all gitlab`
   で送る
4. `git push --tags gitlab` でタグを送る

この設計により、GitHub上に存在するがこのマシンでは一度もチェックアウトしていない
ブランチも、確実に `gitlab` 側に反映される。

## 実測値

**実測値の欄には、前タスクで控えた実際の数値だけを記載している。目安値や
「約N分程度」といった推測は含めていない（幅がある値はその幅自体が実測結果）。**

| 項目 | 実測値 | 測定日 |
|---|---|---|
| 初回起動（reconfigure含む、コールド） | 約180〜198秒 | 2026-09-04 |
| 2回目以降の起動 | 111秒 | 2026-09-04 |
| 定常時メモリ | 約3.7GB | 2026-09-04 |
| ディスク: volume `local-gitlab_gitlab_config` | 191kB | 2026-09-05 |
| ディスク: volume `local-gitlab_gitlab_data` | 490.9MB | 2026-09-05 |
| ディスク: volume `local-gitlab_gitlab_logs` | 45.76MB | 2026-09-05 |
| ディスク: イメージ `gitlab/gitlab-ce:19.3.1-ce.0` | 3.694GB | 2026-09-05 |
| `.wslconfig` の `memory`（`swap=2GB`とセット） | 6GB | 2026-09-04 |
| `puma['worker_processes']` | 2（未調整） | 2026-09-04 |
| `sidekiq['max_concurrency']` | 5（未調整） | 2026-09-04 |

測定環境: Intel Core i5-1240P（GPUなし）、メモリ16GB。連続負荷で熱により
約2.5倍遅くなるため、他の負荷がかかっている状態ではこれより延びる。

初回起動が「約180〜198秒」と幅を持っているのは、起動完了の判定に使った
HTTPポーリングの間隔（20秒）の分解能によるもので、この幅自体が実測の限界を
表している。より正確な値が必要な場合は、volumeを消してから計測し直すこと。

### メモリの測り方（重要）

このDocker Desktop（WSL2バックエンド）環境では `docker stats` がメモリ使用量として
常に `0B / 0B` を返す既知の不具合があり、コンテナ内から `/sys/fs/cgroup/memory.current`
（cgroup v2）・`/sys/fs/cgroup/memory/memory.usage_in_bytes`（cgroup v1）のどちらを
読もうとしてもパスが存在しない。`docker stats` を実行して0が出ても、それは
「GitLabがメモリを使っていない」ことを意味しない。

実際に採用した約3.7GBという数値は、WSL2の共有VM（Docker Desktopのバックエンドを
含むすべてのディストリビューションが同一のLinuxカーネルのメモリ管理を共有している）
の `free -m` が示す `used` 値を、GitLab起動前後で差分を取って求めたものである。

```
GitLab起動前のused:   857MB
GitLab起動後（アイドル時）のused: 約4588MB
--------------------------------------
差分（GitLabの定常時フットプリント）: 約3.7GB
```

**プロセスごとのRSSを単純合算した値（実測で約6.2GB）は使わないこと。これは
誤った過大評価である。** Rubyのプリフォークモデルでは、Pumaワーカー（4プロセス）が
親プロセスからCopy-on-Writeでforkされるため、変更されていない共有ページが
各ワーカーのRSSに重複してカウントされる。合算すると実際の物理メモリ使用量より
大きく出る。差分法による約3.7GBのほうが実態に近い。

### `healthy` は「使える」ではない（重要）

コールドの初回起動では、Dockerが `healthy` を報告してから実際にサインイン画面が
HTTP 200を返すまで、実測で**約167秒**のギャップがあった。`docker-compose.yml` の
`start_period` は起動直後の失敗を無視する猶予でしかなく、healthcheckのコマンド自体が
早期に成功を返せば、reconfigureやデータベースマイグレーションが終わっていなくても
即座に `healthy` になる。

そのため `run_gitlab.ps1 up` は、コンテナが `healthy` になったことに加えて、
`http://localhost:8929/users/sign_in` が実際にHTTP 200を返すことまで確認してから
「起動しました」と表示する。**`docker ps` の `healthy` 表示だけを見てGitLabが
使える状態だと判断しないこと。**

### PumaワーカーとSidekiqの並行数を絞らなかった理由

`puma['worker_processes']`（2）と `sidekiq['max_concurrency']`（5）を削減する
チューニングは、定常時メモリが4GBを超えた場合にのみ実施する計画だった。実測の
約3.7GBはこのしきい値を下回っているため、削減は行っていない。値を絞る余地
（このしきい値の判断基準）自体は残っているので、将来メモリ使用量が増えた場合は
この2つのパラメータの削減を検討すること。

## 動作確認の記録

設計書7.1節の7項目をすべて実施し、すべて成功（PASS）した。

| # | 項目 | 結果 |
|---|---|---|
| 1 | `run_gitlab.ps1 up` で起動し、ヘルスチェックが通ること | PASS |
| 2 | `http://localhost:8929` にrootでログインできること | PASS |
| 3 | GitHubからのインポートが成功し、コミット履歴がGitHubと一致すること | PASS |
| 4 | `run_gitlab.ps1 sync` で全ブランチ・全タグがGitLabに反映されること | PASS |
| 5 | `run_gitlab.ps1 down` で停止すること | PASS |
| 6 | 再度 `up` してデータが残っていること（named volumeの永続化確認） | PASS |
| 7 | Docker Desktopを再起動してもGitLabが自動起動しないこと | PASS |

特に7番目は、Docker Desktopを完全に終了・再起動したあとに `status` を実行しても
`local-gitlab` コンテナ自体が存在しないことを確認しており、`restart: "no"` が
意図どおりに機能していることの直接的な証拠になっている。

## 既知の不安定さ

**この構成の稼働実績は長くない。正直に記録する。**

作業中、GitLabコンテナが理由不明のまま終了（exit 255）した事象が1回あった。その
時点でDocker Desktopのバックエンド自体も既に応答不能になっており、根本原因は
特定できていない（GitLab側かDocker Desktop側か、あるいはホストマシン側の事情かは
切り分けられていない）。

`.wslconfig` の `memory=6GB` という上限は、安定稼働の確認がまだ数分程度の観察しか
積み重なっていない。長時間の連続稼働でも問題が起きないことを保証するものではない。

**もしGitLabが原因不明で落ちた場合、まず疑うべきはメモリ不足である。** `.wslconfig`
の `memory` を元の `8GB` に戻し、`wsl --shutdown` してDocker Desktopを起動し直した
上で問題が再発するか確認すること。WSL2の共有VMがOOMになった場合、コンテナの
理由不明な異常終了として観測される可能性が高い。

## バックアップを取っていない理由

GitLabはバックアップ「先」であり、正はGitHubにある。volumeが壊れても
「GitHubからインポートし直す」で復旧できるため、バックアップのバックアップは
持たない。**将来GitLabを正に切り替える場合は、バックアップ設計が別途必須になる。**

## Phase 2（CI/CD）について

Runnerと `.gitlab-ci.yml` はまだ導入していない。上の実測値を踏まえて、
このハードウェアでCIまで載せられるかを判断してから着手する。
