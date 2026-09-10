# Streamlit RAGをWindowsサーバーへ配置する

GitHubのアプリケーションをWindowsサーバーへ配置し、クライアントのブラウザーから利用するための手順書。対象は `rag_chat_app.py`。**既存の資料原本・ベクトルDBは移行しない**。新環境は空のRAGで始まり、資料を新しく登録しない限り資料に基づく回答はできない。

この文書のコマンド・設定例は実環境での受け入れ確認手順であり、Windows Serverの構築・再起動・別端末からの疎通を実施済みという意味ではない。

## 1. 対象環境と構成

Windows Server 2022 / 2025のDesktop Experience、Windows PowerShell 5.1、Python 3.13 x64、IISを使う例とする。AD必須にはせず、IISのWindows認証とサーバーのローカル利用者グループを基本例にする。ドメイン環境では組織の認証・証明書・GPO管理者と調整する。

**Ollama公式のWindows要件にはWindows Serverの対応が明記されていない。** このOS選定は配置例であり公式サポートの保証ではない。採用前に対象OS・GPUドライバーで `bge-m3` と `gpt-oss:20b` の取得・推論を確認する。メモリ・VRAM・モデル用ディスクは実モデルと同時利用数で測定する。[Ollama Windows公式](https://docs.ollama.com/windows)

```text
クライアントのブラウザー
    │ HTTPS :443 / Windows認証 + 利用グループ制限
    ▼
Windowsサーバー : IIS + URL Rewrite + ARR
    │ HTTP / WebSocket → 127.0.0.1:8501
    ▼
Streamlit（1プロセス）
    ├─ source/ と vector_store.sqlite3（サーバー内のみ）
    └─ HTTP → 127.0.0.1:11434 → Ollama
```

クライアントへPython・Git・Ollama・モデル・DBを配る必要はない。必要なのはブラウザー、名前解決、CAへの信頼、認証アカウント、サーバーへのHTTPS通信だけである。別アプリから呼ぶRAG HTTP APIは現状未実装で、Streamlit画面をブラウザーで使う構成である。

現行アプリには利用者別の認証・資料ACLがなく、**認証された全利用者が同じ資料を検索でき、サイドバーの「差分を取り込む」と「資料をアップロード」も実行できる**。アップロードされた資料も同じベクトルDBへ入り、全利用者の検索対象になる。本手順だけで検索専用ユーザーと管理者を分離できるわけではない。取り込み権限を与えない利用者へ公開する前にはUIの削除・権限制御などの実装変更が必要。SQLiteとメモリー内キャッシュを使うため、複数レプリカではなく1プロセスから運用する。

## 2. パス・アカウント・ソフトウェアの準備

以下は新規専用サーバーの例。既存の同名フォルダー・ユーザー・IISサイト・タスクがある場合は、そのまま上書きせず先に用途を確認する。

|用途|設定例|
|---|---|
|公開DNS名| `rag.example.internal` （実際の名前へ全箇所置換）|
|サーバーIP / 許可するLAN| `192.168.10.20` / `192.168.10.0/24` |
|アプリ配置先| `C:\RAG\local-llm-rag` |
|専用実行アカウント| サーバーの標準ローカルユーザー `rag-svc` |
|利用者グループ| サーバーのローカルグループ `RAGUsers` |
|運用スクリプト / 設定| `C:\RAG\ops` / `C:\RAG\config` |
|モデル / ログ| `C:\RAG\models` / `C:\RAG\logs` |
|Ollama本体| `C:\RAG\tools\ollama\ollama.exe` |
|IISサイトのルート / 証明書申請| `C:\RAG\web` / `C:\RAG\tls` |

### 2.1 管理者PowerShellで初期準備

Git for WindowsとPython 3.13 x64を公式配布元からインストールする。Pythonは専用アカウントから実行できる**全ユーザー向け**に配置し、以下の `C:\Program Files\Python313\python.exe` を実際のパスに合わせる。`python` という名前だけに依存せず、3.13系であることを確認する。[PythonのWindowsインストール](https://docs.python.org/3.13/using/windows.html)

```powershell
$ErrorActionPreference = 'Stop'
git --version
& 'C:\Program Files\Python313\python.exe' --version

$ragPassword = Read-Host 'rag-svc のパスワード' -AsSecureString
New-LocalUser -Name 'rag-svc' -Password $ragPassword -Description 'RAG runtime'
Add-LocalGroupMember -SID 'S-1-5-32-545' -Member "$env:COMPUTERNAME\rag-svc"
New-LocalGroup -Name 'RAGUsers' -Description 'RAG browser users'

New-Item -ItemType Directory -Path 'C:\RAG'
icacls.exe 'C:\RAG' /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'ACL setup failed' }
icacls.exe 'C:\RAG' /grant "$env:COMPUTERNAME\rag-svc:(RX)"
if ($LASTEXITCODE -ne 0) { throw 'Runtime traversal grant failed' }

'ops','config','models','logs','tools','web','tls' | ForEach-Object {
    New-Item -ItemType Directory -Path (Join-Path 'C:\RAG' $_)
}
New-Item -ItemType Directory -Path 'C:\RAG\models\ollama','C:\RAG\models\huggingface'
```

SID `S-1-5-32-544` はAdministrators、`S-1-5-18` はSYSTEM、`S-1-5-32-545` は一般Usersグループ。親の継承を外し、この配下が一般利用者から読み書きできない状態で作成する。`icacls` の終了コードが0であることを各操作後に確認する。以後の外部コマンドもエラーがあれば次へ進まない。[icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls)

`rag-svc` はAdministratorsやRAGUsersへ追加しない。パスワードは管理台帳で保管・更新し、タスクに保存した資格情報も同時に更新する。ドメインのパスワード期限・「バッチジョブとしてログオン」権利・拒否ポリシーが適用される場合は管理者に確認する。

### 2.2 アプリとOllamaを配置

```powershell
git clone --branch master https://github.com/Hide369/local-llm-rag.git 'C:\RAG\local-llm-rag'
if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }
Set-Location 'C:\RAG\local-llm-rag'
git rev-parse HEAD
& 'C:\Program Files\Python313\python.exe' -m venv myvenv313
if ($LASTEXITCODE -ne 0) { throw 'Venv creation failed' }
& '.\myvenv313\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
New-Item -ItemType Directory -Path '.\source','.\.streamlit'
```

仮想環境名はリポジトリのGit除外設定に合わせて `myvenv313` とする。旧環境の `source`・DB・仮想環境・`.env` をコピーしない。パッケージは再インストールし、モデルも新環境で取得する。閉域環境では必要なパッケージとモデルの持ち込み方法を別途準備する。

Ollamaは公式Windowsページの**スタンドアロンZIP**を取得し、DLL・サブフォルダーを含む全内容を `C:\RAG\tools\ollama` へ展開する。GPUごとの追加ファイル・ドライバー条件も同ページで確認する。GUIインストーラー版を併用しない。既にある場合はトレイのOllamaを終了し、自動起動を無効にして、後述のタスクとの11434番競合を防ぐ。[Ollamaのスタンドアロン配置](https://docs.ollama.com/windows#standalone-cli)

専用アカウントへ必要な権限だけを追加する（管理者PowerShell）。

```powershell
$ragAccount = "$env:COMPUTERNAME\rag-svc"
foreach ($ragPath in 'C:\RAG\ops','C:\RAG\config','C:\RAG\tools') {
    icacls.exe $ragPath /grant:r "$($ragAccount):(OI)(CI)RX"
    if ($LASTEXITCODE -ne 0) { throw "ACL failed: $ragPath" }
}
foreach ($ragPath in 'C:\RAG\local-llm-rag','C:\RAG\models','C:\RAG\logs') {
    icacls.exe $ragPath /grant:r "$($ragAccount):(OI)(CI)M"
    if ($LASTEXITCODE -ne 0) { throw "ACL failed: $ragPath" }
}
```

現在の実装はDBとSQLite補助ファイルをリポジトリ直下へ作るため、この例では専用アカウントにアプリ配置先の変更権限を与える。これはコードも変更可能にする妥協である。一般利用者には与えず、コードの読み取り専用化が必要ならDB保存先を分離する実装変更を先に行う。モデル・ログ・設定はSMB共有で利用者へ公開しない。

## 3. Streamlitと取り込みCLIに共通の環境を設定

### 3.1 秘密情報を含む環境ファイル

管理者がエディターで `C:\RAG\config\rag.env` を作成する。UTF-8で保存する。実行アカウントは前節で読み取りのみ許可済み。機械全体の環境変数やタスク引数へ秘密情報を書かない。

```ini
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODELS=C:/RAG/models/ollama
HF_HOME=C:/RAG/models/huggingface
STREAMLIT_SERVER_COOKIE_SECRET=<ここを新しく生成したランダム値に置き換える>
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

cookie secretを生成する例（表示された値を上のファイルへ保存。Gitやチケットへ貼らない）:

```powershell
& 'C:\RAG\local-llm-rag\myvenv313\Scripts\python.exe' -c "import secrets; print(secrets.token_urlsafe(48))"
```

同一サーバー内のOllamaではAPIキー不要。`OLLAMA_API_KEY` は認証付き外部接続を別途設計した場合だけ設定する（現行実装では `X-API-Key` ヘッダー）。本書は外部Ollamaを使わない。`rag.env` を設定の正本にし、アプリ配置先の `.env` は作らない。

### 3.2 Streamlitの非秘密設定

`C:\RAG\local-llm-rag\.streamlit\config.toml` に保存する。

```toml
[server]
address = "127.0.0.1"
port = 8501
headless = true
enableCORS = true
corsAllowedOrigins = ["https://rag.example.internal"]
enableXsrfProtection = true
allowedHosts = ["rag.example.internal"]

[browser]
serverAddress = "rag.example.internal"
serverPort = 443
gatherUsageStats = false
```

このサーバー固有ファイルを誤ってGitへ追加しないよう、サーバー上の `.git\info\exclude` に `/.streamlit/config.toml` を1行追記する。`git status --short` で設定やデータが追加対象に出ないことを確認する。CORS・XSRFを無効化して接続問題を回避しない。名前・HTTPS・443をDNS/IIS/ブラウザーと一致させる。[Streamlit設定](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)

### 3.3 共通ランチャーを作る

次を `C:\RAG\ops\run-rag.py` にUTF-8で保存する。これは手順書内の配置例であり、GitHubから自動配置されるファイルではない。

アプリ内の `load_dotenv()` だけではStreamlit起動時の設定読み込みに間に合わないため、**Streamlitを起動する前**に共通環境ファイルを読む。取り込みも同じPython・環境・作業ディレクトリで実行し、タスクの終了コードへ失敗を伝える。標準出力と標準エラーはログへ保存する。

```python
import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import traceback

from dotenv import load_dotenv

BASE = Path(r"C:\RAG")
REPO = BASE / "local-llm-rag"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["ollama", "chat", "ingest", "warmup"])
    mode = parser.parse_args().mode
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = BASE / "logs" / f"{mode}-{stamp}-{os.getpid()}.log"
    with log_path.open("x", encoding="utf-8") as log:
        try:
            os.chdir(REPO)
            env_path = BASE / "config" / "rag.env"
            if not env_path.is_file() or (REPO / ".env").exists():
                raise RuntimeError("Require config/rag.env and no repository .env")
            load_dotenv(env_path, override=True, encoding="utf-8-sig")
            secret = os.environ.get("STREAMLIT_SERVER_COOKIE_SECRET", "")
            if len(secret) < 32 or "<" in secret:
                raise RuntimeError("Set a generated cookie secret in rag.env")
            child_env = os.environ.copy()
            child_env["PYTHONUNBUFFERED"] = "1"
            child_env["PYTHONIOENCODING"] = "utf-8"
            if mode == "ollama":
                child_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                command = [str(BASE / "tools" / "ollama" / "ollama.exe"), "serve"]
            elif mode == "chat":
                command = [sys.executable, "-m", "streamlit", "run", "rag_chat_app.py"]
            elif mode == "ingest":
                command = [sys.executable, "-m", "scripts.ingest_source"]
            else:
                command = [
                    sys.executable, "-c",
                    "from ingest.reranker import check_reranker, rerank; "
                    "check_reranker(); "
                    "assert len(rerank('test', ['test text'])) == 1; "
                    "print('Reranker download and inference OK')",
                ]
            print(f"Starting {mode}; cwd={REPO}", file=log, flush=True)
            result = subprocess.run(
                command, cwd=REPO, env=child_env,
                stdout=log, stderr=subprocess.STDOUT, check=False,
            )
            print(f"Exit code: {result.returncode}", file=log, flush=True)
            return result.returncode
        except Exception:
            traceback.print_exc(file=log)
            return 1


if __name__ == "__main__":
    sys.exit(main())
```

環境ファイルを変更したら常駐タスクは停止・再起動が必要。取り込みは次回実行時に読み直す。ログは起動ごとに増えるため、アクセス権を維持しつつ容量監視・保存期間・ローテーションを運用で決める。

## 4. 未ログオンでも動く起動時タスクを登録する

管理者がタスクスケジューラの「タスクの作成」を使う。以下の**4タスクを個別**に登録する。OllamaとStreamlitを1タスクの複数操作に並べると直列実行になり、2本目が起動しない。[タスクの操作と作業ディレクトリ](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskaction)

共通設定:

- 実行ユーザー: `サーバー名\rag-svc`。SYSTEM・管理者では実行しない。
- 「ユーザーがログオンしているかどうかにかかわらず実行する」を選び、保存時にパスワードを入力する。「パスワードを保存しない」は選ばない。「最上位の特権で実行する」はオフ。
- `rag-svc` に「バッチジョブとしてログオン」権利があり、拒否ポリシーで打ち消されていないことを確認。
- プログラム: `C:\RAG\local-llm-rag\myvenv313\Scripts\python.exe`
- 開始（オプション）: `C:\RAG\local-llm-rag` （引用符なし）
- 設定: 「要求時に実行する」をオン。「既に実行中の場合」は「新しいインスタンスを開始しない」。
- 「タスクを停止するまでの時間」はオフ（既定の実行時間制限は72時間）。失敗時は1分ごとに3回再試行。予定時刻を過ぎた場合の実行をオン。AC電源限定・アイドル条件で停止しないよう調整する。

|タスク名|引数の追加|トリガー|
|---|---|---|
| `Local-LLM-RAG-Ollama` | `"C:\RAG\ops\run-rag.py" ollama` | システム起動時 |
| `Local-LLM-RAG-Streamlit` | `"C:\RAG\ops\run-rag.py" chat` | システム起動時、30秒遅延 |
| `Local-LLM-RAG-Ingest` | `"C:\RAG\ops\run-rag.py" ingest` | なし（管理者が要求時に実行） |
| `Local-LLM-RAG-Warmup` | `"C:\RAG\ops\run-rag.py" warmup` | なし（初回モデル準備） |

遅延は依存サービスの正常性を保証しない。起動後にOllamaのAPIとStreamlitのヘルスチェックを確認する。再試行上限に達すると自動復旧しないため、タスク結果・ログの監視と管理者による復旧が必要。資格情報と実行時間制限は[タスクのセキュリティ](https://learn.microsoft.com/en-us/windows/win32/taskschd/security-contexts-for-running-tasks)、[ログオン方式](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-logontype-principaltype-element)、[ExecutionTimeLimit](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-executiontimelimit)を参照。

### 4.1 モデルを取得する

まずOllamaタスクだけを起動する。続くAPI確認は応答するまで再実行し、エラーのままpullへ進まない。

```powershell
Start-ScheduledTask -TaskName 'Local-LLM-RAG-Ollama'
Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 30

$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
& 'C:\RAG\tools\ollama\ollama.exe' pull bge-m3
if ($LASTEXITCODE -ne 0) { throw 'Embedding model download failed' }
& 'C:\RAG\tools\ollama\ollama.exe' pull gpt-oss:20b
if ($LASTEXITCODE -ne 0) { throw 'Generation model download failed' }
& 'C:\RAG\tools\ollama\ollama.exe' list
Start-ScheduledTask -TaskName 'Local-LLM-RAG-Warmup'
```

pullしたモデルは**接続先Ollamaサーバープロセスの** `OLLAMA_MODELS` に保存される。管理者のプロファイルとサービスアカウントのモデル置き場を混同しない。

`Start-ScheduledTask` は完了を待たない。Warmupが実行中でなくなり、最終実行時刻が今回の実行時刻、最終結果が `0`、`C:\RAG\logs\warmup-*.log` に推論成功と終了コード0があることを確認する。

```powershell
Get-ScheduledTask -TaskName 'Local-LLM-RAG-Warmup'
Get-ScheduledTaskInfo -TaskName 'Local-LLM-RAG-Warmup'
Get-ChildItem 'C:\RAG\logs\warmup-*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Encoding UTF8
```

リランカーはOllamaとは別にHugging Faceから取得する。初回準備にはサーバーの外向きHTTPSが必要。画像PDFを扱う場合はRapidOCRのモデルも必要なので、同じ専用アカウントで後述のIngestタスクに検証用画像PDFを取り込ませ、モデル取得・OCRを確認する。VLMは任意機能で、本例では無効。使うなら `qwen2.5vl:7b` も取得し、Ingestの起動引数に `--with-vlm` を加えるようランチャーを変更する。[依存関係一覧](依存関係一覧.md)

### 4.2 Streamlitを起動する

```powershell
Start-ScheduledTask -TaskName 'Local-LLM-RAG-Streamlit'
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8501/_stcore/health' -TimeoutSec 30
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8501,11434
```

起動完了後にヘルスチェックが200になり、両ポートが `127.0.0.1` だけにbindしていることを確認する。常駐タスクの `Running` / `0x41301` は実行中を表すが、それだけでは正常性を判断しない。

## 5. IISのHTTPSとWindows認証を設定する

この例は社内LAN用。**内部DNSと内部CAから証明書を発行・信頼配布できること**を前提とする。`.internal` に公開CAの証明書を取得する手順ではない。内部CAがない場合は、所有する公開ドメインを使う証明書発行などを組織で決定してから進める。

### 5.1 IIS、ARR、DNS

管理者PowerShell:

```powershell
Install-WindowsFeature Web-Server,Web-WebSockets,Web-Windows-Auth,Web-Url-Auth,Web-Scripting-Tools -IncludeManagementTools
```

`Success=True` と再起動要否を確認する。その後、[URL Rewrite 2.1](https://www.iis.net/downloads/microsoft/url-rewrite) x64、[Application Request Routing 3](https://www.iis.net/downloads/microsoft/application-request-routing) x64の順に公式インストーラーで導入する。

内部DNSで `rag.example.internal` をサーバーのLAN IPへ登録する。IPv6のAAAAレコードを作る場合はIPv6の経路・ファイアウォールも設定する。サーバーと別クライアントの両方で確認:

```powershell
Resolve-DnsName rag.example.internal
```

IISマネージャーの**サーバーノード**で以下を設定する（既存サイトにも影響するサーバー共通設定なので、共有IISの場合は管理者と調整）。

1. 「Application Request Routing Cache」→「Server Proxy Settings」で「Enable proxy」をオン、Time-outを900秒に設定。
2. 「Configuration Editor」の `system.webServer/proxy` で `preserveHostHeader=True`。
3. 「URL Rewrite」→「View Server Variables」で `HTTP_X_FORWARDED_PROTO` を許可変数として追加。

ARR 3はWebSocketに対応する。WebSocketロールの導入と、転送先のHost・外部HTTPSスキームの一致が必要。許可変数への登録なしで後述の `serverVariables` を使うとエラーになる。[ARR 3とWebSocket](https://blogs.iis.net/erez/new-features-in-arr-application-request-routing-3-0/)、[URL Rewriteのサーバー変数](https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/setting-http-request-headers-and-iis-server-variables)

### 5.2 内部CAへ証明書を申請する

管理者が `C:\RAG\tls\request.inf` を作成する。例示のFQDNは実際のDNS名へ置き換え、ファイル内の `$Windows NT$` は文字列のまま保存する。

```ini
[Version]
Signature="$Windows NT$"

[NewRequest]
Subject="CN=rag.example.internal"
KeyAlgorithm=RSA
KeyLength=3072
HashAlgorithm=SHA256
MachineKeySet=TRUE
Exportable=FALSE
RequestType=PKCS10
ProviderName="Microsoft Software Key Storage Provider"

[Extensions]
2.5.29.17="{text}DNS=rag.example.internal"
2.5.29.37="{text}1.3.6.1.5.5.7.3.1"
```

管理者PowerShellで実行する。既存の申請ファイルがある場合は上書きせず更新手順を確認する。

```powershell
certreq.exe -new 'C:\RAG\tls\request.inf' 'C:\RAG\tls\rag.req'
if ($LASTEXITCODE -ne 0) { throw 'Certificate request failed' }
```

`rag.req` のみを内部CA管理者へ提出し、SANにFQDNを含むサーバー認証用証明書を依頼する。秘密鍵はWindowsのローカルコンピューター鍵ストアに保持される。CA管理者から証明書を `C:\RAG\tls\rag.cer`、中間CA証明書と信頼配布用ルートCA証明書を別途受け取る。**発行されるまで次へ進まない**。

同じサーバーで、必要な中間CA証明書を「ローカルコンピューター → 中間証明機関」へ登録したうえで実行する。

```powershell
certreq.exe -accept -machine 'C:\RAG\tls\rag.cer'
if ($LASTEXITCODE -ne 0) { throw 'Certificate installation failed' }
Get-ChildItem Cert:\LocalMachine\My |
    Where-Object Subject -eq 'CN=rag.example.internal' |
    Format-List Thumbprint,Subject,DnsNameList,EnhancedKeyUsageList,NotAfter,HasPrivateKey
```

`HasPrivateKey=True`、SANのDNS名、Server Authentication用途、有効期限、信頼チェーンを確認する。[certreqの申請・受領](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/certreq_1)

ルートCA証明書は、組織の管理経路で内容・フィンガープリントを確認してから**サーバーと全クライアント**の信頼されたルート証明機関へ配布する。例は各端末の管理者PowerShell（受領先パスは端末ごとに置換）:

```powershell
Import-Certificate -FilePath 'C:\Temp\org-root-ca.cer' -CertStoreLocation 'Cert:\LocalMachine\Root'
```

ドメイン環境ではGPO配布を利用できる。独自の信頼ストアを使うブラウザーはその設定も確認する。証明書検証を無効にする `curl -k` や警告無視は手順にしない。[Windowsへの証明書インポート](https://learn.microsoft.com/en-us/powershell/module/pki/import-certificate)

### 5.3 HTTPSサイトと認証対象を作る

IISマネージャーで専用アプリケーションプール `LocalLlmRag` を「マネージドコードなし」「ApplicationPoolIdentity」で作成する。サイト `LocalLlmRag` を追加し、物理パスを `C:\RAG\web`、プールを同名プール、バインドを**https / 443 / rag.example.internal / SNI有効**として、前節の証明書を選択する。HTTPバインドは作らない。

管理者PowerShellでIISにサイト設定を読ませる。IISの実行主体にアプリ・DB・環境ファイルへの権限は与えない。

```powershell
icacls.exe 'C:\RAG' /grant 'IIS AppPool\LocalLlmRag:(RX)'
if ($LASTEXITCODE -ne 0) { throw 'IIS traversal grant failed' }
icacls.exe 'C:\RAG\web' /grant:r 'IIS AppPool\LocalLlmRag:(OI)(CI)RX'
if ($LASTEXITCODE -ne 0) { throw 'IIS web grant failed' }
```

利用者は専用サービスアカウントとは別に作る。新規ローカル利用者の例:

```powershell
$ragUserPassword = Read-Host 'raguser のパスワード' -AsSecureString
New-LocalUser -Name 'raguser' -Password $ragUserPassword
Add-LocalGroupMember -SID 'S-1-5-32-545' -Member "$env:COMPUTERNAME\raguser"
Add-LocalGroupMember -Group 'RAGUsers' -Member "$env:COMPUTERNAME\raguser"
```

IISマネージャーの**サイト `LocalLlmRag`** を選び、「Authentication」でAnonymous Authenticationを無効、Windows Authenticationを有効にする。「Authorization Rules」で継承された「すべてのユーザーを許可」を削除し、`サーバー名\RAGUsers` グループだけを許可する。設定例の `YOUR-SERVER` を実際のコンピューター名へ置換する。IIS URL Authorizationでは全ユーザーへのDenyを追加しない（許可したグループまで拒否し得る）。

AD環境ならローカルグループを `DOMAIN\RAGUsers` 等へ置換する。カスタムDNS名でKerberos SSOを必須にする場合はSPN・プールID・ブラウザーの統合認証設定もAD管理者と調整する。本例の非ドメイン端末では通常 `サーバー名\raguser` を対話入力する。組織がNTLMを無効にしている場合は、このローカルアカウント例を使わず、組織の認証方式を設定する。単にVPN内に置くだけではアプリの利用者認証の代わりにならない。[Windows Authentication](https://learn.microsoft.com/en-us/iis/configuration/system.webserver/security/authentication/windowsauthentication/)、[IIS URL Authorization](https://learn.microsoft.com/en-us/iis/manage/configuring-security/understanding-iis-url-authorization)

### 5.4 転送ルール

`C:\RAG\web\web.config` を管理者がエディターで作成・編集する。前節でIISマネージャーが作成した設定がある場合は下の要素を統合し、ファイル全体を上書きしない。`authorization` は前節の許可設定と同じ内容にする。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <security>
      <authorization>
        <clear />
        <add accessType="Allow" roles="YOUR-SERVER\RAGUsers" />
      </authorization>
    </security>
    <rewrite>
      <rules>
        <rule name="RagToStreamlit" stopProcessing="true">
          <match url="(.*)" />
          <serverVariables>
            <set name="HTTP_X_FORWARDED_PROTO" value="https" />
          </serverVariables>
          <action type="Rewrite" url="http://127.0.0.1:8501/{R:1}" appendQueryString="true" />
        </rule>
      </rules>
    </rewrite>
    <webSocket enabled="true" />
  </system.webServer>
</configuration>
```

認証の有効・無効はサイトレベルのIISマネージャーで設定し、ロックされた `authentication` セクションを不用意にweb.configへ追加しない。IISはHTTPS終端と認証を担い、StreamlitはループバックからのHTTP/WSを受ける。認証された利用者情報をアプリの資料ACLへ利用する実装は含まない。

サイトとプールの自動開始を有効にし、World Wide Web Publishing Service（W3SVC）が自動起動することを確認する。専用の新規IISで既定サイトを使わない場合だけ「Default Web Site」を停止する。既存業務サイトを一括停止しない。[IISのHTTPSバインド](https://learn.microsoft.com/en-us/iis/configuration/system.applicationhost/sites/site/bindings/binding)

## 6. Windows Defender Firewall

IISで認証設定を完了してからLAN向けに公開する。管理者PowerShellで実際のネットワークプロファイル・既存ルールを確認し、許可LANを置き換える。

```powershell
Get-NetConnectionProfile
Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction
New-NetFirewallRule -Name 'Local-LLM-RAG-HTTPS' -DisplayName 'Local LLM RAG HTTPS from LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443 -RemoteAddress '192.168.10.0/24' -Profile Domain,Private
```

ルール追加は既存の広いAllowルールを狭めない。IISのインストールで有効になった「World Wide Web Services (HTTPS Traffic-In)」等のルールや、プログラム単位のAllow、GPO配布ルールも `wf.msc` で確認し、このサーバーの公開範囲に合わせる。表示名にポート番号がないルールも確認する。OSファイアウォール自体は無効にしない。[New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)

本アプリ用に公開するのは指定LANからのTCP443のみ。80、8501、11434の外部向けAllowは作らない。8501と11434はループバックbindを維持する。RDPなど既存管理経路のルールを一括削除しない。Publicプロファイルを許可する必要がある環境では、ネットワーク管理者と接続範囲を決めてから変更する。

## 7. 新しい資料を取り込む場合

既存データを移行しないため、この工程は**新規に資料を登録する場合のみ**実行する。空のまま運用するなら省略する。

1. 管理者がサーバーの `C:\RAG\local-llm-rag\source` へ新しい資料を配置する。利用者のPCの同名フォルダーではない。
2. 保守時間を確保し、Streamlitタスクを停止する（第9節）。取り込みの同時実行はしない。
3. 下のIngestタスクを起動する。タスクが完了し、今回の最終実行時刻・最終結果0と取り込みログを確認する。エラーなら公開を再開しない。
4. Streamlitを起動し直し、検索キャッシュを新しいDBに合わせる。

```powershell
Start-ScheduledTask -TaskName 'Local-LLM-RAG-Ingest'
Get-ScheduledTask -TaskName 'Local-LLM-RAG-Ingest'
Get-ScheduledTaskInfo -TaskName 'Local-LLM-RAG-Ingest'
Get-ChildItem 'C:\RAG\logs\ingest-*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Encoding UTF8
```

起動コマンドは非同期なので、直後に取得した以前の終了コード0を今回の成功と誤認しない。`C:\RAG\ops\run-rag.py` によりCLIも常駐アプリと同じ実行アカウント・環境・リポジトリ直下の作業ディレクトリを使う。

全量の差分取り込みは `source` から消えた資料のDBエントリーも削除する。検証のために本番 `source` を一時的に空にして実行しない。利用者へファイル共有やUI取り込みの権限を不用意に渡さない。

## 8. 別クライアントから受け入れ確認

以下は**作成者が実施済みの結果ではなく、配置先で行う確認**である。OS版、GPU/ドライバー、Gitコミット、モデル、実行日時、コマンド結果と画面を記録する。

### 8.1 DNS・ポート・TLS・認証

別のWindowsクライアントから実行する。443は `TcpTestSucceeded=True`、8501と11434はFalseが期待値。サーバー名は実際のFQDNへ置換する。

```powershell
Resolve-DnsName rag.example.internal
Test-NetConnection rag.example.internal -Port 443
Test-NetConnection rag.example.internal -Port 8501
Test-NetConnection rag.example.internal -Port 11434
curl.exe -sS -o NUL -w '%{http_code}\n' https://rag.example.internal/
curl.exe --fail --ntlm --user 'YOUR-SERVER\raguser' -o NUL -w '%{http_code}\n' https://rag.example.internal/
```

curlはPowerShellの別名ではなく `curl.exe` を使う。後者はパスワードを対話入力する。NTLM対応curlがない端末やKerberos必須環境ではブラウザーで確認する。未認証は401、許可した利用者は200を期待する。TLSエラーをHTTPの結果と混同しない。さらにRAGUsersに入っていない有効な別アカウントでは拒否され、画面へ到達しないことを確認する。ドメインの自動ログオンによるテスト混同を避ける。

### 8.2 画面・RAG・再起動

ブラウザーで `https://rag.example.internal/` を開き、証明書警告なし・認証後の画面表示を確認する。開発者ツールのNetworkで `/_stcore/stream` がWebSocketへ切り替わり、再接続を繰り返さないことも見る。ヘルスチェックやHTMLの200だけではRAG成功とは判定しない。

データ移行なしでもRAG経路を検証したい場合は、旧資料ではなく、例えば `source\acceptance.md` に「受け入れ確認用設備の名称は青空試験機。設置場所は北棟の検証室。」という**新しい架空の検証資料**を作る。第7節で取り込み、ブラウザーから設置場所を質問して、期待する回答と `acceptance.md` の出典を確認する。リランカーの有効・無効、画像PDFを扱う場合のOCRも確認する。資料を一切追加しない方針ならこの試験は未実施と記録する。

サーバーを再起動し、**誰もログオンしていない状態**で別クライアントから同じHTTPS認証・画面・RAG確認を行う。OllamaやStreamlitが管理者の対話セッションに依存しないことを確認する。

## 9. 停止・更新・障害時の確認

通常の保守停止はまず利用者へ周知し、取り込みや回答生成が終わったことを確認する。管理者PowerShell:

```powershell
Stop-ScheduledTask -TaskName 'Local-LLM-RAG-Streamlit'
Get-ScheduledTask -TaskName 'Local-LLM-RAG-Streamlit'
Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq 8501
```

タスク停止後に子プロセスが残る場合があるため、8501のlistenerが消えたことを確認してから更新・再起動する。残る場合は `OwningProcess` のPID、実行ファイルのパス・コマンドライン・所有者を調べ、対象のRAGプロセスと確認できたものだけ停止する。`python.exe` や `ollama.exe` を名前だけで一括終了しない。Ollamaの保守も同様にタスク停止後の11434を確認する。

DBのバックアップは新環境でデータを登録した後の運用として別途必要。全取り込み・Streamlitプロセスを停止し、SQLite補助ファイルを含む整合したバックアップを取る。ソース・依存環境・設定の更新前バックアップとコミットを記録し、DB形式変更がある場合はその移行手順も確認する。

```powershell
Set-Location 'C:\RAG\local-llm-rag'
git status --short
git rev-parse HEAD
git pull --ff-only origin master
if ($LASTEXITCODE -ne 0) { throw 'Update failed; do not restart' }
& '.\myvenv313\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency update failed; do not restart' }
Start-ScheduledTask -TaskName 'Local-LLM-RAG-Streamlit'
```

`git status` に意図しない変更がある場合はpull前に止まり、差分を確認する。障害時は記録したコード・依存環境・整合したDBバックアップを組み合わせて戻す。Gitの履歴だけを戻せば必ず復旧するとは限らない。

設定・秘密情報をGitへ追加せず、`git clean -fdx` などGit除外ファイルも消す操作をしない。TLS証明書の期限を監視し、更新時は同じ申請・受領手順で新証明書を配置してIISバインドを切り替え、別端末から再確認する。タスクのパスワード期限、モデル・ログ容量、IISログと `C:\RAG\logs`、同時利用時の応答時間を監視する。

|症状|最初に確認すること|
|---|---|
|タスクが起動しない|最終結果、パスワード、バッチログオン権利、PythonパスとACL|
|起動後に停止する|時間制限、再試行上限、子プロセスの終了コードとログ|
|IIS 500.19 / 500.50|セクションのロック、URL Rewrite/ARR、許可したサーバー変数|
|IIS 502 / 504|8501のlistener、ARR proxy有効、推論時間とタイムアウト|
|認証が繰り返される|RAGUsers所属、アカウント名、NTLM禁止・Kerberos/SPN方針|
|画面は出るが応答しない|WebSocket、Ollamaモデル、HF/OCR取得、DB件数と取り込み結果|

## 公開前チェックリスト

- [ ] 対象Windows Server上でOllamaと実モデルの推論を確認した
- [ ] 既存データを移行せず、空RAGで始めることを合意した
- [ ] 専用標準アカウント・ACL・秘密情報のGit除外を確認した
- [ ] OllamaとStreamlitの常駐、CLIの実行ユーザー・作業場所・環境を揃えた
- [ ] Ollama・リランカー・必要なOCR/VLMモデルを新環境で用意した
- [ ] 内部DNS・証明書SAN・クライアントのCA信頼を一致させた
- [ ] 未認証・非許可ユーザーは拒否し、許可ユーザーだけが利用できた
- [ ] 別クライアントから443だけへ接続でき、8501/11434は遮断できた
- [ ] WebSocketと、資料を登録する場合は回答・出典まで確認した
- [ ] 検索専用利用者へ公開する場合は、取り込みUIの権限制御を実装した
- [ ] 再起動後、未ログオンの状態で同じ確認が成功した
- [ ] 更新・バックアップ・証明書/アカウント期限・ログ監視の担当を決めた
