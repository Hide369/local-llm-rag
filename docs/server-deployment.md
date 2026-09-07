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

サーバーの管理者が次を実行し、`/etc/local-llm-rag/rag.env`を作る。親ディレクトリは`root:rag`・`0750`、ファイルは`root:rag`・`0640`にして、rootと実行グループだけが読めるようにする。APIキーを使わないローカルOllama構成でも、Streamlitのcookie secretは必ずランダムな値にする。

```bash
sudo install -d -o root -g rag -m 0750 /etc/local-llm-rag
sudoedit /etc/local-llm-rag/rag.env
sudo chown root:rag /etc/local-llm-rag/rag.env
sudo chmod 0640 /etc/local-llm-rag/rag.env
```

エディターには次の内容を設定する。既存ファイルの場合は必要な値だけ更新する。

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

### 5. 管理者が資料を取り込む場合

資料をサーバーに置かず、かつDBも移行しないなら、この節は実行しない。空のRAGであることを利用者へ明示する。

サーバーの`/opt/local-llm-rag/source/`へ資料を配置し、`rag`ユーザーが読めることを確認する。CLIの`-m scripts.ingest_source`はリポジトリを実行ディレクトリにする必要がある。また、手動の`sudo -u rag python ...`にはStreamlitサービスの`EnvironmentFile`が適用されない。

そこで、`sudoedit /etc/systemd/system/local-llm-rag-ingest.service`で次の単発サービスを作る。`User`・`Group`・`WorkingDirectory`・`EnvironmentFile`はStreamlitと同じ値を使う。これにより、ローカルOllamaだけでなく、`rag.env`に設定した外部Ollamaの接続先・APIキーも取り込み時に読み込まれる。

```ini
[Unit]
Description=local-llm-rag document ingestion
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=oneshot
User=rag
Group=rag
WorkingDirectory=/opt/local-llm-rag
EnvironmentFile=/etc/local-llm-rag/rag.env
ExecStart=/opt/local-llm-rag/.venv/bin/python -u -m scripts.ingest_source
TimeoutStartSec=infinity
NoNewPrivileges=true
PrivateTmp=true
```

管理者は、サーバー上のどのディレクトリからでも次を実行できる。

```bash
sudo systemctl daemon-reload
sudo systemctl start local-llm-rag-ingest.service
sudo systemctl show local-llm-rag-ingest.service -p Result -p ExecMainStatus
sudo journalctl -u local-llm-rag-ingest.service -b -n 100 --no-pager
```

`start`は取り込み完了まで待つ。`Result=success`・`ExecMainStatus=0`とログの取り込み結果を確認する。正常終了後に`inactive (dead)`になるのは`Type=oneshot`の通常の動作である。再取り込みは同じ`start`で実行する。起動時の自動取り込みは不要なので`enable`は行わない。

接続設定は`rag.env`で管理する。変更は次の取り込み実行に反映されるが、Streamlitには`sudo systemctl restart local-llm-rag`が必要である。CLIが別の値を拾わないよう、リポジトリの`.env`に以前の接続設定を重複して残さない。環境変数ファイルの読み込みと実行場所は[systemdの実行環境設定](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml)に従う。

## HTTPS・認証プロキシ

以下はOpenSSL 3系を提供するUbuntu/Debian系のNginxパッケージを使う例で、masterプロセスはroot、workerは`www-data`、設定は`sites-available`／`sites-enabled`で管理する。他のディストリビューションでは、workerのグループ名と設定の読み込み先を合わせる。

### 1. Nginxと名前解決を準備する

サーバー上で必要なパッケージを用意する。

```bash
sudo apt-get update
sudo apt-get install nginx apache2-utils openssl ca-certificates curl
openssl version
```

以下の`rag.example.internal`は内部DNS名の例である。サーバーとクライアントの両方でこの名前がサーバーのLAN IPへ解決されるよう、内部DNSに登録する。DNS名は証明書のSAN、Nginx、Streamlit、ブラウザーのURLで統一する。

この経路では**組織の内部CAでサーバー証明書を発行できること**が前提になる。`.internal`にはLet's Encryptの証明書を発行できない。内部CAがない場合は、所有する公開ドメインの名前へ置き換え、DNS-01による発行を使う。DNS-01は公開DNSのTXTレコードで検証するため、Webサーバー自体はLAN内に配置できる。内部DNS名の制約は[証明書ポリシー](https://letsencrypt.org/documents/isrg-cp-v3.1/)、DNS-01の条件は[Let's Encryptの認証方式](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)を参照する。

### 2. 内部CAへ証明書を申請し、サーバーへ配置する

以下は初回の鍵作成である。サーバー上で実行する。既存の鍵がある場合は再生成せず、その鍵を使う更新手順をCA管理者と確認する。

```bash
sudo install -d -o root -g root -m 0700 /etc/nginx/tls/rag
sudo test ! -e /etc/nginx/tls/rag/privkey.pem && \
sudo openssl req -new -newkey rsa:3072 -noenc \
  -keyout /etc/nginx/tls/rag/privkey.pem \
  -out /etc/nginx/tls/rag/server.csr \
  -subj '/CN=rag.example.internal' \
  -addext 'subjectAltName=DNS:rag.example.internal'
sudo chmod 0600 /etc/nginx/tls/rag/privkey.pem
```

