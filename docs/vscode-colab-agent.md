# VS CodeでColabのgpt-oss:20bを使う

Google ColabのL4上で動くOllamaを推論に使い、ファイル編集とコマンド実行をWindows側のCodex拡張で行う。通常のVS Code/Codex設定には触れず、専用ウィンドウと専用設定を使う。

## 前提

- `colab/run_ollama_server.ipynb` をL4ランタイムで上から順に実行している
- ノートブックが表示した最新の `OLLAMA_HOST` と `OLLAMA_API_KEY` をプロジェクト直下の `.env` に設定している
- VS CodeとOpenAI Codex拡張がWindowsへインストール済みである
- コーディング中は、VRAM測定条件をそろえるためVLMやRAG取り込みを同時実行しない

モデルへ送った指示、コード断片、ツール結果はColabへ転送される。`.env` と生成したCodex設定にAPIキー自体は書き込まず、専用VS Codeプロセスの環境変数として渡す。

## 初回セットアップ

プロジェクト直下のPowerShellで次を順に実行する。

```powershell
# URL・認証・モデル機能を確認する。推論は行わない
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --check

# 元モデルをバックアップして、64kコンテキストを設定する
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context

# 64kの実配置とResponses APIのツール往復を実測する
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe

# 専用Codex設定とSuperpowersスキルを準備する
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup
```

別のプロジェクトを開く場合も、このリポジトリの仮想環境と起動補助を使える。対象プロジェクト直下にColabの接続値を書いた`.env`を置き、`--project`へそのフォルダを渡す。対象ごとにCodexの設定とSuperpowersのスキル参照は分離される。

```powershell
$agentRoot = 'C:\path\to\local_llm'
$targetProject = 'C:\path\to\another-project'
Push-Location $agentRoot
try {
    .\myvenv313\Scripts\python.exe -m scripts.coding_agent --project $targetProject
} finally {
    Pop-Location
}
```

`--probe`がCPU配置を報告した場合は32kへ下げ、再測定する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context --context-size 32768
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe --context-size 32768
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup --context-size 32768
```

`local_llm`自身を開く場合のセットアップ先は `%LOCALAPPDATA%\local-llm\coding-agent\` である。外部プロジェクトでは、その配下のプロジェクト固有フォルダを使う。Superpowers 6.3.0を版ごとにコピーし、対象プロジェクトの `.agents\skills` 直下から14個のスキルを参照する。既存の同名ファイルや同じ対象プロジェクト用ではない設定がある場合は上書きせず終了する。

## Playwright MCPを追加する

PlaywrightはCodexプラグインとしてではなく、CodexのMCPサーバーとして追加する。このため、設定済みの`features.plugins = false`は変更しない。ブラウザーとMCPサーバーはWindowsで動き、Colabは`gpt-oss:20b`の推論だけを担当する。

まず、対象プロジェクト用のCodex実行環境を作成する。すでにセットアップ済みなら、この手順は不要である。

```powershell
# local_llm自身を対象にする場合
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup

# 別のプロジェクトを対象にする場合
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup --project 'C:\path\to\project'
```

コマンド出力の`codex_home`に表示されるフォルダを開き、そこにある`config.toml`を編集する。専用のVS Codeウィンドウが起動中なら、先に閉じる。`# END LOCAL_LLM_MANAGED_CONFIG`より**後**に次を追記する。管理対象の範囲内を編集すると、次回の`--setup`で設定が置き換わる。

```toml
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--caps=testing"]
startup_timeout_sec = 30
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

`npx`の実行にはNode.js 20以降が必要である。PowerShellを開き直してから、次の両方が動くことを確認する。

```powershell
node --version
npx --version
```

設定を保存したら、通常どおりエージェントを起動する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent
```

VS CodeのCodexチャットで`/mcp`を実行し、`playwright`が接続済みであることを確認する。ローカル開発サーバーを起動したうえで、最初は変更を行わない小さな確認を依頼する。

```text
$using-superpowers を使って、http://127.0.0.1:3000 を開き、
見出しが表示されることを確認してください。変更は加えないでください。
```

`--caps=testing`は、ページ検証用のPlaywrightツールを追加する。`gpt-oss:20b`で最初の接続確認が不安定な場合は、`args`を次のように短くして、ページを開く・スナップショットを取得する操作から確認する。

```toml
args = ["-y", "@playwright/mcp@latest"]
```

初回起動時は`npx`がMCPパッケージと必要なブラウザーを取得するため、Windows側のネットワーク接続が必要になる。Playwright MCPは既定で表示可能なブラウザーを開く。ログイン済みの情報を使わせたくない場合は、ブラウザーでログインしないか、MCPの`--isolated`オプションを追加して一時プロファイルを使う。

停止するときは同じ設定に`enabled = false`を追加してVS Codeの専用ウィンドウを再起動する。`# END LOCAL_LLM_MANAGED_CONFIG`より後の追記部分は、その後に`--setup`を実行しても保持される。

## 起動と操作

Colab用の専用VS Codeを開く。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent
```

表示されたウィンドウのCodexサイドバーで依頼する。最初は次のような小さい依頼で、読取・編集・テストまで確認する。

```text
$using-superpowers を使って、このプロジェクトのテストを1件選び、
実装の目的を説明してから、そのテストだけを実行してください。ファイルは変更しないでください。
```

スキル名を明示したい場合は `$brainstorming`、`$writing-plans`、`$test-driven-development`、`$systematic-debugging`、`$verification-before-completion` のように入力する。Codex拡張はプラグインそのものを読み込まず、プロジェクトに置いた単体スキルを検出する。

## Colabへ再接続する

Colabランタイムやngrokトンネルを作り直すとURLとAPIキーが変わる。

1. ノートブックを上から順に再実行する。
2. `.env` の2値を新しい値へ更新する。
3. 以前のColab専用VS Codeウィンドウを閉じる。
4. `--check`を実行してから、既定コマンドで開き直す。

実行中のVS Codeプロセスは更新後の環境変数を受け取れないため、ウィンドウの再起動が必要である。

## 停止と復元

作業を止めるときは専用VS Codeウィンドウを閉じ、Colabランタイムまたはノートブックのサーバープロセスを停止する。起動補助は通常のVS Code設定や通常のCodex設定を変更しない。

`--configure-context`の初回実行は、変更前のモデルを `gpt-oss:20b-before-coding-agent` として保存する。元のモデル設定へ戻す場合は、Colab接続中に次を実行する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --restore-context
```

接続情報は通常どおり `.env` から読む。バックアップタグは自動削除しない。

## 制限

- Colabランタイムが停止すると新しい推論はできない。未保存のローカル編集はVS Code側に残る。
- 長時間の自律開発や複雑な変更の成功はモデル能力にも左右される。変更内容とテスト結果を毎回確認する。
- 64kがL4のVRAMへ全量配置できない場合は32kを使う。会話が長くなるほど早く自動圧縮される。
- 推論用のツール呼び出しはWindows側で実行されるため、Codexの`workspace-write`と`on-request`の承認設定が適用される。
- OllamaのResponses APIはCodexのfreeform `apply_patch`ツール形式に対応しない。この専用環境は同ツールを公開せず、CodexにPowerShellで小さく編集させる。
- SSEが一時的に切断された場合、重複したツール実行を避けるためストリームを自動再試行しない。ローカルの変更を確認してから依頼を再送する。
- `gpt-oss:20b`は20Bモデルであり、テストコマンドを具体的に指定した方が安定する。受け入れ試験ではSuperpowers読取、Pythonファイル編集、指定pytestの`1 passed`まで確認した。
