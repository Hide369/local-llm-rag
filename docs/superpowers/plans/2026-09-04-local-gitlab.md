# ローカルGitLab CE導入（Phase 1）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHubを正としたまま、必要なときだけ起動するGitLab CEをローカルに立て、全ブランチ・全タグのミラーを持つ。

**Architecture:** `infra/gitlab/docker-compose.yml` がGitLab CEコンテナ1つとnamed volume 3つを定義し、`run_gitlab.ps1` が起動・停止・同期の入口を一本化する。`origin`（GitHub）は変更せず、`gitlab` という別remoteへ明示的にpushする。アプリケーションコード（`ingest/`・`rag_chat_app.py`・`scripts/`・`tests/`）には一切触れない。

**Tech Stack:** Docker Desktop 20.10.21 / Docker Compose v2.13.0 / GitLab CE（Omnibus、バージョンはTask 1で確定）/ Windows PowerShell 5.1

**Spec:** [docs/superpowers/specs/2026-09-04-local-gitlab-design.md](../specs/2026-09-04-local-gitlab-design.md)

## Global Constraints

- **アプリケーションコードを一切変更しない。** 触れてよいのは `infra/`（新規）、`run_gitlab.ps1`（新規）、`docs/`、`README.md`、`.gitignore` のみ（spec 4.1節）
- **`origin` remote を変更しない。** GitHubが正であり、GitLabは従（spec 1節・5.1節）
- **`restart: "no"` を必ず指定する。** `unless-stopped` / `always` は「必要時のみ起動」と矛盾するため禁止（spec 4.5節）
- ポートは **HTTP 8929 / SSH 2224** 固定。80・443・8501（Streamlit）・11434（Ollama）は使わない（spec 4.4節）
- 永続化は **named volume**。Windowsパスへのbind mountは禁止（spec 6.2節）
- 秘密情報は `infra/gitlab/.env` に置く。`.env.example` には実値を書かない（spec 6.1節）
- **GitLab自体のバックアップは実装しない**（spec 6.3節・9節のYAGNI）
- **HTTPS/TLS・Container Registry・Pages・Wiki・Issue/PR移行・LAN公開は実装しない**（spec 9節）
- **Runner と `.gitlab-ci.yml` はPhase 2。この計画では作らない**（spec 8節）
- **見込みの数値をドキュメントに書かない。** 起動時間・メモリ・ディスクは実測値のみ記録する（spec 4.3節・7.2節）
- スクリプト内のコメントは日本語で「なぜ」を書く（`run_streamlit.ps1` の流儀）
- コミットメッセージは英語、コンベンショナルコミット形式
- PowerShell 5.1のため `&&` / `||` / 三項演算子は使えない。`;` と `if ($?)` を使う

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `infra/gitlab/docker-compose.yml` | 新規 | GitLab CEコンテナとvolumeの定義。ポート・メモリ抑制設定・healthcheckを持つ |
| `infra/gitlab/.env.example` | 新規 | イメージバージョン、root初期パスワード、Composeプロジェクト名のテンプレート |
| `infra/gitlab/.env` | 新規・非追跡 | 上記の実値。gitignore済みでコミットされない |
| `run_gitlab.ps1` | 新規 | `up` / `down` / `status` / `sync` の入口。healthyになるまでの待機も担う |
| `docs/gitlab-local.md` | 新規 | セットアップ手順、運用手順、実測値の記録、設計判断の理由 |
| `README.md` | 変更 | 「ローカルGitLabにミラーする」節の追加、構成表への追記、設計資料へのリンク追加 |
| `.gitignore` | 変更 | `.env` のコメント文のみ更新（除外規則は変えない） |
| `%USERPROFILE%\.wslconfig` | 変更・リポジトリ外 | WSL2のメモリ上限。コミットしない。手順は `docs/gitlab-local.md` に記載 |

**責務の分離:** `docker-compose.yml` は「何を動かすか」だけを持ち、待機やremote操作などの手続きは持たない。`run_gitlab.ps1` は「どう操作するか」だけを持ち、ポート番号やイメージ名を再定義しない（表示用のURLのみ持つ）。

## テスト方針

インフラ構成のためpytestでは検証できない。各タスクは「先に確認コマンドを実行して失敗を見る → 実装する → 同じコマンドで成功を見る」という順序を守る。**既存のpytestスイートには一切手を触れない。**

---

### Task 1: compose定義と .env.example

**Files:**
- Create: `infra/gitlab/docker-compose.yml`
- Create: `infra/gitlab/.env.example`
- Create: `infra/gitlab/.env`（非追跡。コミットしない）

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces: コンテナ名 `local-gitlab`、Composeプロジェクト名 `local-gitlab`、volume `local-gitlab_gitlab_config` / `local-gitlab_gitlab_logs` / `local-gitlab_gitlab_data`、HTTP `http://localhost:8929`、SSHポート `2224`。Task 3の `run_gitlab.ps1` がこのコンテナ名とcomposeファイルパスを参照する

