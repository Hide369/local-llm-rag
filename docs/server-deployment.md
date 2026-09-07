# Streamlit RAGをサーバーへ配置する

GitHubからアプリケーションを別環境へ配置し、利用者のブラウザーからRAGチャットを使うための構成を示す。対象は現在の`rag_chat_app.py`である。

この文書は**既存の資料原本とベクトルDBを移行しない**前提である。移植先ではRAGのデータは空の状態から始まる。資料を一切配置しないなら、画面は起動できるが、資料に基づく回答はできない。資料を使う運用にする場合は、別途、管理者が移植先の`source/`へ資料を安全に配置して取り込む手順が必要になる。

## 推奨構成

ブラウザーはStreamlitまたはOllamaに直接つながず、HTTPSのリバースプロキシだけを公開する。

```text
利用者のブラウザー
        │ HTTPS :443（認証あり）
        ▼
Nginx / 組織のリバースプロキシ
        │ HTTP 127.0.0.1:8501
        ▼
Streamlit（rag_chat_app.py、1プロセス）
        ├── SQLite: vector_store.sqlite3
        └── HTTP 127.0.0.1:11434
                ▼
             Ollama（bge-m3、gpt-oss:20b）
```

公開するポートはリバースプロキシの`443`だけにする。`8501`（Streamlit）と`11434`（Ollama）はサーバー外から到達できないよう、ループバックアドレスへのbindとファイアウォールの両方で制限する。Ollamaは既定で`127.0.0.1:11434`へbindする。ネットワーク公開が必要な場合も、Ollamaを直接公開せず、認証とTLSを担うプロキシを介する。

## 現行実装で把握すべき制約

|項目|現状|サーバー運用での扱い|
|---|---|---|
|資料原本|`source/`。Git管理外|この移行ではコピーしない。必要になった時点でサーバー管理者が配置する。|
|ベクトルDB|リポジトリ直下の`vector_store.sqlite3`。Git管理外|コピーしない。最初の起動時は空のDBが作られる。|
|Ollama接続先|`OLLAMA_HOST`。未設定時は`http://127.0.0.1:11434`|Streamlitと同じサーバー上のOllamaを指定する。クライアントには設定しない。|
|認証・権限|アプリ内には未実装|プロキシまたは組織のSSOで必ず認証する。|
|資料の取り込み|画面のサイドバーからも実行できる|利用者へ公開するなら、取り込みUIを削除・管理者専用にする実装変更が必要。|
|スケールアウト|SQLiteとプロセス内キャッシュを使う|複数レプリカではなく、まず1プロセスで運用する。|

特に、現在の画面にある「差分を取り込む」は認証済みの全利用者に見える。資料の書き込み権限を利用者へ渡さない方針なら、サーバー公開前にこの操作を削除するか、管理者だけが使える別の運用経路へ分ける。

## 初期配置（Linux / systemdの例）

以下ではアプリを`/opt/local-llm-rag`、実行用ユーザーを`rag`とする。パスとドメイン名は環境に合わせて置き換える。

### 1. アプリケーションを取得する

```bash
sudo useradd --system --create-home --home-dir /opt/local-llm-rag --shell /usr/sbin/nologin rag
sudo -u rag git clone https://github.com/Hide369/local-llm-rag.git /opt/local-llm-rag
sudo -u rag python3.13 -m venv /opt/local-llm-rag/.venv
sudo -u rag /opt/local-llm-rag/.venv/bin/python -m pip install -r /opt/local-llm-rag/requirements.txt
```

アプリの更新は、同じディレクトリで`git pull --ff-only`を実行し、後述のサービスを再起動する。`source/`、`vector_store.sqlite3`、`.env`はGit管理外なので、Gitの更新で上書きされない。

### 2. Ollamaを同じサーバーに配置する

Ollamaをインストールして、アプリが使う埋め込みモデルと生成モデルを取得する。

```bash
ollama pull bge-m3
ollama pull gpt-oss:20b
ollama list
```

Ollamaは`127.0.0.1:11434`のままにする。`OLLAMA_HOST=0.0.0.0:11434`のような設定で直接公開しない。WindowsでOllamaをサービス運用する場合は、環境変数を変更した後にOllamaを終了・再起動して反映する。

### 3. 実行環境変数を置く

`/etc/local-llm-rag/rag.env`を作り、所有者をroot、読み取りを`rag`だけにする。APIキーを使わないローカルOllama構成でも、Streamlitのcookie secretは必ずランダムな値にする。

