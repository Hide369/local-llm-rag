# Streamlit RAGをWindows Serverへ配置する

GitHubからアプリケーションをWindows Serverへ配置し、利用者のブラウザーからRAGチャットを使うための構成を示す。対象は現在の`rag_chat_app.py`である。

この文書は**既存の資料原本とベクトルDBを移行しない**前提である。移植先ではRAGのデータは空の状態から始まる。資料を一切配置しないなら、画面は起動できるが、資料に基づく回答はできない。資料を使う運用にする場合は、別途、管理者が移植先の`source\`へ資料を安全に配置して取り込む手順が必要になる。

## 推奨構成

ブラウザーはStreamlitまたはOllamaに直接つながず、Windows Server上のHTTPSリバースプロキシだけを公開する。

```text
利用者のブラウザー
        │ HTTPS :443（認証あり）
        ▼
IIS / 組織のリバースプロキシ
        │ HTTP 127.0.0.1:8501
        ▼
Streamlit（rag_chat_app.py、1プロセス）
        ├── SQLite: vector_store.sqlite3
        └── HTTP 127.0.0.1:11434
                ▼
             Ollama（bge-m3、gpt-oss:20b）
```

公開するポートはリバースプロキシの`443`だけにする。`8501`（Streamlit）と`11434`（Ollama）はサーバー外から到達できないよう、ループバックアドレスへのbindとWindows Defender Firewallの両方で制限する。

Ollamaは`127.0.0.1:11434`で待ち受ける構成とし、`0.0.0.0:11434`では公開しない。ネットワーク公開が必要な場合も、Ollamaを直接公開せず、認証とTLSを担うプロキシを介する。

## 現行実装で把握すべき制約

|項目|現状|Windows Server運用での扱い|
|---|---|---|
|資料原本|`source/`。Git管理外|この移行ではコピーしない。必要になった時点でサーバー管理者が`source\`へ配置する。|
|ベクトルDB|リポジトリ直下の`vector_store.sqlite3`。Git管理外|コピーしない。最初の起動時は空のDBが作られる。|
|Ollama接続先|`OLLAMA_HOST`。未設定時は`http://127.0.0.1:11434`|Streamlitと同じWindows Server上のOllamaを指定する。クライアントには設定しない。|
|認証・権限|アプリ内には未実装|IIS、組織SSO、VPN、リバースプロキシなどで必ず認証する。|
|資料の取り込み|画面のサイドバーからも実行できる|利用者へ公開するなら、取り込みUIを削除・管理者専用にする実装変更が必要。|
|スケールアウト|SQLiteとプロセス内キャッシュを使う|複数プロセス・複数サーバーではなく、まず1プロセスで運用する。|

特に、現在の画面にある「差分を取り込む」は認証済みの全利用者に見える。資料の書き込み権限を利用者へ渡さない方針なら、サーバー公開前にこの操作を削除するか、管理者だけが使える別の運用経路へ分ける。

---

## 初期配置（Windows Server / PowerShellの例）

以下ではアプリを`C:\Apps\local-llm-rag`へ配置する。PowerShellは**管理者として実行**する。

実運用では、Streamlitを日常の管理者アカウントで動かすのではなく、専用のローカルアカウントまたはドメインサービスアカウントで実行することを推奨する。

### 1. 必要なソフトウェアをインストールする

Windows Serverへ次をインストールする。

- Git for Windows
- Python 3.13
- Ollama for Windows
- IIS
- IIS WebSocket Protocol
- IIS URL Rewrite
- IIS Application Request Routing（ARR）

Git、Python、Ollamaが利用できることを確認する。

```powershell
git --version
python --version
ollama --version
```

### 2. アプリケーションを取得する

```powershell
New-Item -ItemType Directory -Path C:\Apps -Force

git clone https://github.com/Hide369/local-llm-rag.git C:\Apps\local-llm-rag

Set-Location C:\Apps\local-llm-rag

python -m venv .venv

.\.venv\Scripts\python.exe -m pip install --upgrade pip

.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

アプリの更新は、同じディレクトリで次を実行する。

```powershell
Set-Location C:\Apps\local-llm-rag

git pull --ff-only

.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

更新後は、後述するStreamlitのタスクを再起動する。