- [ ] **Step 1: Docker Desktopを起動する**

Docker Desktopは現在停止している。**Step 2の失敗理由が「composeファイルが無い」ことだと確実に分かるよう、先にデーモンを起動しておく**（デーモンが落ちたまま実行すると、接続エラーなのかファイル欠如なのか区別できない）。

```powershell
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
```

起動完了を確認する:

```powershell
docker version --format '{{.Server.Version}}'
```

Expected: サーバーのバージョン（例 `20.10.21`）が表示される。エラーになる場合はDocker Desktopの起動を待つ。

- [ ] **Step 2: 確認コマンドを先に実行して失敗を見る**

```powershell
docker compose -f infra\gitlab\docker-compose.yml config
```

Expected: FAIL（`no such file or directory` 相当。composeファイルがまだ無いため）

- [ ] **Step 3: 固定するGitLab CEのバージョンを決める**

spec 4.2節のとおり、記憶ではなくDocker Hubの実際のtag一覧から決める。

```powershell
$resp = curl.exe -s "https://registry.hub.docker.com/v2/repositories/gitlab/gitlab-ce/tags/?page_size=100&ordering=last_updated"
($resp | ConvertFrom-Json).results | Where-Object { $_.name -match '^\d+\.\d+\.\d+-ce\.0$' } | Select-Object -First 5 -ExpandProperty name
```

**バージョン番号が最も大きいものを採用する。`last_updated` 順の先頭ではない。** GitLabは直近3つのマイナーバージョンに同時にパッチを出すため、更新日時で並べると `19.1.7` `19.2.5` `19.3.1` のように**古いマイナーが先頭に来る**（2026-08-26のリリースは実際にこの並びだった）。上のコマンドは更新日時順で取得しているので、返ってきた一覧からセマンティックバージョンとして最大のものを選ぶこと。

以降この計画では採用したtagを `<VERSION>-ce.0` と表記する。**`latest` は使わない**（依存はロックするという方針のため）。

- [ ] **Step 4: `.env.example` を作る**

`infra/gitlab/.env.example` を以下の内容で作成する。実値は書かない。

```
# ローカルGitLab CE の設定。このファイルを .env にコピーして実値を書く。
# .env はリポジトリルートの .gitignore で除外済みのためコミットされない。

# 使用するGitLab CEのイメージバージョン（例: 17.11.7）。
# latest ではなく必ず具体的なバージョンを固定する。
GITLAB_VERSION=

# rootユーザーの初期パスワード。GitLabの要件により8文字以上。
# 初回起動時にのみ適用され、以降の変更はWeb UIから行う。
GITLAB_ROOT_PASSWORD=

# Composeのプロジェクト名。volume名の接頭辞になるため変更しないこと。
COMPOSE_PROJECT_NAME=local-gitlab
```

- [ ] **Step 5: `.env` を作って実値を入れる**

```powershell
Copy-Item infra\gitlab\.env.example infra\gitlab\.env
```

エディタで `infra/gitlab/.env` を開き、`GITLAB_VERSION` にStep 3で決めたバージョン（`-ce.0` を除いた `17.11.7` の形）、`GITLAB_ROOT_PASSWORD` に8文字以上のパスワードを設定する。

- [ ] **Step 6: `docker-compose.yml` を作る**

`infra/gitlab/docker-compose.yml` を以下の内容で作成する。