```ini
OLLAMA_HOST=http://127.0.0.1:11434
STREAMLIT_SERVER_COOKIE_SECRET=<十分に長いランダム値>
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

Colabなど認証付きの外部Ollamaへ接続する場合に限り、`OLLAMA_API_KEY`をこのファイルに追加する。値をGit、`.streamlit/config.toml`、サービス定義へ直接書かない。

### 4. Streamlitをlocalhostで起動する

`/etc/systemd/system/local-llm-rag.service`の例:

```ini
[Unit]
Description=local-llm-rag Streamlit application
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User=rag
Group=rag
WorkingDirectory=/opt/local-llm-rag
EnvironmentFile=/etc/local-llm-rag/rag.env
ExecStart=/opt/local-llm-rag/.venv/bin/python -m streamlit run rag_chat_app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now local-llm-rag
sudo systemctl status local-llm-rag
curl --fail http://127.0.0.1:8501/_stcore/health
```

`source/`とDBを移行しないため、この時点で作られるDBは空である。サーバー自身のディスクに資料を配置して初回取り込みを行う場合は、ブラウザーのボタンではなく管理者が次を実行する。

```bash
sudo -u rag /opt/local-llm-rag/.venv/bin/python -m scripts.ingest_source
```

資料をサーバーに置かず、かつDBも移行しないなら、このコマンドは実行しない。空のRAGであることを利用者へ明示する。

## HTTPS・認証プロキシ

Nginxの最小例である。TLS証明書と`auth_basic`は組織のSSO、VPN、IDプロキシなどに置き換えてよい。重要なのは、Streamlitへ直接到達できず、WebSocketのUpgradeヘッダーをプロキシが保持することである。

```nginx
server {
    listen 443 ssl http2;
    server_name rag.example.internal;

    ssl_certificate     /etc/letsencrypt/live/rag.example.internal/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rag.example.internal/privkey.pem;

    # SSO/VPNを使わない場合の最低限の認証例
    auth_basic "RAG";
    auth_basic_user_file /etc/nginx/.htpasswd-rag;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
    }
}
```

Streamlit側のCORS・XSRF保護は無効にしない。サーバー名が固定なら、`.streamlit/config.toml`（Gitには秘密を書かない）に許可するホストとオリジンを設定する。

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

このファイルの非テーマ設定を変更した場合は、Streamlitの再起動が必要である。`rag.example.internal`、証明書のパス、許可オリジンは実際のFQDNへ統一する。HTTPとHTTPS、または異なるポートを混在させるとCORS/XSRFやWebSocketの接続に失敗する。

## クライアント側に必要なもの

ブラウザー利用者に必要なのは、認証済みのURL（例: `https://rag.example.internal/`）へのHTTPSアクセスだけである。クライアントPCへ次のものを配置しない。

- Gitリポジトリ、Python、Ollama、モデル
- `OLLAMA_HOST`や`OLLAMA_API_KEY`
- `source/`、`vector_store.sqlite3`

現在の構成は「Streamlitがフロントエンド」であり、他のアプリケーションから呼ぶためのRAG APIは実装していない。別のWebフロントや業務システムをクライアントにする場合は、OllamaやSQLiteを公開せず、サーバー上に認証・入力検証・レート制限を持つAPI（例: FastAPI）を追加し、そのAPIだけをプロキシで公開する。

## 公開前チェックリスト

- [ ] `origin/master`のコミットをサーバーで確認した
- [ ] `source/`と`vector_store.sqlite3`を移植しない方針、および空RAGで始まる影響を合意した
- [ ] Ollamaに`bge-m3`と`gpt-oss:20b`を取得した
- [ ] Streamlitは`127.0.0.1:8501`、Ollamaは`127.0.0.1:11434`だけで待ち受けている
- [ ] ファイアウォールで外部公開を`443`だけにした
- [ ] TLSと認証（SSO/VPNまたは同等の仕組み）を設定した
- [ ] StreamlitのCORS/XSRF保護を有効のままFQDNを設定した
- [ ] 利用者が取り込みを実行できないよう、UIまたは運用を分離した
- [ ] `curl --fail http://127.0.0.1:8501/_stcore/health`と、認証済みブラウザーアクセスを確認した

## 参考資料

- [Streamlit: configuration options](https://docs.streamlit.io/develop/concepts/configuration/options)
- [Streamlit: remote access troubleshooting](https://docs.streamlit.io/knowledge-base/deploy/remote-start)
- [Ollama FAQ: server and network exposure](https://docs.ollama.com/faq)
