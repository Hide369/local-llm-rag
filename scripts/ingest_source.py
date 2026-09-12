"""source/ 配下の資料をベクトルDBへ取り込むCLI。

初回はOCR23ページを含む38ファイル・460チャンクの処理でおよそ24分かかる。
Streamlitのボタンで24分ブロックするのは現実的でないため、初回はこのCLIから実行する。

1ファイル処理するごとにDBへ書き込む。全ファイル分をまとめて書き込むと、
12分経過時点の失敗ですべてを失う。ファイル単位で保存しておけば、再実行時に
ハッシュ判定で成功済みのファイルがスキップされ、失敗分だけをやり直せる。
"""
import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# OLLAMA_HOST を ingest.embedder がインポート時に読むため、他のプロジェクト内
# importより先に .env を読み込む必要がある。
load_dotenv()

from ingest import embedder, navigation, store, vlm
from ingest.chunker import chunk_units
from ingest.models import PAGE, SLIDE, ParsedUnit
from ingest.parsers import SUPPORTED_SUFFIXES, parse

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
DB_PATH = store.DB_PATH

# アップロード由来の資料キーに付ける接頭辞。source/ 直下に同名の資料があっても
# 上書きしないためと、画面の一覧・削除がキーの前方一致だけで済むようにするため。
UPLOAD_PREFIX = "uploads/"


@dataclass
class IngestReport:
    indexed: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)
    # 資料キー → ナビゲーション用スライドとして除外した件数。
    # 1件も落ちなかった資料はキーを持たない。
    dropped: dict[str, int] = field(default_factory=dict)
    # 全ユニットがナビゲーション判定になり、何も落とさなかった資料のキー。
    # notify() のログはCLIでしか見えない（Streamlit経路は on_progress を渡して
    # いない）。この情報を報告に載せておかないと、GUIから取り込んだときに
    # 全滅の警告が見えないところで消える。
    kept_all_navigation: list[str] = field(default_factory=list)
    # 資料キー → 見つからなかった画像の参照先。件数だけでは、どの画像が
    # 抜けたのか追えない。dropped を件数ではなく現物で持っているのと同じ理由。
    missing_images: dict[str, list[str]] = field(default_factory=dict)


def file_hash(path: Path) -> str:
    """内容が1バイトでも変われば変わる識別子。先頭16桁で十分に衝突しない。"""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:16]


def _normalise_suffix(suffix: str) -> str:
    """先頭のドットの有無を問わない。--only-suffix md と .md を同じに扱う。"""
    lowered = suffix.strip().lower()
    return lowered if lowered.startswith(".") else f".{lowered}"


def _target_files(source_dir: Path, only_suffix: str | None = None) -> list[Path]:
    """サブフォルダも含めて対象ファイルを集める。

    資料を分類して置けるようにするため再帰する。対象外の拡張子はここで落とすので、
    source/ に雑多なファイルが増えてもパーサーには渡らない。
    ~$ で始まるファイルはOfficeが編集中に作る一時ファイル（ロックファイル）なので、
    対応拡張子でも除外する。含めるとPermissionErrorで取り込みが失敗扱いになる。
    only_suffix を渡すとさらにその拡張子だけへ絞る。フロントマターの追加のように
    Markdownだけを取り直したいとき、OCRを含む全量再処理（約24分）を避けるため。
    """
    wanted = _normalise_suffix(only_suffix) if only_suffix else None
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and not path.name.startswith("~$")
        and (wanted is None or path.suffix.lower() == wanted)
    )


def _source_key(path: Path, source_dir: Path) -> str:
    """source/ からの相対パスを資料の識別子にする。

    区切りはスラッシュに統一する。WindowsのバックスラッシュがそのままチャンクIDと
    メタデータに入ると、環境をまたいだときに一致しなくなるため。
    直下のファイルは相対パスがファイル名と一致するので、既存のチャンクの識別子は
    変わらず、再取り込みは発生しない。
    """
    return path.relative_to(source_dir).as_posix()


