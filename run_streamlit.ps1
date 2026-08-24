# 前回のセッションが残したStreamlitプロセスがポート8501を掴んだままだと
# 新しい `streamlit run` がポート使用中で起動に失敗する（起動ログも出ないため
# 「起動しない」ように見える）。起動前に8501番のLISTENINGプロセスを検出して
# 終了させてから起動することで、これを毎回自動的に回避する。
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$listeners = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue

if ($listeners) {
    $pids = $listeners.OwningProcess | Sort-Object -Unique
    foreach ($listenerPid in $pids) {
        $proc = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "ポート8501を使用中の古いプロセスを終了します: PID $listenerPid ($($proc.ProcessName))"
            Stop-Process -Id $listenerPid -Force
        }
    }
    Start-Sleep -Milliseconds 500
}

& "$PSScriptRoot\myvenv313\Scripts\python.exe" -m streamlit run "$PSScriptRoot\rag_chat_app.py"
