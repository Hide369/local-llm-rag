"""テスト全体で共有する、EphemeralClient生成まわりのヘルパー。

chromadbのEphemeralClient()生成はWindows上でRust拡張が非致命的な
access violationを起こし（chromadb/api/rust.py:112 の start()内）、pytestの
faulthandlerがそのたびに全スタックトレースを標準出力へ書き出す。テスト自体は
毎回成功しているが、3行で済むはずのサマリが数百行のノイズに埋もれ、本物の
警告が出ても気づけなくなる。

Task 7では `-p no:faulthandler` でプロジェクト全体のfaulthandlerを切って
これを黙らせようとしたが、それはクラッシュ診断能力をテスト全体から奪う
副作用が大きすぎるため差し戻された（コミット8d75e20）。ここではその反省を
踏まえ、EphemeralClient()を生成する一瞬だけfaulthandlerを止め、直後に
元の状態へ戻す。他のテストのクラッシュ診断には影響しない。

ここで生成するのはインメモリのEphemeralClientのみで、本番のchroma_dbには
一切触れない。
"""
import faulthandler

import chromadb


def ephemeral_client():
    """access violationのノイズを出さずにEphemeralClientを生成する。"""
    was_enabled = faulthandler.is_enabled()
    faulthandler.disable()
    try:
        return chromadb.EphemeralClient()
    finally:
        if was_enabled:
            faulthandler.enable()