`source\`、`vector_store.sqlite3`、`.env`などGit管理外のファイルは、Git更新によって上書きされないようにする。

---

### 3. Ollamaを同じWindows Serverに配置する

Ollamaをインストールした後、アプリが使う埋め込みモデルと生成モデルを取得する。

```powershell
ollama pull bge-m3
ollama pull gpt-oss:20b
ollama list
```

OllamaのAPIがlocalhostで応答することを確認する。

```powershell
Invoke-WebRequest http://127.0.0.1:11434/api/tags
```

Ollamaを外部公開しない。`OLLAMA_HOST`を設定する場合も、次のようにlocalhostだけにする。

```powershell
[Environment]::SetEnvironmentVariable(
    "OLLAMA_HOST",
    "127.0.0.1:11434",
    "Machine"
)
```

環境変数を変更した場合は、Ollamaを一度完全に終了してから再起動する。

`OLLAMA_HOST=0.0.0.0:11434`のような設定は使用しない。

---

### 4. Streamlit用の環境変数を作成する

環境変数はGitリポジトリへ直接書き込まず、Windows Server側で管理する。

例:

```powershell
[Environment]::SetEnvironmentVariable(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
    "Machine"
)

[Environment]::SetEnvironmentVariable(
    "STREAMLIT_SERVER_COOKIE_SECRET",
    "<十分に長いランダム値>",
    "Machine"
)

[Environment]::SetEnvironmentVariable(
    "STREAMLIT_BROWSER_GATHER_USAGE_STATS",
    "false",
    "Machine"
)
```

Cookie secretはランダムに生成する。PowerShellでは例えば次のように生成できる。

```powershell
$bytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

Colabなど認証付きの外部Ollamaへ接続する場合に限り、`OLLAMA_API_KEY`もサーバー側へ設定する。

APIキーやCookie secretをGit、`config.toml`、起動スクリプトへ直接ハードコードしない。

---

### 5. Streamlitをlocalhostで起動する

まず手動起動で動作確認する。

```powershell
Set-Location C:\Apps\local-llm-rag

.\.venv\Scripts\python.exe -m streamlit run .\rag_chat_app.py `
    --server.address=127.0.0.1 `
    --server.port=8501 `
    --server.headless=true
```

別のPowerShellからヘルスチェックする。

```powershell
Invoke-WebRequest http://127.0.0.1:8501/_stcore/health
```

正常なら`200 OK`が返ることを確認する。

---

### 6. StreamlitをWindows起動時に自動起動する

Windows標準機能だけで構成する場合は、タスク スケジューラを利用する。

起動用スクリプト`C:\Apps\local-llm-rag\run-streamlit.ps1`を作成する。

```powershell
Set-Location C:\Apps\local-llm-rag

& "C:\Apps\local-llm-rag\.venv\Scripts\python.exe" `
    -m streamlit run "C:\Apps\local-llm-rag\rag_chat_app.py" `
    --server.address=127.0.0.1 `
    --server.port=8501 `
    --server.headless=true
```

次にタスクを登録する。

```powershell
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Apps\local-llm-rag\run-streamlit.ps1"'

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "Local-LLM-RAG-Streamlit" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -User "SYSTEM" `
    -RunLevel Highest `
    -Force
```

登録後に起動する。

```powershell
Start-ScheduledTask -TaskName "Local-LLM-RAG-Streamlit"
```

状態を確認する。

```powershell
Get-ScheduledTask -TaskName "Local-LLM-RAG-Streamlit"
Get-ScheduledTaskInfo -TaskName "Local-LLM-RAG-Streamlit"
```

本番環境では`SYSTEM`よりも、アプリ用の専用サービスアカウントで実行する方が望ましい。専用アカウントを使用する場合は、`C:\Apps\local-llm-rag`と必要なファイルだけへアクセス権を付与する。

---

### 7. 資料の初回取り込み

`source\`とDBを移行しないため、この時点で作成されるRAGデータは空である。

サーバー自身のディスクへ資料を配置して初回取り込みを行う場合は、ブラウザーのボタンではなく管理者がPowerShellから実行する。

```powershell
Set-Location C:\Apps\local-llm-rag

