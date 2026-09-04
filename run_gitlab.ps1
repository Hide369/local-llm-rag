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
    # .State.Health.Status だけを見てはいけない。コンテナが異常終了しても
    # このフィールドは終了直前の値（多くの場合 healthy や starting）を保持し続け、
    # docker ps -a にも残るため、健康状態だけでは「止まっている」ことを検知できない。
    # 実際にこの構成でコンテナが exit 255 で落ちた事例があり（docs/gitlab-local.md
    # 「既知の不安定さ」）、その場合 up は死んだコンテナを永久にポーリングし、
    # status は「起動処理中」と誤報する。実行中かどうかを併せて読む。
    $running = docker inspect --format "{{.State.Running}}" $ContainerName
    if ($running.Trim() -ne "true") { return "stopped" }
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
            if ($health -eq "absent") { throw "コンテナが見つかりません。docker compose up が失敗しています。" }
            if ($health -eq "stopped") {
                throw "コンテナが停止しています。起動直後に異常終了した可能性があります。`ndocker compose -f $ComposeFile logs gitlab で終了理由を確認してください。"
            }

            # コンテナのhealthcheckは、reconfigureが終わる前にnginxがポートを
            # 開けた時点で healthy を返すことが実測で確認できた（このマシンでは
            # healthy 判定からサインイン画面が実際に200を返すまで約167秒のギャップが
            # あった。記録した実測値は docs/gitlab-local.md 参照）。healthyだけを見て
            # 「起動しました」と表示すると、その案内を見てブラウザを開いたユーザーや、
            # 直後に .\run_gitlab.ps1 sync 等を叩くTask 4が死んだポートに当たって
            # しまう。そのためサインイン画面が実際に200を返すまで追加で待つ。
            $httpReady = $false
            if ($health -eq "healthy") {
                try {
                    $response = Invoke-WebRequest -Uri "$GitLabUrl/users/sign_in" -UseBasicParsing -TimeoutSec 10
                    if ($response.StatusCode -eq 200) { $httpReady = $true }
                } catch {
                    # 接続拒否やタイムアウトはまだ起動途中という意味なので、
                    # ここで止めずに待機を続ける。
                    $httpReady = $false
                }
            }

            if ($health -eq "healthy" -and $httpReady) { break }

            $elapsed = [int]((Get-Date) - $started).TotalSeconds
            $httpState = if ($httpReady) { "応答あり" } else { "未応答" }
            Write-Host ("  {0}秒経過 / コンテナ: {1} / サインイン画面: {2}" -f $elapsed, $health, $httpState)
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
            "stopped" { Write-Host "GitLabコンテナは存在しますが停止しています。意図しない終了であれば docker compose -f infra\gitlab\docker-compose.yml logs gitlab で理由を確認してください。" }
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

        # 名前が gitlab である remote が存在することだけでは不十分。誤って
        # `git remote add gitlab https://github.com/...` のように登録されていると、
        # 以降のブランチpushや --tags のpushがそのままGitHubへ飛ぶ。GitHubを上書き
        # しないことはこの設計で唯一許容できない事象なので、ネットワーク操作に
        # 入る前に宛先そのものを確認する。
        $gitlabUrl = git -C $PSScriptRoot remote get-url gitlab
        if ($gitlabUrl -notlike "http://localhost:8929/*") {
            throw "gitlab remoteの宛先が想定外です（$gitlabUrl）。ローカルGitLab以外へpushしないよう中止します。"
        }

        # GitHub側の最新状態をまず取り込む。--prune で、GitHub上で削除された
        # ブランチをこちらでも追跡し続けてしまうことを防ぐ。
        git -C $PSScriptRoot fetch origin --prune
        if (-not $?) { throw "origin からのfetchに失敗しました。" }

        # git push --all はローカルにチェックアウト済みのブランチしか送らない。
        # 実測でこれが原因となり、GitHub上の7ブランチ中6ブランチ（ローカルに
        # 存在しなかったfeature/fixブランチ）が無言で同期から漏れた。
        # ミラーはローカルの作業状態ではなくGitHub（origin）の実態を反映すべき
        # なので、origin のリモート追跡ブランチを直接 gitlab へ送る。
        # refs/remotes/origin/* を単純にワイルドカードで渡すと、実ブランチでは
        # ない refs/remotes/origin/HEAD（symbolic ref）まで
        # "refs/heads/HEAD" として送ろうとして GitLab に不正なブランチ名として
        # 拒否される（実測で確認）ため、for-each-ref で実ブランチのみを列挙して
        # 明示的なrefspecを組み立てる。
        # パイプラインの途中で終了コードを見ると $? は最後のコマンドレット
        # （Where-Object）の成否を返してしまい、git 側の失敗を取り逃がす。
        # git の結果を一度受けてから $LASTEXITCODE で判定し、絞り込みは別行で行う。
        $originRefsRaw = git -C $PSScriptRoot for-each-ref --format="%(refname)" refs/remotes/origin
        if ($LASTEXITCODE -ne 0) { throw "origin のブランチ一覧取得（for-each-ref）に失敗しました。" }
        $originBranchRefs = @($originRefsRaw | Where-Object { $_ -ne "refs/remotes/origin/HEAD" })

        # 0本になるのは通常ありえない（最低でも master はあるはず）。空のrefspecで
        # pushしても何も送られず「同期した」と見せかけるだけで意味が無いため、
        # 黙って通過させずに異常として止める。
        if (-not $originBranchRefs) {
            throw "origin にブランチが1本も見つかりませんでした。直前の fetch origin --prune が正しく行われたか、origin remoteの設定を確認してください。"
        }

        $refspecs = $originBranchRefs | ForEach-Object {
            $branch = $_ -replace '^refs/remotes/origin/', ''
            "${_}:refs/heads/$branch"
        }
        git -C $PSScriptRoot push gitlab $refspecs
        if (-not $?) {
            throw "origin のリモート追跡ブランチから gitlab への一括pushに失敗しました。gitlab上の対象ブランチが直接変更され、GitHub側から乖離している可能性があります。gitlab側のブランチの状態を確認し、必要であれば退避・削除したうえで、もう一度 .\run_gitlab.ps1 sync を実行してください。"
        }

        # ローカルにしか存在しないブランチ（現在の作業ブランチ等、まだGitHubに
        # pushされていないもの）は上記だけでは送られないため、これも別途送る。
        #
        # ここで `git push --all gitlab` を使ってはいけない。--all はorigin側にも
        # 存在するブランチまで送るため、GitHubでPRをマージした直後（まだ pull して
        # いない状態）にローカルの master が遅れていると、その古いrefのpushが
        # 非fast-forwardで拒否され sync 全体が落ちる。タグのpushにも到達しない。
        # しかも直前のステップでミラーは既に正しい状態になっているので、この失敗は
        # 完全に無意味である。このリポジトリの履歴は「Merge pull request #N」で
        # 埋まっており、PRマージは例外ではなく通常の運用そのものなので、
        # origin に存在しないブランチだけに絞る。副次的に、ステップ2で既に送った
        # ブランチを二重にpushする無駄も無くなる。
        $originNames = $originBranchRefs | ForEach-Object { $_ -replace '^refs/remotes/origin/', '' }
        $localOnlyRaw = git -C $PSScriptRoot for-each-ref --format="%(refname:short)" refs/heads
        if ($LASTEXITCODE -ne 0) { throw "ローカルブランチ一覧の取得（for-each-ref）に失敗しました。" }
        $localOnly = @($localOnlyRaw | Where-Object { $originNames -notcontains $_ })

        # ローカル固有のブランチが0本なのは正常（全ブランチがGitHubにpush済み）。
        # 空のまま push すると引数不足になるため、送るものがある場合だけ実行する。
        if ($localOnly.Count -gt 0) {
            # ここが非fast-forwardで失敗した場合、ローカル固有のはずのブランチが
            # gitlab側で直接変更されて乖離していることを意味する。直前のステップで
            # GitLabは既にGitHubと同じ状態になっているため、ここで強制pushして
            # 食い違いを揉み消すことはしない。原因を調べて解消してから再度syncする。
            git -C $PSScriptRoot push gitlab $localOnly
            if ($LASTEXITCODE -ne 0) {
                throw "ローカル固有ブランチのpushに失敗しました（非fast-forwardの可能性）。対象: $($localOnly -join ', ')。gitlab は直前のステップで既にGitHubの状態と一致しています。gitlab側の同名ブランチの状態を確認し、乖離を解消してから、もう一度 .\run_gitlab.ps1 sync を実行してください。"
            }
        } else {
            Write-Host "ローカルにしか存在しないブランチはありません。"
        }

        git -C $PSScriptRoot push --tags gitlab
        if (-not $?) { throw "タグのpushに失敗しました。" }
        Write-Host "全ブランチ・全タグを gitlab へ同期しました。"
    }
}