```yaml
# ローカルGitLab CE。GitHubを正とするミラー先であり、必要なときだけ起動する。
# 設計の根拠は docs/superpowers/specs/2026-09-04-local-gitlab-design.md を参照。

services:
  gitlab:
    image: gitlab/gitlab-ce:${GITLAB_VERSION}-ce.0
    container_name: local-gitlab
    # external_url のホスト名と揃えないと、GitLabが生成するクローンURLがずれる。
    hostname: localhost
    # 「必要なときだけ起動する」運用のため、Docker Desktopの起動に追随させない。
    # unless-stopped にするとPC起動のたびにGitLabが立ち上がり、Ollamaと
    # メモリを取り合ってしまう。
    restart: "no"
    # 同梱PostgreSQLが既定の64mでは警告を出すため広げる。
    shm_size: '256m'
    environment:
      GITLAB_ROOT_PASSWORD: ${GITLAB_ROOT_PASSWORD}
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://localhost:8929'
        gitlab_rails['gitlab_shell_ssh_port'] = 2224

        # --- ここからメモリ抑制（16GBのPCでOllamaと共存させるため） ---
        # 自己監視スタックを丸ごと止める。利用者が1人の環境では監視対象が
        # 自分しかおらず、削減効果が最も大きい。
        prometheus_monitoring['enable'] = false
        # 既定はCPUコア数に応じて増えるが、同時利用者が1人なら2で足りる。
        puma['worker_processes'] = 2
        # Phase 1ではCIを回さないため非同期ジョブ自体が少ない。
        sidekiq['max_concurrency'] = 5
    ports:
      - "8929:8929"
      - "2224:22"
    volumes:
      - gitlab_config:/etc/gitlab
      - gitlab_logs:/var/log/gitlab
      - gitlab_data:/var/opt/gitlab
    healthcheck:
      test: ["CMD", "/opt/gitlab/bin/gitlab-healthcheck", "--fail", "--max-time", "10"]
      interval: 30s
      timeout: 15s
      retries: 60
      # 初回はreconfigureが走るうえ、このPCはサーマルスロットリングで
      # 大きく遅くなる（README「既知の制約」）。既定の猶予では足りない。
      start_period: 600s

# Windowsパスへのbind mountはパーミッションとI/O性能の両面で問題が出るため
# named volumeを使う。
volumes:
  gitlab_config:
  gitlab_logs:
  gitlab_data:
```

- [ ] **Step 7: 確認コマンドが通ることを見る**

```powershell
docker compose -f infra\gitlab\docker-compose.yml config
```

Expected: PASS。展開後のYAMLが表示され、`image:` にStep 3で決めたバージョンが埋まっていること、`restart: "no"` があること、ポートが `8929` と `2224` であることを目視で確認する。

- [ ] **Step 8: イメージを取得し、healthcheckの定義が実在することを確認する**

イメージは約3GBあるため時間がかかる。

```powershell
docker compose -f infra\gitlab\docker-compose.yml pull
```

続けて、Step 6で書いたhealthcheckのコマンドがイメージ側の定義と一致するか確認する。

```powershell
docker inspect --format '{{json .Config.Healthcheck}}' "gitlab/gitlab-ce:<VERSION>-ce.0"
```

Expected: `/opt/gitlab/bin/gitlab-healthcheck` を含むtestが表示される。**もしパスが異なっていた場合は、表示された実際のコマンドに合わせてStep 6の `test:` を書き換える**（記憶ではなく実物に合わせる）。

- [ ] **Step 9: コミット**

`.env` が追跡されないことを確認してからコミットする。

```powershell
git status --short infra/
```

Expected: `infra/gitlab/.env` が現れないこと（`.gitignore` の `.env` パターンが全階層に一致するため）。もし現れたら先に原因を解消する。

```powershell
git add infra/gitlab/docker-compose.yml infra/gitlab/.env.example
git commit -m "feat: define an on-demand local GitLab CE container"
```

---

### Task 2: WSL2のメモリ上限を設定する

**Files:**
- Modify: `%USERPROFILE%\.wslconfig`（リポジトリ外。コミットしない）

**Interfaces:**
- Consumes: なし
- Produces: WSL2ユーティリティVMのメモリ上限。Task 5で実測値に基づき締め直す

**このタスクに必要な背景:** Windows 11のWSL2は既定でホストRAMの約50%を上限とする。このPCは15.7GBなので既定は約7.8GBであり、8GBを明示してもほぼ同じ値になる。**それでも明示する理由は2つある。** 第一に、既定値はRAM容量に依存して変わるため予測できない。第二に、初回起動のreconfigureはメモリのピークが未測定であり、ここで絞りすぎるとOOMで失敗して原因の切り分けが難しくなる。**ピークを測る前は絞らず、Task 5で実測値に基づいて締める。**

- [ ] **Step 1: 現在の上限を確認する**

```powershell
wsl -d Ubuntu-24.04 -- free -m
```

Expected: `Mem:` 行の `total` が約7800MB（既定の50%）。この値を控える。

- [ ] **Step 2: `.wslconfig` を作成・編集する**

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

既存の内容がある場合は `[wsl2]` セクションに追記する。無い場合は以下を書く。

```ini
[wsl2]
# ローカルGitLab CEをDocker Desktop上で動かすための上限。
# 既定はRAMの50%でホスト依存になるため、明示して予測可能にする。
# 初回起動のreconfigureはメモリのピークが未測定なので、ここでは絞らない。
memory=8GB
swap=2GB
```

**`processors` は設定しない。** GitLabのreconfigureはCPUバウンドであり、このPC（i5-1240P、サーマルスロットリングあり）でコア数を絞ると初回起動がさらに延びるため。

- [ ] **Step 3: WSLを再起動して反映させる**

```powershell
wsl --shutdown
```

Docker Desktopが停止するので、再度起動する。

