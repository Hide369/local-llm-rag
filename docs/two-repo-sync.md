# 本家とvLLM版の2リポジトリを同期する

同じアプリを2つのリポジトリで持つ。

|呼び名|リポジトリ|既定の接続先|
|---|---|---|
|**本家**|`Hide369/local-llm-rag`|Ollama（`LLM_BACKEND=ollama`）|
|**vLLM版**|`Hide369/local-llm-rag-vllm`|GB10のvLLM（`LLM_BACKEND=vllm`）|

## 最初に: これは本来やりたくない形である

`CLAUDE.md` に「二重管理にしないこと」と書いてある。**2リポジトリを持つのは、
その戒めに正面からぶつかる。** 片方だけ直した変更は、気づかれないまま何か月も
残る。どちらが正なのか分からなくなった時点で、両方が信用できなくなる。

それでもこの形を採るなら、守るべき条件は1つだけである。

> **2つのリポジトリの差分を、意図的に小さく保つ。**

差分が3ファイル以内に収まっているあいだは、`git merge` がほぼ自動で通る。
コードに手が入り始めると、毎回のマージで衝突が出て、いずれ同期が止まる。

そのために、**接続先もモデル名も環境変数で切り替わるようにしてある**
（`ingest/backend.py`、`LLM_BACKEND` / `EMBED_MODEL` / `CHAT_MODELS` ほか。
[docs/vllm-gb10.md の8節](vllm-gb10.md#8-本リポジトリのragとつなぐ)）。
**新しい違いが出てきたら、まず「環境変数で吸収できないか」を考えること。**
吸収できるなら、その実装は本家へ入れる。vLLM版に固有のコードを書くのは最後の手段である。

## 差分は何か

vLLM版が本家と違うのは、原則としてこの2ファイルだけである。

|ファイル|違い|
|---|---|
|`.env.example`|vLLM向けの値（`LLM_BACKEND=vllm`、`VLLM_HOST`、`EMBED_MODEL` など）が既定で有効になっている|
|`README.md`|冒頭に「これはvLLM版である」の断りと、本家へのリンクがある|

`ingest/retrieval.py` の `RELEVANCE_THRESHOLD` は、埋め込みモデルを替えたあとに
**実測して**入れ替える値である。測るまでは本家と同じ値のままにしておくこと
（`scripts/check_retrieval.py`）。当てずっぽうで変えると、圏外の質問に答えるように
なったことが誰にも分からない。

## 日常の流れ

**原則: 変更は本家で作り、本家にマージしてから、vLLM版へ流す。** 逆向きに作ると、
どちらが新しいのか分からなくなる。

### 1. 一度だけ: vLLM版にリモートを足す

```bash
git clone https://github.com/Hide369/local-llm-rag-vllm.git
cd local-llm-rag-vllm
git remote add upstream https://github.com/Hide369/local-llm-rag.git
git remote -v   # origin = vllm版 / upstream = 本家
```

### 2. 本家へマージしたあと、vLLM版へ流す

```bash
git fetch upstream
git checkout master
git merge upstream/master
# 衝突は .env.example と README.md の冒頭でしか起きないはずである
git push origin master
```

衝突したときは、**その2ファイルについては常にvLLM版の側を残す**。

```bash
git checkout --ours .env.example README.md
git add .env.example README.md
git merge --continue
```

`--ours` を毎回打つのが面倒なら、vLLM版のクローンにマージドライバを仕込める。

```bash
# vLLM版のクローンで一度だけ
git config merge.keepours.name "常に自分の側を残す"
git config merge.keepours.driver true
printf '.env.example merge=keepours\n' >> .git/info/attributes
```

`.gitattributes` ではなく `.git/info/attributes` に書くのは、この設定が
**そのクローンでしか意味を持たない**ためである（ドライバの定義は `git config` 側に
あり、リポジトリに入れても他の人の手元では動かない）。README は人が読んで
判断すべき変更が入りうるので、自動で潰さない。

### 3. vLLM版で見つけた不具合を直すとき

**vLLM版で直して終わりにしない。** 本家に同じ修正が要る。

```bash
# vLLM版で直して確認したあと
git log --oneline -1          # 直したコミットのハッシュを控える

cd ../local-llm-rag           # 本家のクローンで
git checkout -b fix/xxxx
git cherry-pick <ハッシュ>
# テストを通してPRを出し、本家へマージする

# そのあと vLLM版で本家を取り込み直す（cherry-pick した分は空になって畳まれる）
cd ../local-llm-rag-vllm
git fetch upstream && git merge upstream/master
```

差分の2ファイルだけを触る修正（vLLM側の既定値の間違いなど）は、本家へ持っていく
必要がない。それ以外は必ず本家へ入れる。

## 半年後に効いてくる確認

同期が止まっていないかは、この1行で分かる。

```bash
# vLLM版のクローンで
git fetch upstream && git diff --stat upstream/master..HEAD -- . ':!.env.example' ':!README.md'
```

**ここに何も出なければ健全である。** コードの差分が出てきたら、それは
「環境変数で吸収するはずだったもの」が漏れている合図である。本家へ寄せること。

取り込み漏れのほうは逆向きで見る。

```bash
git log --oneline HEAD..upstream/master   # まだ流していない本家の変更
```

## 統合をやめたくなったら

差分が増えて手に負えなくなったら、2リポジトリをやめる判断もある。本家1本にして
`.env` だけで切り替えるなら、いま `ingest/backend.py` が持っている仕組みで足りる。
**vLLM版のリポジトリは、本家のコードと `.env` の違いでしかない**という前提を
保っているあいだは、いつでもこの選択に戻れる。戻れなくなる前に判断すること。
