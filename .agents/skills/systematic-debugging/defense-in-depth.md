# 多層防御の検証

## 概要

無効なデータによって引き起こされたバグを修正する場合、検証を 1 か所に追加するだけで十分だと感じます。ただし、その 1 つのチェックは、別のコード パス、リファクタリング、またはモックによってバイパスされる可能性があります。

**中心原則:** データが通過するすべての層で検証します。バグを構造的に不可能にする。

## 複数のレイヤーを使用する理由

単一の検証: 「バグを修正しました」
複数のレイヤー: 「バグを不可能にしました」

レイヤーが異なると、異なるケースが検出されます。
- エントリの検証によりほとんどのバグが検出されます
- ビジネスロジックがエッジケースをキャッチ
- 環境ガードはコンテキスト固有の危険を防止します
- デバッグログは、他のレイヤーで障害が発生した場合に役立ちます

## 4 つの層

### レイヤ 1: エントリ ポイントの検証
**目的:** API 境界で明らかに無効な入力を拒否する

```typescript
function createProject(name: string, workingDirectory: string) {
  if (!workingDirectory || workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }
  if (!statSync(workingDirectory).isDirectory()) {
    throw new Error(`workingDirectory is not a directory: ${workingDirectory}`);
  }
  // ... proceed
}
```

### レイヤ 2: ビジネス ロジックの検証
**目的:** データがこの操作にとって意味があることを確認する

```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }
  // ... proceed
}
```

### レイヤ 3: 環境保護
**目的:** 特定の状況における危険な操作を防止する

```typescript
async function gitInit(directory: string) {
  // In tests, refuse git init outside temp directories
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    const tmpDir = normalize(resolve(tmpdir()));

    if (!normalized.startsWith(tmpDir)) {
      throw new Error(
        `Refusing git init outside temp dir during tests: ${directory}`
      );
    }
  }
  // ... proceed
}
```

### レイヤ 4: デバッグ計測
**目的:** フォレンジックのためにコンテキストをキャプチャする

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  logger.debug('About to git init', {
    directory,
    cwd: process.cwd(),
    stack,
  });
  // ... proceed
}
```

## パターンの適用

バグを見つけた場合:

1. **データ フローを追跡する** - 不正な値はどこから発生しているのか?どこで使われますか？
2. **すべてのチェックポイントをマッピング** - データが通過するすべてのポイントをリストします
3. **各レイヤーに検証を追加** - エントリ、ビジネス、環境、デバッグ
4. **各レイヤーをテスト** - レイヤー 1 をバイパスし、レイヤー 2 がそれをキャッチすることを確認します。

## セッションの例

バグ: 空です `projectDir` 引き起こされた `git init` ソースコード内で

**データフロー:**
1. テスト設定 → 空の文字列
2. `Project.create(name, '')`
3. `WorkspaceManager.createWorkspace('')`
4. `git init` 駆け込む `process.cwd()`

**4 つのレイヤーが追加されました:**
- レイヤー 1: `Project.create()` 空でない/存在する/書き込み可能であることを検証します
- レイヤー 2: `WorkspaceManager` projectDir が空でないことを検証します
- レイヤー 3: `WorktreeManager` テストで tmpdir 外の git init を拒否します
- レイヤー 4: git init 前のスタック トレース ロギング

**結果:** 1847 のテストすべてに合格、バグの再現は不可能

## 重要な洞察

4 つの層すべてが必要でした。テスト中に、各層は他の層が見逃していたバグを発見しました。
- 異なるコードパスによりエントリ検証がバイパスされる
- ビジネスロジックチェックをバイパスしたモック
- さまざまなプラットフォームでのエッジケースには環境保護が必要です
- デバッグログにより構造的誤用が特定されました

**1 つの検証ポイントで停止しないでください。** すべてのレイヤーにチェックを追加します。