```powershell
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
```

- [ ] **Step 4: 反映を確認する**

```powershell
wsl -d Ubuntu-24.04 -- free -m
```

Expected: `Mem:` 行の `total` が約8000MB前後になっていること。Step 1で控えた値から変化していない場合は `.wslconfig` の場所（`$env:USERPROFILE` 直下か）と `[wsl2]` というセクション名を確認する。

- [ ] **Step 5: コミットは行わない**

`.wslconfig` はリポジトリ外のユーザー設定であり追跡しない（spec 4.6節）。設定した値はTask 6で `docs/gitlab-local.md` に手順として記録する。**ここで設定した値をメモしておくこと。**

---

### Task 3: `run_gitlab.ps1` と初回起動

**Files:**
- Create: `run_gitlab.ps1`

**Interfaces:**
- Consumes: Task 1の `infra/gitlab/docker-compose.yml`、コンテナ名 `local-gitlab`
- Produces: `.\run_gitlab.ps1 up` / `down` / `status` / `sync` の4サブコマンド。Task 4が `sync` を、Task 5が `up` / `down` / `status` を使う

- [ ] **Step 1: 確認コマンドを先に実行して失敗を見る**

```powershell
.\run_gitlab.ps1 status
```

Expected: FAIL（`用語 '.\run_gitlab.ps1' は...認識されません` 相当。ファイルがまだ無いため）

- [ ] **Step 2: `run_gitlab.ps1` を作る**

リポジトリルートに以下の内容で作成する。`scripts/` に置かないのは、そこが `__init__.py` を持ちpytestからimportされるPythonパッケージであるため（spec 4.1節）。

```powershell
# ローカルGitLab CE の起動・停止・同期をまとめた入口。
#
# GitLabは「必要なときだけ起動する」運用（設計書2.3節）のため、docker compose を
# 直接叩かずこのスクリプトに一本化する。特に up は、healthyになるまで待たずに
# ブラウザを開くと「起動していない」ように見えてしまうため、待機を必ず挟む。
#
# 設計の根拠は docs/superpowers/specs/2026-09-04-local-gitlab-design.md を参照。

param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "status", "sync")]
    [string]$Command = "status"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ComposeFile   = Join-Path $PSScriptRoot "infra\gitlab\docker-compose.yml"
$EnvFile       = Join-Path $PSScriptRoot "infra\gitlab\.env"
$ContainerName = "local-gitlab"
$GitLabUrl     = "http://localhost:8929"

function Get-GitLabHealth {
    # コンテナが存在しない場合と、存在するが起動途中の場合を呼び出し側で
    # 区別したいので "absent" を別の戻り値にする。
    # docker inspect のstderrを潰す書き方はPowerShell 5.1で終了コードの扱いが
    # 不安定になるため、存在確認は docker ps で先に行う。
    $found = docker ps -a --filter "name=^$ContainerName$" --format "{{.Names}}"
    if (-not $found) { return "absent" }
    $state = docker inspect --format "{{.State.Health.Status}}" $ContainerName
    return $state.Trim()
}

switch ($Command) {

    "up" {
        if (-not (Test-Path $EnvFile)) {
            throw "infra\gitlab\.env がありません。infra\gitlab\.env.example をコピーして作成してください。"
        }

        docker compose -f $ComposeFile up -d
        if (-not $?) { throw "docker compose up に失敗しました。" }

        Write-Host "GitLabの起動を待っています。初回はreconfigureが走るため十数分かかることがあります。"
        $started = Get-Date
        while ($true) {
            $health = Get-GitLabHealth
            if ($health -eq "healthy") { break }
            if ($health -eq "absent") { throw "コンテナが見つかりません。docker compose up が失敗しています。" }
            $elapsed = [int]((Get-Date) - $started).TotalSeconds
            Write-Host ("  {0}秒経過 / 状態: {1}" -f $elapsed, $health)
            Start-Sleep -Seconds 15
        }
        $total = [int]((Get-Date) - $started).TotalSeconds
        Write-Host ("GitLabが起動しました（{0}秒）: {1}" -f $total, $GitLabUrl)
    }

    "down" {
        docker compose -f $ComposeFile down
        if (-not $?) { throw "docker compose down に失敗しました。" }
        Write-Host "GitLabを停止しました。リポジトリのデータはvolumeに残ります。"
    }

    "status" {
        $health = Get-GitLabHealth
        switch ($health) {
            "absent"  { Write-Host "GitLabコンテナは存在しません（停止中）。" }
            "healthy" { Write-Host ("GitLabは起動しています: {0}" -f $GitLabUrl) }
            default   { Write-Host ("GitLabは起動処理中です。状態: {0}" -f $health) }
        }
    }

    "sync" {
        # GitLabは常時起動していないので、停止中にpushして分かりにくい
        # ネットワークエラーを見るより、先に理由を明示して止める。
        if ((Get-GitLabHealth) -ne "healthy") {
            throw "GitLabが起動していません。先に .\run_gitlab.ps1 up を実行してください。"
        }
        $remotes = git -C $PSScriptRoot remote
        if ($remotes -notcontains "gitlab") {
            throw "gitlab remoteが未登録です。docs\gitlab-local.md の手順で追加してください。"
        }

        # ブランチ名を手で打つと取りこぼすため、全ブランチと全タグをまとめて送る。
        git -C $PSScriptRoot push --all gitlab
        if (-not $?) { throw "ブランチのpushに失敗しました。" }
        git -C $PSScriptRoot push --tags gitlab
        if (-not $?) { throw "タグのpushに失敗しました。" }
        Write-Host "全ブランチ・全タグを gitlab へ同期しました。"
    }
}
```

