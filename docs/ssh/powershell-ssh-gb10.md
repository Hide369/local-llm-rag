# Windows PowerShell から GB10（Ubuntu）へ SSH 接続する

Windows の PowerShell には標準で **OpenSSH クライアント** が組み込まれている。
追加のソフトウェアをインストールしなくても、クライアント PC の PowerShell から
Ubuntu サーバー（GB10）へ SSH 接続してリモート操作できる。

## 接続の手順

### 1. サーバー側（Ubuntu / GB10）の準備

Ubuntu サーバー側で SSH サーバーが有効になっていることを確認する。

**SSH サーバーのインストール状態確認・起動**

```bash
sudo systemctl status ssh
```

インストールされていない、または停止している場合は以下を実行する。

```bash
sudo apt update && sudo apt install openssh-server -y
sudo systemctl enable --now ssh
```

**サーバーの IP アドレスの確認**

```bash
ip a
```

`192.168.1.50` のようなローカル IP アドレスを確認しておく。

### 2. クライアント側（PowerShell）からのログイン

Windows の PowerShell を開き、以下のコマンドを実行する。

```powershell
ssh <ユーザー名>@<サーバーのIPアドレス>
```

実行例:

```powershell
ssh user@192.168.1.50
```

初回接続時にはホストのフィンガープリントの確認が表示される。

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

`yes` と入力し、続けてユーザーのパスワードを入力すればログインできる。

## 快適に運用するためのポイント

### SSH 公開鍵認証の設定（パスワードなしログイン）

毎回のパスワード入力を省略するため、公開鍵認証を設定しておくことを強く推奨する。

1. クライアント側（PowerShell）で鍵を生成する。

   ```powershell
   ssh-keygen
   ```

   保存先を聞かれたら Enter で既定値（`C:\Users\<ユーザー名>\.ssh\`）のままでよい。
   生成される公開鍵は `~/.ssh/id_rsa.pub` 等（OpenSSH のバージョンにより
   `id_ed25519.pub` になる）。

2. 生成された公開鍵をサーバー側の `~/.ssh/authorized_keys` に登録する。
   Windows には `ssh-copy-id` が無いため、PowerShell から次のように送る
   （鍵ファイル名は手順1で生成されたものに合わせる）。

   ```powershell
   type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user@192.168.1.50 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```

以後は `ssh user@192.168.1.50` でパスワードを聞かれずにログインできる。

### `~/.ssh/config` の活用

クライアント側の `C:\Users\<ユーザー名>\.ssh\config` に以下のようなエイリアスを
設定しておくと、短いコマンドで接続できる。

```text
Host gb10-server
    HostName 192.168.1.50
    User your_username
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

これにより、PowerShell から次のように入力するだけでログインできる。

```powershell
ssh gb10-server
```
