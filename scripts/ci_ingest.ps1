# GitLab CI から呼ばれる、資料取り込みの入口。
#
# 設計の根拠は docs/superpowers/specs/2026-09-05-ci-ingest-design.md を参照。
#
# 重い処理の前に失敗条件をすべて確認する順序になっている。全量の取り込みは
# 24分かかるため、20分走ってから「Streamlitが起動していました」と言われても遅い。

param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# --- 1. 入力ディレクトリの存在 ---
if (-not (Test-Path -Path $SourceDir -PathType Container)) {
    Write-Host "ディレクトリがありません: $SourceDir"
    exit 1
}

# --- 2. 入力が資料リポジトリのチェックアウトであることの確認 ---
# ingest_source.py は入力ディレクトリに無い資料をDBから削除する（孤児削除）。
# これは「入力がリポジトリ全体である」ことが前提の挙動であり、小さなディレクトリを
# 誤って渡すとDBの中身がほぼ全部消える。復旧は全量24分の再取り込みになる。
# CIの正常経路は常に $CI_PROJECT_DIR を渡すので事故は起きない。危険なのは
# 人間が手で叩くときで、動作確認手順がまさにそれを要求している以上、塞いでおく。
#
# remote名は origin とは限らない（local_llm/source の remote名は gitlab）。
# 手動実行でそのディレクトリを渡す経路も残すため、remote名では絞らず
# 全remoteのURLを見る。
#
# Windows PowerShell 5.1 の既知の挙動として、$ErrorActionPreference = "Stop" の
# もとではネイティブコマンドのstderr出力が 2>$null で握っていても終了エラーに
# なってしまう（リダイレクトより先に例外化される）。スクリプトブロック内だけ
# ErrorActionPreference を緩め、$LASTEXITCODE で結果を判定する。
$remotes = & { $ErrorActionPreference = "Continue"; git -C $SourceDir remote -v 2>$null }
if ($LASTEXITCODE -ne 0 -or -not ($remotes -match "source-archive")) {
    Write-Host "資料リポジトリのチェックアウトではありません: $SourceDir"
    Write-Host "  source-archive を指すremoteが見つかりません。誤ったディレクトリを"
    Write-Host "  取り込むとベクトルDBの資料がすべて孤児として削除されるため中止します。"
    exit 1
}

# --- 3. Streamlit 稼働ガード ---
# rag_chat_app.py は PersistentClient を @st.cache_resource でプロセス内に保持し、
# BM25インデックスも起動時に一度だけ構築する。稼働中に別プロセスがchroma_dbへ
# 書き込むと、HNSWファイルの整合が取れなくなる上、更新もアプリ再起動まで反映
# されない。
#
# 既定を8501だけにしてはいけない。過去に8503で起動した実績がある
# （.superpowers/sdd/2026-08-12-markdown-ingestion/streamlit-8503.log）。
$portSpec = if ($env:STREAMLIT_PORTS) { $env:STREAMLIT_PORTS } else { "8501,8503" }
$ports = $portSpec -split "," | ForEach-Object { [int]$_.Trim() }

# 待ち受けが1つも無いとき Get-NetTCPConnection はエラーを投げる。
# $listening が空になるのが正常系なので、エラーは握らず黙らせる。
$listening = Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue
if ($listening) {
    $busy = ($listening | ForEach-Object { $_.LocalPort } | Sort-Object -Unique) -join ", "
    Write-Host "Streamlitが起動しています（ポート $busy）。"
    Write-Host "  稼働中にchroma_dbへ書き込むとインデックスが壊れるため中止します。"
    Write-Host "  アプリを停止してからジョブを再実行してください。"
    Write-Host "  別用途のポートであれば STREAMLIT_PORTS で監視対象を変更できます。"
    exit 1
}

# --- 4. venv の Python ---
# Activate.ps1 は呼ばない。実行ポリシーの影響を受け、Runnerのコンテキストでは
# 対話シェルと異なる挙動になりうる。インタプリタを直接指定すれば有効化は不要で、
# 失敗する余地が1つ減る。
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot "myvenv313\Scripts\python.exe"
if (-not (Test-Path -Path $python -PathType Leaf)) {
    Write-Host "仮想環境のPythonがありません: $python"
    exit 1
}

Write-Host "事前条件をすべて満たしました。"
exit 0