- [ ] **Step 3: 起動前の `status` を確認する**

```powershell
.\run_gitlab.ps1 status
```

Expected: `GitLabコンテナは存在しません（停止中）。`

- [ ] **Step 4: `sync` がGitLab停止中に正しく止まることを確認する**

```powershell
.\run_gitlab.ps1 sync
```

Expected: FAIL。`GitLabが起動していません。先に .\run_gitlab.ps1 up を実行してください。` というメッセージで止まること。**pushが実行されていないことが重要**（`origin` に誤って送られない）。

- [ ] **Step 5: 初回起動する**

```powershell
.\run_gitlab.ps1 up
```

Expected: 15秒ごとに `starting` の経過が表示され、最終的に `GitLabが起動しました（N秒）: http://localhost:8929` が出る。**表示された秒数を「初回起動（reconfigure含む）」の実測値として控える**（Task 6で記録する）。

失敗した場合は次で状況を確認する。

```powershell
docker compose -f infra\gitlab\docker-compose.yml logs --tail 100
```

- [ ] **Step 6: Web UIにログインできることを確認する**

ブラウザで `http://localhost:8929` を開く。ユーザー名 `root`、パスワードは `infra/gitlab/.env` の `GITLAB_ROOT_PASSWORD` に設定した値。

Expected: ログインでき、GitLabのダッシュボードが表示されること。

- [ ] **Step 7: 起動中の `status` を確認する**

```powershell
.\run_gitlab.ps1 status
```

Expected: `GitLabは起動しています: http://localhost:8929`

- [ ] **Step 8: 定常時のメモリとディスクを実測する**

Web UIにログインした直後の状態で測る。

```powershell
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}} / CPU {{.CPUPerc}}" local-gitlab
docker system df -v
```

**表示された値を控える**（Task 6で記録する）。`docker system df -v` の出力からは、`local-gitlab_gitlab_config` / `local-gitlab_gitlab_logs` / `local-gitlab_gitlab_data` の3つのサイズと、イメージのサイズを拾う。

- [ ] **Step 9: コミット**

```powershell
git add run_gitlab.ps1
git commit -m "feat: add a helper that starts, stops and syncs the local GitLab"
```

---

### Task 4: GitHubからのインポートと同期

**Files:**
- 追跡ファイルの変更は無い（GitLab側の状態と、ローカルの `.git/config` のremote設定を変える）

**Interfaces:**
- Consumes: Task 3の `.\run_gitlab.ps1 up` / `sync`、起動中のGitLab
- Produces: `gitlab` という名前のgit remote。GitLab上のプロジェクト `local-llm-rag`

- [ ] **Step 1: GitLabが起動していることを確認する**

```powershell
.\run_gitlab.ps1 status
```

Expected: `GitLabは起動しています: http://localhost:8929`。停止していれば `.\run_gitlab.ps1 up` を実行する。

- [ ] **Step 2: Web UIからGitHubのリポジトリをインポートする**

ブラウザで `http://localhost:8929/projects/new#import_project` を開き、「Repository by URL」を選ぶ。

- Git repository URL: `https://github.com/Hide369/local-llm-rag.git`
- Project name: `local-llm-rag`
- Visibility: Private

認証情報は空欄でよい（公開リポジトリのため）。「Create project」を押す。

Expected: インポートが完了し、プロジェクトのページが開けること。

- [ ] **Step 3: インポート結果がGitHubと一致することを確認する**

GitLabのプロジェクトページで `master` の最新コミットのSHAを確認し、ローカルの `origin/master` と突き合わせる。

```powershell
git log --oneline origin/master -1
```

Expected: GitLab上の `master` 最新コミットのSHAが、`origin/master` の最新コミットと一致すること。

- [ ] **Step 4: `gitlab` remoteを追加する**

