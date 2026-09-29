# Superpowers プラグイン導入手順（GB10 ローカルLLM + VS Code Claude Code）

GB10サーバー上のローカルLLM（gpt-oss-120b）に、VS Code拡張の Claude Code から接続している環境で、プラグイン「Superpowers」を使うための手順と注意点をまとめる。

## 1. インストール

Claude Code のチャット欄で次のコマンドを実行する。

公式マーケットプレイスから入れる場合:

```
/plugin install superpowers@claude-plugins-official
```

作者のマーケットプレイスから入れる場合（入るプラグインは同じ）:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### うまくいかない場合

- `/plugin` が認識されない → Claude Code を最新版に更新し、セッションを再起動する。
- VS Code拡張から `/plugin` が動かない → VS Codeのターミナルで `claude` を起動し、CLIからインストールする。設定（`~/.claude`）は拡張と共通なので、CLIで入れたプラグインは拡張からも使える。

### 導入の確認

`/plugin` を実行し、一覧に superpowers が有効として表示されていれば完了。

## 2. ローカルLLM構成での注意点

| 項目 | 内容 |
|---|---|
| GitHubへの到達性 | インストール時にGitHubからプラグインを取得する。クライアントが閉域網にある場合は、`obra/superpowers` を別の端末でcloneして持ち込み、ローカルパスから読み込む。 |
| コンテキスト長 | using-superpowers の指示がSessionStartフックで毎回注入される。vLLM等の `max-model-len` が小さいとコンテキストを圧迫する。 |
| ツール呼び出し精度 | Superpowersはモデルが自分でSkill読み込みやサブエージェント起動を行う前提で作られている。プロンプトもClaude向けのため、gpt-oss-120bではスキルが発動しない、手順を飛ばすといったことが起こり得る。 |

## 3. CLAUDE.md での指定は必要か

**基本的には不要。** プラグインのSessionStartフックが、セッション開始時に using-superpowers の指示を自動で注入する。

ただし、フックが保証するのは「指示がモデルに渡る」ところまで。その指示を読んで自分からスキルを呼ぶかどうかはモデル次第で、gpt-oss-120bでは無視されたりタイミングがずれたりする可能性がある。

## 4. 推奨する確認手順

1. 何も追加せずに「〇〇機能を作りたい」と依頼し、brainstorming が自動で始まるか確認する。
2. 始まらない場合は `/superpowers:brainstorm` などのコマンドで明示的に呼ぶ。
3. それでも手順を飛ばす場合は、CLAUDE.md に次の一文を追加して後押しする。

   ```
   実装前に必ずsuperpowersのスキルを確認して使うこと。
   ```

手順3は必須ではなく、ローカルモデルの弱いところを補うための保険という位置づけ。

## 参考

- [obra/superpowers (GitHub)](https://github.com/obra/superpowers)
- [obra/superpowers-marketplace (GitHub)](https://github.com/obra/superpowers-marketplace)
