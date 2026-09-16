# GB10のデスクトップで日本語を入力する

GB10（DGX Spark / OEM機）の画面に直接キーボードを繋いだとき、テキスト欄で日本語が
打てない場合の手当て。出荷状態のDGX OSには日本語のインプットメソッド（IME）が
入っていないため、これは故障ではなく未導入である。

> **この文書の位置づけ**
> DGX OS 7（Ubuntu 24.04ベース・`aarch64`）のGNOMEデスクトップを前提にした一般的な
> 手順である。**手元にGB10が無いため実測はしていない。** パッケージ名とGNOMEの
> メニュー名は版で変わるので、[1節](#1-いまどうなっているかを確かめる)の確認
> コマンドで現物を見てから進めること。

## 目次

- [0. その前に：GB10で入力する必要があるか](#0-その前にgb10で入力する必要があるか)
- [1. いまどうなっているかを確かめる](#1-いまどうなっているかを確かめる)
- [2. フォントとロケール](#2-フォントとロケール)
- [3. IMEを入れる](#3-imeを入れる)
- [4. アプリごとのはまりどころ](#4-アプリごとのはまりどころ)
- [5. 動作確認](#5-動作確認)
- [6. aptが通らない社内ネットワークの場合](#6-aptが通らない社内ネットワークの場合)
- [7. トラブルシュート](#7-トラブルシュート)
- [出典](#出典)

## 0. その前に：GB10で入力する必要があるか

症状が「GB10で日本語が打てない」でも、**文字を打っている機械がどれか**で必要な作業が
変わる。

|使い方|打鍵と変換をするのは|GB10側に要るもの|
|---|---|---|
|手元のWindowsからSSH / VS Code Remote|手元のWindowsのIME|フォントとロケールだけ（[2節](#2-フォントとロケール)）|
|手元のブラウザーからStreamlit画面を開く|手元のWindowsのIME|なし|
|GB10の画面にキーボードを繋ぐ／VNC・RDPでデスクトップに入る|GB10のIME|[3節](#3-imeを入れる)の一式|

つまり、GB10を推論サーバーとして置き、操作は手元からという構成なら、GB10にIMEは
要らない。GB10のデスクトップを人が直接使う場合だけ以下が要る。

## 1. いまどうなっているかを確かめる

```bash
# aarch64 / Ubuntu 24.04 ベースであること
uname -m
lsb_release -a

# セッションが wayland か x11 か（4節の判断に使う）
echo "$XDG_SESSION_TYPE"

# ロケール。ja_JP.UTF-8 が無ければ2節
locale
locale -a | grep -i ja

# IMEが入っているか。何も出なければ3節
dpkg -l | grep -E 'mozc|ibus|fcitx'
im-config -l

# 日本語フォントがあるか。0 なら2節
fc-list | grep -ci "Noto Sans CJK"
```

`uname -m` が `aarch64` でも、ここで入れるものに自前ビルドは要らない。mozc・ibus・
fcitx5 はいずれもUbuntuのarm64リポジトリにバイナリがあり、`apt` でそのまま入る。
vLLMのときのような `sm_121` / aarch64 のwheel問題（[docs/vllm-gb10.md](vllm-gb10.md)）は
ここでは起きない。

## 2. フォントとロケール

IMEより先にこちらを入れる。IMEが無くても、日本語を「表示する」「貼り付ける」
「ログを読む」だけならこれで足りる。

```bash
sudo apt update
sudo apt install -y fonts-noto-cjk fonts-noto-cjk-extra language-pack-ja
```

`language-pack-ja` を入れると `ja_JP.UTF-8` が生成される。生成されていなければ
明示する。

```bash
sudo locale-gen ja_JP.UTF-8
```

画面全体を日本語にするかどうかは別の話である。**表示は英語のままでよい**なら
ロケールは変えなくてよい（日本語の表示と入力はロケールとは独立している）。
日本語表示にしたい場合だけ次を実行して再ログインする。

```bash
sudo localectl set-locale LANG=ja_JP.UTF-8
```

SSHの向こうで日本語が化けるときもここが効く。クライアントから `LANG` を送るか、
GB10側の `~/.bashrc` で `export LANG=ja_JP.UTF-8` する。

## 3. IMEを入れる

**ibus-mozc と fcitx5-mozc のどちらか一方**を選ぶ。両方を常駐させると取り合いになって
かえって入力できなくなる。まず A を試し、VS CodeやChromeで効かないようなら B に
乗り換える。

### A. ibus-mozc（GNOMEの標準。まずこちら）

GNOMEは ibus を前提に作られていて、Wayland でも X11 でもGNOME側が面倒を見る。
入れる物がいちばん少ない。

```bash
sudo apt install -y ibus-mozc
im-config -n ibus
```

ここで**ログアウトして入り直す**（再ログインしないと反映されない）。そのあと
「設定 → キーボード → 入力ソース → ＋ → 日本語 → 日本語 (Mozc)」を追加する。
端末から入れるなら次でもよい。

```bash
# 日本語配列キーボードの場合
gsettings set org.gnome.desktop.input-sources sources "[('xkb','jp'),('ibus','mozc-jp')]"
# 英語配列キーボードの場合
gsettings set org.gnome.desktop.input-sources sources "[('xkb','us'),('ibus','mozc-jp')]"
```

切り替えはGNOMEの入力ソース切り替え、既定で `Super`+`Space`。効かないときは
`ibus restart` で読み直す。

### B. fcitx5-mozc（Electron/Chromium系で確実に効かせたいとき）

VS Code や Chrome のような Chromium/Electron のアプリは、Wayland上でIMEを掴み損ねる
ことがある（[vscode#277073](https://github.com/microsoft/vscode/issues/277073)）。
fcitx5 は手当ての幅が広く、この手の不具合の情報も多い。

```bash
sudo apt install -y fcitx5 fcitx5-mozc fcitx5-config-qt
im-config -n fcitx5
```

`/etc/environment` の末尾に次を足す（root権限が要る）。

```
GTK_IM_MODULE=fcitx
QT_IM_MODULE=fcitx
XMODIFIERS=@im=fcitx
```

ログアウトして入り直し、`fcitx5-configtool` で入力メソッドに「Mozc」を追加する。
切り替えは既定で `Ctrl`+`Space`。

Wayland では、GTKアプリをWaylandネイティブの経路（text-input-v3）に任せるほうが
安定する場合があり、その場合は `GTK_IM_MODULE` を**設定しない**。どちらが良いかは
GNOMEとfcitx5の版の組み合わせで変わるので、両方試して動くほうを採る。現状の診断は
`fcitx5-diagnose` が出してくれる。

## 4. アプリごとのはまりどころ

- **VS Code / Chrome / Chromium（Electron系）**：Wayland セッション（1節の
  `XDG_SESSION_TYPE` が `wayland`）でだけIMEが効かない、という切り分けになったら、
  起動フラグを足す。

  ```bash
  code --ozone-platform-hint=auto --enable-wayland-ime --wayland-text-input-version=3
  ```

  恒久化するなら `~/.local/share/applications/` に `.desktop` をコピーして `Exec=` に
  足すか、環境変数 `ELECTRON_OZONE_PLATFORM_HINT=auto` を入れる。それでも駄目なら
  XWayland（X11）で起動すると `XMODIFIERS` 経由で効く。
- **端末（GNOME Terminal など）**：IMEはそのまま効く。SSHの向こうへ送った文字が
  化けるのは入力ではなくロケールの問題で、[2節](#2-フォントとロケール)の `LANG` を見る。
- **本リポジトリのStreamlit画面**：ブラウザーの上で動くので、ブラウザーでIMEが効けば
  打てる。GB10のChromeで打てないなら上のフラグを、手元のWindowsのブラウザーで
  開いているならGB10側の設定は無関係である。

## 5. 動作確認

```bash
# ibus を選んだ場合、mozc が見えること
ibus list-engines | grep -i mozc

# fcitx5 を選んだ場合、足りないものを指摘してくれる
fcitx5-diagnose | head -40

# Mozc 自体の設定（キー割り当てなど）
/usr/lib/mozc/mozc_tool --mode=config_dialog
```

そのうえで `gnome-text-editor` を開き、切り替えキーを押してから「にほんご」と打って
変換候補が出ることを見る。**この確認を通していない状態を「直った」と呼ばないこと。**

## 6. aptが通らない社内ネットワークの場合

外に出られない場所に置いたGB10では `apt install` が失敗する。別のUbuntu 24.04
**arm64** 機で`.deb`を集めて持ち込む。

```bash
# 取得側（arm64のUbuntu 24.04で実行すること）
apt-get install --download-only -o Dir::Cache::archives=./debs \
  ibus-mozc fonts-noto-cjk language-pack-ja

# GB10側
sudo apt install ./debs/*.deb
```

x86_64機で集めた`.deb`は入らない。`dpkg --print-architecture` が `arm64` である機械で
集めること。

## 7. トラブルシュート

|症状|原因|対処|
|---|---|---|
|`半角/全角` キーを押しても何も起きない|英語配列扱い、またはキー割り当てが無い|`Super`+`Space`（ibus）/ `Ctrl`+`Space`（fcitx5）で切り替える。`mozc_tool --mode=config_dialog` でキーを割り当て直す|
|再ログインしたのにIMEが出ない|`im-config` の選択が入っていない／ibusとfcitx5が両方入っている|`im-config -l` で確認し、`im-config -n <一つだけ>`、ログアウトして入り直す|
|端末では打てるがVS Code / Chromeで打てない|WaylandでElectronがIMEを掴んでいない|[4節](#4-アプリごとのはまりどころ)のフラグ。駄目ならXWaylandで起動|
|変換候補の窓が出ず、ローマ字がそのまま入る|アプリがIMEに繋がっていない|`fcitx5-diagnose`、または`GTK_IM_MODULE`の有無を切り替えて再ログイン|
|日本語が □（豆腐）になる|日本語フォントが無い|`sudo apt install fonts-noto-cjk`|
|SSH越しに日本語が化ける|リモート側の`LANG`が英語|`export LANG=ja_JP.UTF-8`、または`SendEnv`/`AcceptEnv`で送る|
|`apt` が404を返す|universeが無効、または社内ネットワークで外に出られない|`sudo add-apt-repository universe && sudo apt update`。出られないなら[6節](#6-aptが通らない社内ネットワークの場合)|

## 出典

- [NVIDIA DGX OS 7 User Guide](https://docs.nvidia.com/dgx/dgx-os-7-user-guide/)（DGX OS 7 が Ubuntu 24.04 ベースであること。DGX Spark は 7.2.3 以降）
- [Canonical — NVIDIA DGX Spark is built on an Ubuntu base](https://canonical.com/blog/nvidia-dgx-spark-ubuntu-base)（Waylandのデスクトップが載っていること）
- [Fcitx — Using Fcitx 5 on Wayland](https://fcitx-im.org/wiki/Using_Fcitx_5_on_Wayland)（Wayland での環境変数の扱い）
- [microsoft/vscode#277073 — Japanese IME not working on Linux (Wayland + fcitx5)](https://github.com/microsoft/vscode/issues/277073)（Electron系のフラグ）
- 本リポジトリ内: [docs/vllm-gb10.md](vllm-gb10.md)（GB10そのものの構築手順）、
  [docs/vllm-gb10-models.md](vllm-gb10-models.md)（載せるモデルの選定）
