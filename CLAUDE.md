@AGENTS.md

## Claude Code 固有

上の共通ガイドラインは `AGENTS.md` に置いてある。Claude Code は `AGENTS.md` を
読まないため、ここからインポートして両ツールで同じ内容を共有している。二重管理に
しないこと。追記は `AGENTS.md` 側へ行い、Claude Code だけに効かせたいものだけを
この節に書く。

- 共通ガイドラインの PowerShell コマンドと仮想環境（`myvenv313`）はそのまま使える。
- `.agents/skills/` は Codex 向けの配置である。Claude Code から同じ superpowers
  スキルを使う場合はプラグインを導入し、`superpowers:brainstorming` のように
  `superpowers:` 付きで呼ぶ。`$skill-name` 記法は Codex のものである。
- 社内資料の MCP サーバ（`local_docs` / `search_documents`）への接続と、利用者側の
  `~/.claude/CLAUDE.md` の書き方は [docs/claude-code-vscode.md](docs/claude-code-vscode.md)
  にある。
