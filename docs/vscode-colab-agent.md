# VS CodeでColabのgpt-oss:20bを使う

Google ColabのL4上で動くOllamaを推論に使い、ファイル編集とコマンド実行をWindows側のCodex拡張で行う。通常のVS Code/Codex設定には触れず、専用ウィンドウと専用設定を使う。

> 社内LANのGB10（DGX Spark）に置いたOllamaへ繋ぎ、`gpt-oss:120b` を使う手順は
> [GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md) にある。
> 起動補助は同じもので、接続先・モデル・コンテキスト長が違うだけである。

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

## コンテキスト長を選ぶ

`--context-size` に渡せるのは **32768 / 65536 / 131072** の3つだけである
（`coding_agent/connection.py` の `SUPPORTED_CONTEXT_SIZES`）。自由入力にしていない
のは、打ち間違いを `--probe` の失敗まで持ち越さないためである。Ollamaは大きすぎる
値でも例外を出さず、モデルの一部を黙ってCPUへ落とすだけなので、気づくのが遅れる。

|値|想定|
|---|---|
|32768|`--probe` がCPU配置を報告したときの退避先|
|65536|**既定。** ColabのL4（24GB）で実配置を確認した値|
|131072|128GB級のユニファイドメモリを持つ機械（GB10/DGX Spark など）向け。**L4では確実に溢れる**|

**どの機械でも通る値ではない。実際に載るかどうかは `--probe` が確かめる。**
数字を大きくしただけで読める量が増えるわけではなく、`--configure-context` で
Ollama側に焼き、`--probe` で全層がGPUに載っていることを確認して、はじめて効く。

`--probe`がCPU配置を報告した場合は1段下げて測り直す。次に試す値はエラーメッセージが
名指しする（131072で溢れたなら65536、65536で溢れたなら32768）。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context --context-size 32768
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe --context-size 32768
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup --context-size 32768
```

一番小さい32768でも溢れた場合、下げる先はもう無い。モデルを小さくするか、同じGPUを
使う他の処理（VLM、RAGの取り込み）を止める。

`local_llm`自身を開く場合のセットアップ先は `%LOCALAPPDATA%\local-llm\coding-agent\` である。外部プロジェクトでは、その配下のプロジェクト固有フォルダを使う。Superpowers 6.3.0を版ごとにコピーし、対象プロジェクトの `.agents\skills` 直下から14個のスキルを参照する。既存の同名ファイルや同じ対象プロジェクト用ではない設定がある場合は上書きせず終了する。

## Playwright MCPを使う

Playwright MCPの設定、接続確認、トラブルシューティングは[Playwright MCPの設定](playwright-mcp.md)にまとめている。

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