# 位置の呼び方は ingest/retrieval.py の Hit._one_citation() に揃える。
# 利用者が画面で見る出典と同じ言い方でないと、どのスライドの話か照合できない。
# diagram（drawio）と section（Markdown）と sheet（Excel）はここに載せない。
# 通し番号が利用者にとって意味を持たず、_dropped_positions が heading を出すため。
_POSITION_LABELS = {PAGE: "p.", SLIDE: "スライド"}


def _dropped_positions(dropped: list[ParsedUnit]) -> str:
    """落としたユニットの位置を「スライド4,5,17」の形にまとめる。

    件数だけでは、規則が誤爆したときに何が消えたのか追えない。
    navigation.drop_navigation() が件数ではなく現物を返しているのはこのためで、
    ここがその現物を使う唯一の場所である。

    通し番号が利用者にとって意味を持たない形式（Markdownの見出し）は見出し文字列を
    出す。1つの資料は1つのパーサーが読むので種別が混ざることはないが、混ざっても
    壊れないよう種別ごとにまとめる。
    """
    groups: dict[str, list[str]] = {}
    for unit in dropped:
        label = _POSITION_LABELS.get(unit.location_type, "")
        position = str(unit.location) if label else (unit.heading or str(unit.location))
        groups.setdefault(label, []).append(position)
    return "、".join(f"{label}{','.join(items)}" for label, items in groups.items())


def _ingest_one(
    path: Path,
    source: str,
    current_hash: str,
    collection,
    session,
    today: str,
    caption_image,
    notify,
    report: IngestReport,
    keep_code_blocks: bool = False,
) -> None:
    """1ファイルを解析して取り込み、結果を report へ記録する。

    source/ の走査（ingest_directory）と画面からのアップロード（ingest_uploads）で
    違うのは、対象ファイルの集め方・差分判定・孤児削除の有無だけである。解析から
    保存までの手順は同じものを使う。2箇所に写すと、ナビゲーション除外のような
    判断が片方にしか入らない状態が生まれる。
    """
    notify(f"処理中: {source}")
    missing: list[str] = []
    try:
        units = parse(path, caption_image=caption_image, on_missing_image=missing.append)
        kept, dropped = navigation.drop_navigation(units)
        kept_all_navigation = bool(dropped) and not kept
        if kept_all_navigation:
            # 規則が誤爆したときに資料が丸ごと消えるのを防ぐ。空のチャンク列を
            # store.replace_source() に渡すと、その資料はDBから消える。
            # 中身のある資料からノイズを取り除くのがこの機能の目的であり、
            # 「中身が1つも無い資料」は規則の誤りである可能性のほうが高い。
            notify(f"警告: {source} は全ユニットがナビゲーション判定。除外しません")
            dropped = []
        else:
            units = kept
        chunks = chunk_units(
            units, source, current_hash, today, keep_code_blocks=keep_code_blocks
        )
        vectors = embedder.embed_texts(
            [chunk.text for chunk in chunks], session=session
        )
        store.replace_source(collection, source, chunks, vectors)
    except Exception as error:  # 1ファイルの失敗で全体を止めない
        report.failed[source] = str(error)
        notify(f"失敗: {source} — {error}")
        return

    report.indexed[source] = len(chunks)
    if missing:
        # 取り込みは成功している。画像が付かなかったことだけを伝える。
        report.missing_images[source] = missing
        notify(f"画像が見つかりません: {source} — {'、'.join(missing)}")
    # 報告に載せるのは取り込みが成功した資料だけである。埋め込みで失敗した
    # 資料をここに載せると、要約に「失敗」と「全ユニットがナビゲーション
    # 判定のため除外しませんでした」が並び、後者が「丸ごと取り込んだ」と
    # 読めてしまう（実際はDBに1件も入っていない）。
    if kept_all_navigation:
        report.kept_all_navigation.append(source)
    if dropped:
        report.dropped[source] = len(dropped)
        notify(
            f"完了: {source}（{len(chunks)}チャンク、"
            f"ナビゲーション{len(dropped)}件を除外: "
            f"{_dropped_positions(dropped)}）"
        )
    else:
        notify(f"完了: {source}（{len(chunks)}チャンク）")