Step 2のプロジェクトページに表示されるHTTPのクローンURLを使う。`<user>` はGitLabで作成したプロジェクトの名前空間（rootで作った場合は `root`）。

```powershell
git remote add gitlab http://localhost:8929/<user>/local-llm-rag.git
git remote -v
```

Expected: `origin`（GitHub）と `gitlab`（localhost:8929）の両方が表示されること。**`origin` のURLが `https://github.com/Hide369/local-llm-rag.git` のまま変わっていないこと**を必ず確認する。

- [ ] **Step 5: `sync` を実行する**

```powershell
.\run_gitlab.ps1 sync
```

初回はGitLabのHTTP認証を求められる。ユーザー名 `root`、パスワードは `.env` の `GITLAB_ROOT_PASSWORD`。

Expected: `全ブランチ・全タグを gitlab へ同期しました。`

- [ ] **Step 6: 全ブランチが揃ったことを確認する**

```powershell
git ls-remote --heads gitlab
git ls-remote --heads origin
```

Expected: `origin` 側のブランチがすべて `gitlab` 側にも存在すること。現在 `origin` には `master` に加えて `feat/colab-l4-ollama-connection`、`feat/reranker`、`feat/reranker-impl`、`feat/vlm-image-captioning`、`fix/colab-gpu-detection`、`fix/colab-zstd-dependency` の6本がある。

なお、この作業ブランチ `docs/local-gitlab-design` は `gitlab` 側にだけ増える。`sync` はローカルにあるブランチをすべて送るため、これは正常。

- [ ] **Step 7: 追跡ファイルに変更が無いことを確認する**

このタスクは `.git/config` とGitLab側の状態のみを変えるため、追跡ファイルの変更は発生しない。

```powershell
git status --short
```

Expected: 何も出力されないこと。何か出た場合は意図しない変更なので調べる。

---

### Task 5: 永続化・自動起動・メモリ上限の検証

**Files:**
- Modify: `%USERPROFILE%\.wslconfig`（実測値に基づき締め直す。コミットしない）

**Interfaces:**
- Consumes: Task 3の `run_gitlab.ps1`、Task 4でインポート済みのGitLab、Task 3 Step 8のメモリ実測値
- Produces: spec 7.1節の全7項目の検証結果。Task 6がこれを記録する

- [ ] **Step 1: 停止する**

```powershell
.\run_gitlab.ps1 down
```

Expected: `GitLabを停止しました。リポジトリのデータはvolumeに残ります。`

- [ ] **Step 2: volumeが残っていることを確認する**

```powershell
docker volume ls --filter "name=local-gitlab"
```

Expected: `local-gitlab_gitlab_config` / `local-gitlab_gitlab_logs` / `local-gitlab_gitlab_data` の3つが残っていること。

- [ ] **Step 3: 再起動してデータが残っていることを確認する**

```powershell
.\run_gitlab.ps1 up
```

Expected: 2回目はreconfigureが走らないため初回より短く起動する。**表示された秒数を「2回目以降の起動時間」の実測値として控える**（Task 6で記録する）。

ブラウザで `http://localhost:8929` を開き、Task 4でインポートしたプロジェクトが残っていることを確認する。

- [ ] **Step 4: 自動起動しないことを確認する（spec 4.5節の検証）**

```powershell
.\run_gitlab.ps1 down
```

Docker Desktopを終了し、再度起動する。

```powershell
Stop-Process -Name "Docker Desktop" -Force
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
```

Docker Desktopが起動しきったあとで確認する。

```powershell
.\run_gitlab.ps1 status
```

Expected: `GitLabコンテナは存在しません（停止中）。` **ここで「起動しています」または「起動処理中です」と出たら `restart` ポリシーが効いていないので、`docker-compose.yml` の `restart: "no"` を確認して直す。**

- [ ] **Step 5: `.wslconfig` のメモリ上限を実測値に基づいて締める**

Task 3 Step 8で控えたGitLabのメモリ使用量を使う。上限は「GitLabの実測値 + 2GB」を目安に、1GB単位で切り上げて決める。たとえば実測が3.4GBなら6GBにする。

Task 2で書いた `[wsl2]` の `memory=8GB` をこの値に書き換える。

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

コメントも実測に合わせて更新する。

```ini
[wsl2]
# ローカルGitLab CEの実測メモリ使用量（docs/gitlab-local.md 参照）に
# 2GBの余裕を足した値。残りをWindows本体・Streamlit・ローカルOllamaに残す。
memory=<決めた値>GB
swap=2GB
```

- [ ] **Step 6: 締めた上限でGitLabが正常に動くことを確認する**

```powershell
wsl --shutdown
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
```

Docker Desktopの起動後:

```powershell
.\run_gitlab.ps1 up
```