`server.csr`だけを組織所定の申請経路でCA管理者へ渡す。秘密鍵はサーバーに保持する。CSRの作成方法は[OpenSSLの公式手順](https://docs.openssl.org/3.0/man1/openssl-req/)を参照する。

CA管理者から、SANに実際のDNS名を含みサーバー認証用途で発行された証明書と必要な中間証明書、信頼配布用のルートCA証明書を受け取る。`fullchain.pem`は「サーバー証明書→中間証明書」の順にPEMを連結したものとし、ルートCA証明書は別にする。以下では受領ファイルをサーバーの`/var/tmp/rag-fullchain.pem`と`/var/tmp/org-root-ca.crt`へ配置済みとする。発行・受領までは次の設定へ進まない。

```bash
sudo install -o root -g root -m 0644 /var/tmp/rag-fullchain.pem /etc/nginx/tls/rag/fullchain.pem
sudo openssl x509 -in /etc/nginx/tls/rag/fullchain.pem -noout -subject -issuer -dates -ext subjectAltName
```

表示されたDNS名と有効期限を確認する。秘密鍵はrootのみ読み取り可能にし、証明書チェーンとの鍵の一致は後述の`nginx -t`でも検査する。[Nginxの証明書・秘密鍵の配置条件](https://nginx.org/en/docs/http/configuring_https_servers.html)に従う。

ルートCA証明書は組織の管理経路で各クライアントOS／ブラウザーの信頼ストアへ配布する。Windows端末では通常は管理ポリシーで「信頼されたルート証明機関」へ配布する。Ubuntu/Debian端末および疎通確認に使うサーバーでは、受領したルートCA証明書について次を実行できる。

```bash
sudo install -o root -g root -m 0644 /var/tmp/org-root-ca.crt /usr/local/share/ca-certificates/local-llm-rag-root.crt
sudo update-ca-certificates
```

クライアントにも同じCA証明書を事前配布し、その端末上の受領パスに合わせて実行する。証明書検証を無効化する`curl -k`やブラウザーの警告無視を運用手順にはしない。公開CAを使う場合は、そのACMEクライアントが管理する証明書パスへNginx設定を合わせ、自動更新と更新後のreloadも設定する。

### 3. Basic認証の利用者を登録する

この例ではHTTPS上のBasic認証を使う。組織のSSO／IDプロキシを使う場合はこの認証部分を置き換える。VPNだけを使う場合も、利用者をどう認証するかを別途決める。

サーバー上で次を実行する。`raguser`は登録する利用者名へ置き換える。パスワードは対話入力する。

```bash
if ! sudo test -e /etc/nginx/.htpasswd-rag; then
    sudo install -o root -g www-data -m 0640 /dev/null /etc/nginx/.htpasswd-rag
fi
sudo htpasswd -B /etc/nginx/.htpasswd-rag raguser
sudo chown root:www-data /etc/nginx/.htpasswd-rag
sudo chmod 0640 /etc/nginx/.htpasswd-rag
```

利用者の追加・パスワード更新も同じ`htpasswd -B`で行う。`-c`は既存ファイルを作り直して他の利用者を消すため付けない。Nginx workerが読めることを`sudo -u www-data test -r /etc/nginx/.htpasswd-rag`で確認する。[htpasswdのオプション](https://httpd.apache.org/docs/current/programs/htpasswd.html)を参照する。

### 4. NginxとStreamlitの設定を保存する

`sudoedit /etc/nginx/sites-available/local-llm-rag`で以下を保存する。WebSocketのUpgradeヘッダーを転送する設定も含む。

```nginx
server {
    listen 443 ssl;
    server_name rag.example.internal;

    ssl_certificate     /etc/nginx/tls/rag/fullchain.pem;
    ssl_certificate_key /etc/nginx/tls/rag/privkey.pem;

    # 上の手順で作成した利用者ファイルを参照する
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

Streamlit側のCORS・XSRF保護は無効にしない。サーバー上で次を実行し、`/opt/local-llm-rag/.streamlit/config.toml`に以下のTOMLを保存する。既存設定があれば該当するキーを更新し、秘密情報は書き込まない。

```bash
sudo -u rag mkdir -p /opt/local-llm-rag/.streamlit
sudoedit /opt/local-llm-rag/.streamlit/config.toml
sudo chown rag:rag /opt/local-llm-rag/.streamlit/config.toml
sudo chmod 0640 /opt/local-llm-rag/.streamlit/config.toml
```

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

### 5. 設定を有効化して確認する

Nginxの`/etc/nginx/nginx.conf`が`/etc/nginx/sites-enabled/*`を読み込む構成であることを確認し、サーバー上で次を実行する。同名の有効化先がある場合は、既存リンクの行き先を確認してから更新する。

```bash
sudo ln -s /etc/nginx/sites-available/local-llm-rag /etc/nginx/sites-enabled/local-llm-rag
sudo nginx -t
```

`syntax is ok`・`test is successful`を確認できた場合だけ次へ進む。証明書の読み込みや秘密鍵との不一致などのエラーがあれば、設定を修正して`nginx -t`を再実行する。認証ファイルの読み取りは前節の`test -r`でも確認する。`nginx -t`の検査範囲は[Nginxの公式説明](https://nginx.org/en/docs/switches.html)を参照する。

```bash
sudo systemctl restart local-llm-rag
sudo systemctl enable --now nginx
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager
```

別のクライアント端末から、DNSとCAの信頼設定を反映したうえで実行する。未認証時は`401`、登録済み利用者では`200`が期待値である。2つ目のコマンドはパスワードを対話入力する（Windows PowerShellでは`curl.exe`を使う）。

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://rag.example.internal/
curl --fail --user raguser -o /dev/null -w '%{http_code}\n' https://rag.example.internal/
```

Windowsでは`-o /dev/null`も`-o NUL`へ置き換える。続いてブラウザーで同じURLを開き、認証後にStreamlit画面が表示されることを確認する。この確認はTLSと認証の確認であり、RAG応答の成立を保証するものではない。証明書の更新時も`nginx -t`の成功後にreloadし、期限と接続を再確認する。

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