def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
    only_suffix: str | None = None,
    caption_image=None,
    keep_code_blocks: bool = False,
) -> IngestReport:
    """source_dir を走査し、変更のあった資料だけを取り込む。"""
    # source/uploads/ の資料はキーが uploads/… になり、画面からアップロードした
    # 資料と区別が付かなくなる。混ざると孤児削除の除外（下）がsource/の資料まで
    # 守ってしまい、消えるべき資料が消えない。名前を直してもらう。
    if (source_dir / UPLOAD_PREFIX.rstrip("/")).is_dir():
        raise ValueError(
            f"{source_dir} に uploads/ があります。この名前は画面からアップロード"
            "した資料の予約語です。別の名前に変更してください。"
        )

    report = IngestReport()
    notify = on_progress or (lambda _message: None)
    own_session = session is None
    session = session or embedder.new_session()
    today = date.today().isoformat()

    try:
        files = _target_files(source_dir, only_suffix)
        for path in files:
            source = _source_key(path, source_dir)
            current_hash = file_hash(path)

            if not force and store.stored_file_hash(collection, source) == current_hash:
                report.skipped.append(source)
                notify(f"スキップ（変更なし）: {source}")
                continue

            _ingest_one(
                path,
                source,
                current_hash,
                collection,
                session,
                today,
                caption_image,
                notify,
                report,
                keep_code_blocks,
            )

        # source/ を唯一の入力とするため、消えた資料はDBからも消す。
        # ただし部分取り込みのときは行わない。対象外の拡張子のファイルが
        # すべて孤児と判定され、他形式のチャンクが丸ごと消えるため。
        if only_suffix is None:
            # アップロード由来の資料は原本が source/ に無い。既知の集合へ加えないと、
            # 誰かが「差分を取り込む」を押した瞬間に画面から取り込んだ資料が消える。
            # 消す時期は利用者がダイアログの削除ボタンで決める。
            known = {_source_key(path, source_dir) for path in files}
            known |= {
                source
                for source in store.indexed_sources(collection)
                if source.startswith(UPLOAD_PREFIX)
            }
            report.removed = store.delete_orphans(collection, known)
            for source in report.removed:
                notify(f"削除（source/にありません）: {source}")
    finally:
        if own_session:
            session.close()

    return report



def upload_key(filename: str) -> str:
    """アップロードされたファイル名から資料キーを組み立てる。"""
    return f"{UPLOAD_PREFIX}{filename}"