Expected: healthyまで到達すること。**到達しない、またはコンテナが落ちる場合は上限が厳しすぎるので、1GBずつ増やして再試行し、通った値を採用する。** 採用した値と、途中で失敗した値があればそれもTask 6で記録する。

- [ ] **Step 7: メモリが想定より多い場合のみ、抑制設定を締める（spec 10節）**

Task 3 Step 8の実測メモリが **4GBを超えていた場合のみ** このステップを行う。4GB以下なら何もせず次へ進む。

`infra/gitlab/docker-compose.yml` の `GITLAB_OMNIBUS_CONFIG` を次の順に1つずつ変更し、そのつど `.\run_gitlab.ps1 down` → `up` → `docker stats --no-stream ... local-gitlab` で効果を測る。**1度に2つ変えると、どちらが効いたか分からなくなる。**

1. `puma['worker_processes'] = 2` を `1` にする
2. それでも4GBを超えるなら `sidekiq['max_concurrency'] = 5` を `3` にする

```powershell
.\run_gitlab.ps1 down
# docker-compose.yml を1箇所だけ編集する
.\run_gitlab.ps1 up
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}" local-gitlab
```

Expected: Web UIのログインと表示が変更前と同じように動くこと。**応答が体感で明らかに遅くなった場合は絞りすぎなので1つ前の値に戻す。** 採用した最終値をTask 6で記録する。

変更した場合はコミットする。

```powershell
git add infra/gitlab/docker-compose.yml
git commit -m "perf: trim GitLab worker counts to the measured memory budget"
```

- [ ] **Step 8: 検証結果をまとめる**

spec 7.1節の7項目それぞれについて、結果（成功／失敗と、失敗した場合の対処）を書き出しておく。Task 6でこれを `docs/gitlab-local.md` に転記する。

1. `up` で起動しヘルスチェックが通る
2. `http://localhost:8929` にrootでログインできる
3. インポートしたコミット履歴がGitHubと一致する
4. `sync` で全ブランチ・全タグが反映される
5. `down` で停止する
6. 再度 `up` してデータが残っている
7. Docker Desktop再起動でGitLabが自動起動しない

- [ ] **Step 9: 未コミットの変更が無いことを確認する**

```powershell
git status --short
```

Expected: 何も出力されないこと（`.wslconfig` はリポジトリ外であり、Step 7で `docker-compose.yml` を変えた場合はそこでコミット済みのため）。

---

### Task 6: ドキュメント整備

**Files:**
- Create: `docs/gitlab-local.md`
- Modify: `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Task 2 Step 2、Task 3 Step 5・8、Task 5 Step 3・5・6・7・8の実測値と検証結果
- Produces: なし（Phase 1の最終タスク）

- [ ] **Step 1: `docs/gitlab-local.md` を作る**

以下の骨子で書く。**実測値の欄には、前タスクで控えた実際の数値だけを入れる。目安値や「約N分程度」といった推測は書かない**（spec 7.2節）。

````markdown
# ローカルGitLabにミラーする

GitHub（`Hide369/local-llm-rag`）を正としたまま、手元のGitLab CEに全ブランチ・
全タグの複製を持つための手順。設計の根拠は
[設計書](superpowers/specs/2026-09-04-local-gitlab-design.md) を参照。

**GitLabは必要なときだけ起動する。** 常時起動するとOllamaとメモリを取り合うため、
`restart` ポリシーは `"no"` にしてありDocker Desktopの起動にも追随しない。

## セットアップ

### 1. WSL2のメモリ上限を設定する

`%USERPROFILE%\.wslconfig` に以下を書く（リポジトリには含まれない）。

（Task 5 Step 5で確定した内容をここに転記する）

設定後は `wsl --shutdown` してDocker Desktopを起動し直す。

### 2. `.env` を用意する

（`infra/gitlab/.env.example` を `.env` にコピーする `Copy-Item` のコマンドと、
`GITLAB_VERSION` に実際に採用したバージョン、`GITLAB_ROOT_PASSWORD` に8文字以上を
設定する旨を書く。パスワードの実値は書かない）

### 3. 起動する

（`.\run_gitlab.ps1 up` のコマンドと、初回はreconfigureが走るため時間がかかること、
実際にかかった時間は下の「実測値」を参照する旨を書く）

### 4. GitHubからインポートする

（`http://localhost:8929/projects/new#import_project` を開き「Repository by URL」に
`https://github.com/Hide369/local-llm-rag.git` を入力する手順と、その後の
`git remote add gitlab <実際に使ったURL>` までを書く。`origin` は変更しないことを明記する）

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

## 実測値

