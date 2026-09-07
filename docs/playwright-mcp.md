# Playwright MCPの設定

Windows上のCodexからPlaywright MCPを使い、ローカルのWebアプリを検証するための設定手順を示す。Colabは`gpt-oss:20b`の推論だけを担当し、ブラウザーとMCPサーバーはWindowsで動作する。

PlaywrightはCodexプラグインではなくMCPサーバーとして追加する。そのため、`features.plugins = false`は変更しない。

## 前提

- [VS CodeでColabのgpt-oss:20bを使う](vscode-colab-agent.md) の初回セットアップを完了している
- WindowsにNode.js 20以降をインストールしている

PowerShellを開き直して、Node.jsと`npx`が利用できることを確認する。

```powershell
node --version
npx --version
```

## MCPサーバーを追加する

対象プロジェクト用のCodex実行環境を作成する。すでにセットアップ済みなら、この手順は不要である。

```powershell
# local_llm自身を対象にする場合
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup

# 別のプロジェクトを対象にする場合
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup --project 'C:\path\to\project'
```

コマンド出力の`codex_home`に表示されたフォルダーの`config.toml`を編集する。専用のVS Codeウィンドウが起動中なら、先に閉じる。`# END LOCAL_LLM_MANAGED_CONFIG`より**後**に次を追記する。管理対象範囲を編集すると、次の`--setup`で設定が置き換わる。

```toml
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--caps=testing"]
startup_timeout_sec = 30
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

## 接続を確認する

設定を保存したら、専用のCodexを起動する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent
```

VS CodeのCodexチャットで`/mcp`を実行し、`playwright`が接続済みであることを確認する。ローカル開発サーバーを起動したうえで、まずは変更を加えない確認を依頼する。

```text
$using-superpowers を使って、http://127.0.0.1:3000 を開き、
見出しが表示されることを確認してください。変更は加えないでください。
```

## トラブルシューティングと運用

`--caps=testing`はページ検証用のPlaywrightツールを追加する。`gpt-oss:20b`で最初の接続確認が不安定な場合は、`args`を次のように短くし、ページを開く・スナップショットを取得する操作から確認する。

```toml
args = ["-y", "@playwright/mcp@latest"]
```

初回起動時は`npx`がMCPパッケージと必要なブラウザーを取得するため、Windows側のネットワーク接続が必要になる。Playwright MCPは既定で表示可能なブラウザーを開く。ログイン済みの情報を使わせたくない場合は、ブラウザーでログインしないか、MCPの`--isolated`オプションを追加して一時プロファイルを使う。

停止するときは同じ設定に`enabled = false`を追加して、専用のVS Codeウィンドウを再起動する。`# END LOCAL_LLM_MANAGED_CONFIG`より後の追記部分は、その後に`--setup`を実行しても保持される。