def ingest_uploads(
    paths,
    collection,
    session=None,
    on_progress=None,
    caption_image=None,
) -> IngestReport:
    """画面からアップロードされた一時ファイルを取り込む。

    孤児削除を行わない。渡されるのはその場でアップロードされた数ファイルだけで、
    それを唯一の入力とみなすと source/ 由来の資料がすべて孤児として消える。

    差分判定もしない。原本は一時ファイルであり、同じ内容を上げ直したかどうかは
    利用者にとって意味を持たない。押したら取り込まれるほうが画面の挙動として
    素直である。
    """
    report = IngestReport()
    notify = on_progress or (lambda _message: None)
    own_session = session is None
    session = session or embedder.new_session()
    today = date.today().isoformat()

    try:
        for path in paths:
            _ingest_one(
                path,
                upload_key(path.name),
                file_hash(path),
                collection,
                session,
                today,
                caption_image,
                notify,
                report,
            )
    finally:
        if own_session:
            session.close()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="source/ の資料をベクトルDBへ取り込む")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--force", action="store_true", help="変更がなくても再取り込みする"
    )
    parser.add_argument(
        "--only-suffix",
        help="この拡張子のファイルだけを対象にする（例 .md）。指定時は孤児削除を行わない",
    )
    parser.add_argument(
        "--with-vlm",
        action="store_true",
        help=(
            "PDF/PPTX/DOCX/XLSX/Markdown内の埋め込み画像をVLMで説明文化しOCRにかける"
            "（指定しないと画像は一切走査されない。取り込みが大幅に遅くなる）"
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=store.DB_PATH,
        help=(
            "取り込み先のDBファイル（既定は社内資料の vector_store.sqlite3）。"
            "技術ドキュメントは docs_store.sqlite3 を指定する"
        ),
    )
    parser.add_argument(
        "--keep-code-blocks",
        action="store_true",
        help=(
            "コードブロックを途中で割らずに1チャンクへ収める"
            "（技術ドキュメント向け。社内資料には指定しない）"
        ),
    )
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        print(f"ディレクトリがありません: {args.source_dir}")
        return 1

    try:
        # 460チャンクの処理を始めてから落ちないよう、先に疎通を確認する。
        embedder.check_ollama()
    except embedder.EmbeddingError as error:
        print(error)
        return 1

    caption_image = None
    if args.with_vlm:
        try:
            vlm.check_vlm()
        except vlm.VlmError as error:
            print(error)
            return 1
        caption_image = vlm.caption_image

    # open_store はパスを間違えても例外を出さず空のDBを新規作成する
    # （ingest/store.py の DB_PATH のコメント参照）。タイポは「検索結果が全部空」
    # という静かな失敗になり、テストも緑のまま通る。どのファイルを開いたかを
    # 必ず画面に出し、取り込み後の件数でも裏を取る。
    print(f"取り込み先: {args.db}")
    collection = store.open_store(str(args.db))
    report = ingest_directory(
        args.source_dir,
        collection,
        on_progress=print,
        force=args.force,
        only_suffix=args.only_suffix,
        caption_image=caption_image,
        keep_code_blocks=args.keep_code_blocks,
    )

    print("\n--- 結果 ---")
    print(f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル")
    print(f"スキップ: {len(report.skipped)}ファイル")
    print(f"削除: {len(report.removed)}ファイル")
    if report.dropped:
        print(
            f"ナビゲーション除外: {sum(report.dropped.values())}件"
            f" / {len(report.dropped)}ファイル"
        )
    for source, references in report.missing_images.items():
        print(f"画像が見つかりません {source}: {'、'.join(references)}")
    if report.kept_all_navigation:
        print(
            "全ユニットがナビゲーション判定のため除外しませんでした: "
            + "、".join(report.kept_all_navigation)
        )
    if report.failed:
        print(f"失敗: {len(report.failed)}ファイル")
        for source, message in report.failed.items():
            print(f"  {source}: {message}")
    total = collection.count()
    print(f"DB内の総チャンク数: {total}（本文{collection.chunk_count()}種）")
    if total == 0:
        # 0件で正常終了すると、検索が全部空になる原因に気づけない。
        print(f"警告: {args.db} は空です。--db のパスが正しいか確認してください")

    # 取り込めたことと、次にDBを開いたときに読めることは別の事実である。
    # ChromaDBでは前者だけが成立し、破損が次回起動まで露見しなかった。
    #
    # 件数だけでは足りない。あの障害はベクトルの読み込みで起きており、件数は
    # 最後まで正しく返っていた。接続を開き直したうえで検索を1回通し、
    # ベクトルの層まで実際に触る。
    try:
        verified = store.open_store(str(args.db))
        indexed = verified.count()
        if indexed and not verified.search(
            [1.0] + [0.0] * (embedder.EMBED_DIM - 1), limit=1
        ):
            raise RuntimeError(f"{indexed}件あるのに検索が0件を返しました")
        # 帳簿が2つに分かれたぶん、片方だけが残る壊れ方が新しく生まれる。
        # 孤児の本文はベクトル行列に載り続けるが、検索結果には現れない。
        # 上位の枠は取ったうえで出現が引けずに落とされるため、本物のヒットを
        # 黙って押し出す（隔離DBでの実測: 孤児1件と正規1件で limit=2 を引くと
        # 1件しか返らず、limit=1 では0件になる）。さらに chunks() 経由で
        # BM25索引にも載り、idf と平均文書長を歪める。出現だけの行は逆に
        # 本文が引けない。どちらも件数には表れない。
        orphans, dangling = verified.integrity()
        if orphans or dangling:
            raise RuntimeError(
                f"整合性が壊れています: 孤児の本文{orphans}件 / 本文の無い出現{dangling}件"
            )
    except Exception as error:  # noqa: BLE001  何が起きても取り込みは失敗とする
        print(f"取り込み後の検証に失敗しました: {error}")
        return 1

    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