| 項目 | 実測値 | 測定日 |
|---|---|---|
| 初回起動（reconfigure含む） | | |
| 2回目以降の起動 | | |
| 定常時メモリ | | |
| ディスク（volume 3つ計） | | |
| ディスク（イメージ） | | |
| `.wslconfig` の memory | | |
| `puma['worker_processes']` | | |
| `sidekiq['max_concurrency']` | | |

測定環境: Intel Core i5-1240P（GPUなし）、メモリ16GB。連続負荷で熱により
約2.5倍遅くなるため、他の負荷がかかっている状態ではこれより延びる。

## 動作確認の記録

（Task 5 Step 8で書き出した7項目とその結果を、項目ごとに成功／失敗が分かる形で書く）

## バックアップを取っていない理由

GitLabはバックアップ「先」であり、正はGitHubにある。volumeが壊れても
「GitHubからインポートし直す」で復旧できるため、バックアップのバックアップは
持たない。**将来GitLabを正に切り替える場合は、バックアップ設計が別途必須になる。**

## Phase 2（CI/CD）について

Runnerと `.gitlab-ci.yml` はまだ導入していない。上の実測値を踏まえて、
このハードウェアでCIまで載せられるかを判断してから着手する。
````

- [ ] **Step 2: 実測値と検証結果を埋める**

Step 1の骨子のうち、括弧書きで示した箇所と実測値の表のセルを、すべて実際の内容で置き換える。測定日は作業を行った日付を入れる。**括弧書きのプレースホルダと空セルを1つも残さないこと。**

- [ ] **Step 3: `.gitignore` のコメントを更新する**

除外規則は変えない。コメント文だけを書き換える（spec 4.1節）。

変更前:

```
# ColabのL4 GPUに接続するときの OLLAMA_HOST / OLLAMA_API_KEY を書く（秘密情報）
.env
```

変更後:

```
# 秘密情報を書くファイル。ルート直下の .env にはColabのL4 GPU接続用の
# OLLAMA_HOST / OLLAMA_API_KEY を、infra/gitlab/.env にはローカルGitLabの
# GITLAB_ROOT_PASSWORD を書く。パターンにスラッシュが無いため全階層に一致する。
.env
```

- [ ] **Step 4: `.gitignore` の変更で除外が壊れていないことを確認する**

```powershell
git check-ignore -v .env infra/gitlab/.env
```

Expected: 両方とも `.gitignore` の `.env` 行にマッチしていると表示されること。

- [ ] **Step 5: READMEに節を追加する**

`## ColabのL4 GPUに接続する` 節の直後、`## 構成` の直前に以下を挿入する。

```markdown
## ローカルGitLabにミラーする

GitHubを正としたまま、手元のGitLab CEに全ブランチ・全タグの複製を持てる。
GitLabはOllamaとメモリを取り合うため常時起動はせず、必要なときだけ
`.\run_gitlab.ps1 up` で立ち上げて使う。

セットアップと運用の手順は [docs/gitlab-local.md](docs/gitlab-local.md) を参照。
```

- [ ] **Step 6: READMEの構成表に2行追加する**

`## 構成` の表の末尾に以下の2行を追加する。

```markdown
| `infra/gitlab/` | ローカルGitLab CEのDocker定義（アプリ本体には非依存） |
| `run_gitlab.ps1` | ローカルGitLabの起動・停止・同期 |
```

- [ ] **Step 7: READMEの設計資料にリンクを追加する**

`## 設計資料` の一覧の末尾に以下の2行を追加する。

```markdown
- 設計書（ローカルGitLab）: `docs/superpowers/specs/2026-09-04-local-gitlab-design.md`
- 実装計画（ローカルGitLab）: `docs/superpowers/plans/2026-09-04-local-gitlab.md`
```

- [ ] **Step 8: 既存のテストが壊れていないことを確認する**

このPhaseではアプリケーションコードに触れていないため全て通るはずだが、念のため確認する。

```powershell
.\myvenv313\Scripts\python.exe -m pytest
```

Expected: 既存と同じ結果（PASS）。1件でも失敗した場合は、この計画の変更が原因かを必ず確認する。

- [ ] **Step 9: コミット**

```powershell
git add docs/gitlab-local.md README.md .gitignore
git commit -m "docs: document how to run and sync the local GitLab mirror"
```

- [ ] **Step 10: 変更範囲がGlobal Constraintsどおりであることを確認する**

```powershell
git diff --stat master...HEAD
```

Expected: 変更されたのが `infra/gitlab/docker-compose.yml`、`infra/gitlab/.env.example`、`run_gitlab.ps1`、`docs/` 配下、`README.md`、`.gitignore` のみであること。**`ingest/`・`rag_chat_app.py`・`scripts/`・`tests/`・`requirements.txt` に1行でも差分があれば、それは意図しない変更なので取り消す。**