.\.venv\Scripts\python.exe -m scripts.ingest_source
```

資料をWindows Serverへ置かず、DBも移行しないなら、このコマンドは実行しない。

---

## Windows Defender Firewall

StreamlitとOllamaはlocalhostで待ち受けることに加え、Windows Defender Firewallでも外部接続を許可しない。

外部公開するのはHTTPSの`443`だけとする。

既存ルールを確認する。

```powershell
Get-NetFirewallRule |
    Where-Object DisplayName -Match "8501|11434|443"
```

HTTPSを許可する例:

```powershell
New-NetFirewallRule `
    -DisplayName "Local LLM RAG HTTPS" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 443 `
    -Action Allow
```

Streamlitの`8501`とOllamaの`11434`について、外部向けAllowルールは作成しない。

明示的にブロックする場合は次のようにする。

```powershell
New-NetFirewallRule `
    -DisplayName "Block Streamlit External Access" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8501 `
    -Action Block

New-NetFirewallRule `
    -DisplayName "Block Ollama External Access" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 11434 `
    -Action Block
```

---

## HTTPS・認証プロキシ（IIS）

Windows ServerではIISをリバースプロキシとして利用する。

概念的な通信経路は次のとおり。

```text
HTTPS :443
   ↓
IIS
   ↓
http://127.0.0.1:8501
   ↓
Streamlit
```

IIS側では少なくとも次を有効にする。

- HTTPSバインド
- TLS証明書
- WebSocket Protocol
- URL Rewrite
- Application Request Routing（ARR）
- Reverse Proxy
- 必要に応じてWindows認証、SSO、VPN、IDプロキシ

### IIS ARRを有効にする

IIS Managerでサーバーを選択し、

`Application Request Routing Cache`  
→ `Server Proxy Settings`  
→ `Enable proxy`

を有効にする。

### URL Rewriteの例

対象サイトの`web.config`に、Streamlitへ転送するルールを設定する。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="ReverseProxyToStreamlit" stopProcessing="true">
          <match url="(.*)" />
          <action
            type="Rewrite"
            url="http://127.0.0.1:8501/{R:1}"
            appendQueryString="true" />
        </rule>
      </rules>
    </rewrite>

    <webSocket enabled="true" />
  </system.webServer>
</configuration>
```

StreamlitはWebSocketを使用するため、IISのWebSocket Protocolを必ず有効にする。

Windows ServerではServer Managerから、

`Add Roles and Features`  
→ `Web Server (IIS)`  
→ `Web Server`  
→ `Application Development`  
→ `WebSocket Protocol`

を有効にする。

---

## IISでHTTPSを設定する

IISサイトへ`https / 443`のバインドを追加し、サーバー証明書を割り当てる。

利用者は例えば次のURLへアクセスする。

```text
https://rag.example.internal/
```

企業内運用では、組織CAが発行した証明書または正式なTLS証明書を使用する。

自己署名証明書を利用する場合は、各クライアントPCで証明書を信頼させる必要があるため、本番用途では組織のPKIを推奨する。

---

## IISで認証する

アプリ自体に利用者認証がないため、公開前にIISまたは上位の認証基盤でアクセス制御する。

Active Directory環境なら、IISのWindows Authenticationを利用する方法がある。

例:

```text
利用者
  ↓
Active Directory認証
  ↓
IIS
  ↓
Streamlit
```

利用可能な認証方式は環境に応じて次から選択する。

- Windows Authentication
- Microsoft Entra ID連携
- 組織SSO
- VPN経由のみ許可
- ID認証付きリバースプロキシ

Streamlitの`8501`へ直接アクセスできる状態では、IIS認証を迂回できるため、`8501`を外部公開しないことが重要である。

---

## Streamlit設定

`C:\Apps\local-llm-rag\.streamlit\config.toml`を作成する。

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

`rag.example.internal`は実際のWindows ServerのFQDNへ置き換える。

Streamlitの非テーマ設定を変更した場合は、Streamlitを再起動する。

```powershell
Stop-ScheduledTask -TaskName "Local-LLM-RAG-Streamlit"
Start-ScheduledTask -TaskName "Local-LLM-RAG-Streamlit"
```

HTTPとHTTPS、または異なるFQDN・ポートを混在させると、CORS/XSRFやWebSocket接続で問題が発生するため、クライアント向けURLを統一する。

---

## Windows側のアクセス権

RAGアプリの配置ディレクトリは、一般利用者から直接変更できないようにする。

例として、AdministratorsとSYSTEMだけにフルコントロールを残す場合:

