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
            if ($health -eq "absent") { throw "コンテナが見つかりません。docker compose up が失敗しています。" }

            # コンテナのhealthcheckは、reconfigureが終わる前にnginxがポートを
            # 開けた時点で healthy を返すことが実測で確認できた（このマシンでは
            # healthy 判定からサインイン画面が実際に200を返すまで80秒以上のギャップが
            # あった）。healthyだけを見て「起動しました」と表示すると、その案内を見て
            # ブラウザを開いたユーザーや、直後に .\run_gitlab.ps1 sync 等を叩くTask 4が
            # 死んだポートに当たってしまう。そのためサインイン画面が実際に200を返すまで
            # 追加で待つ。
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

        # GitHub側の最新状態をまず取り込む。--prune で、GitHub上で削除された
        # ブランチをこちらでも追跡し続けてしまうことを防ぐ。
        git -C $PSScriptRoot fetch origin --prune
        if (-not $?) { throw "origin からのfetchに失敗しました。" }

        # git push --all はローカルにチェックアウト済みのブランチしか送らない。
        # 実測でこれが原因となり、GitHub上の8ブランチ中6ブランチ（ローカルに
        # 存在しなかったfeature/fixブランチ）が無言で同期から漏れた。
        # ミラーはローカルの作業状態ではなくGitHub（origin）の実態を反映すべき
        # なので、origin のリモート追跡ブランチを直接 gitlab へ送る。
        # refs/remotes/origin/* を単純にワイルドカードで渡すと、実ブランチでは
        # ない refs/remotes/origin/HEAD（symbolic ref）まで
        # "refs/heads/HEAD" として送ろうとして GitLab に不正なブランチ名として
        # 拒否される（実測で確認）ため、for-each-ref で実ブランチのみを列挙して
        # 明示的なrefspecを組み立てる。
        $originBranchRefs = git -C $PSScriptRoot for-each-ref --format="%(refname)" refs/remotes/origin |
            Where-Object { $_ -ne "refs/remotes/origin/HEAD" }
        if ($originBranchRefs) {
            $refspecs = $originBranchRefs | ForEach-Object {
                $branch = $_ -replace '^refs/remotes/origin/', ''
                "${_}:refs/heads/$branch"
            }
            git -C $PSScriptRoot push gitlab $refspecs
            if (-not $?) { throw "origin のリモート追跡ブランチから gitlab への一括pushに失敗しました。" }
        }

        # ローカルにしか存在しないブランチ（現在の作業ブランチ等、まだGitHubに
        # pushされていないもの）は上記だけでは送られないため、これも別途送る。
        # ここが非fast-forwardで失敗した場合、ローカルブランチがGitHub上の
        # 対応ブランチと乖離していることを意味する。直前のステップでGitLabは
        # 既にGitHubと同じ状態になっているため、ここで強制pushして食い違いを
        # 揉み消すことはしない。原因を調べて解消してから再度syncしてほしい。
        git -C $PSScriptRoot push --all gitlab
        if (-not $?) {
            throw "ローカルブランチのpushに失敗しました（非fast-forwardの可能性）。ローカルのブランチがGitHub上の同名ブランチと乖離している可能性があります。gitlab は直前のステップで既にGitHubの状態と一致しています。git fetch / git rebase 等でローカルを最新のGitHubの状態に合わせてから、もう一度 .\run_gitlab.ps1 sync を実行してください。"
        }

        git -C $PSScriptRoot push --tags gitlab
        if (-not $?) { throw "タグのpushに失敗しました。" }
        Write-Host "全ブランチ・全タグを gitlab へ同期しました。"
    }
}