```powershell
icacls "C:\Apps\local-llm-rag" /inheritance:r
icacls "C:\Apps\local-llm-rag" /grant:r "Administrators:(OI)(CI)F"
icacls "C:\Apps\local-llm-rag" /grant:r "SYSTEM:(OI)(CI)F"
```

専用サービスアカウントを使う場合は、そのアカウントへ必要最小限の`Read/Execute`および、`source\`と`vector_store.sqlite3`へ必要な書き込み権限を与える。

一般のクライアント利用者へ、Windowsファイル共有経由で`source\`や`vector_store.sqlite3`を公開しない。

---

## クライアント側に必要なもの

ブラウザー利用者に必要なのは、認証済みURLへのHTTPSアクセスだけである。

例:

```text
https://rag.example.internal/
```

クライアントPCへ次のものを配置しない。

- Gitリポジトリ
- Python
- Ollama
- LLMモデル
- `OLLAMA_HOST`
- `OLLAMA_API_KEY`
- `source\`
- `vector_store.sqlite3`

つまり、クライアントPCは通常のWebアプリと同じようにブラウザーだけで利用する。

```text
WindowsクライアントPC
      │
      │ HTTPS
      ▼
Windows Server
      ├─ IIS
      ├─ Streamlit
      ├─ Ollama
      ├─ bge-m3
      ├─ gpt-oss:20b
      └─ SQLite
```

現在の構成は「Streamlitがフロントエンド」であり、他のアプリケーションから呼び出すためのRAG APIは実装していない。

別のWebフロントや業務システムをクライアントにする場合は、OllamaやSQLiteを公開せず、Windows Server上に認証・入力検証・レート制限を持つAPI（例: FastAPI）を追加し、そのAPIだけをIIS経由で公開する。

---

## 動作確認

### Ollama

```powershell
Invoke-WebRequest http://127.0.0.1:11434/api/tags
```

### Streamlit

```powershell
Invoke-WebRequest http://127.0.0.1:8501/_stcore/health
```

### Listenポート

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object LocalPort -in 443,8501,11434 |
    Sort-Object LocalPort
```

期待する状態:

```text
443    IIS               外部公開
8501   127.0.0.1のみ     Streamlit
11434  127.0.0.1のみ     Ollama
```

### クライアント

クライアントPCのブラウザーから次を確認する。

```text
https://rag.example.internal/
```

一方、次の直接アクセスはできない状態にする。

```text
http://<Windows ServerのIP>:8501/
http://<Windows ServerのIP>:11434/
```

---

## 公開前チェックリスト

- [ ] Windows ServerへGit、Python、Ollamaをインストールした
- [ ] `origin/master`のコミットをWindows Server上で確認した
- [ ] Python仮想環境`.venv`を作成した
- [ ] `requirements.txt`をインストールした
- [ ] `source\`と`vector_store.sqlite3`を移植しない方針、および空RAGで始まる影響を合意した
- [ ] Ollamaに`bge-m3`と`gpt-oss:20b`を取得した
- [ ] Ollamaは`127.0.0.1:11434`で待ち受けている
- [ ] Streamlitは`127.0.0.1:8501`で待ち受けている
- [ ] Streamlitをタスク スケジューラまたは専用Windowsサービスで自動起動するようにした
- [ ] Windows Defender Firewallで外部公開を`443`だけにした
- [ ] `8501`と`11434`を外部公開していない
- [ ] IISへURL RewriteとARRを導入した
- [ ] IISのWebSocket Protocolを有効にした
- [ ] TLS証明書を設定した
- [ ] IISまたは組織のSSO/VPNで認証を設定した
- [ ] StreamlitのCORS/XSRF保護を有効のままFQDNを設定した
- [ ] 利用者が資料取り込みを実行できないよう、UIまたは運用を分離した
- [ ] OllamaのAPIへlocalhostから接続できることを確認した
- [ ] Streamlitのヘルスチェックが成功した
- [ ] クライアントからHTTPS経由でアクセスできることを確認した
- [ ] クライアントから`8501`と`11434`へ直接接続できないことを確認した

## 参考資料

- Streamlit: configuration options
- Streamlit: remote access troubleshooting
- Ollama FAQ: server and network exposure
- Microsoft IIS: WebSocket Protocol
- Microsoft IIS: URL Rewrite
- Microsoft IIS: Application Request Routing
