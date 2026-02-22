import argparse
import datetime as dt
import hashlib
import platform
import sqlite3
import unicodedata
from pathlib import Path

import cltk
from cltk.lemmatize.grc import GreekBackoffLemmatizer


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "hermes_text.db"
LEMMA_VERSION = "GreekBackoffLemmatizer"
MODEL_VERSION = "GreekBackoffLemmatizer:built-in"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hermes", description="Hermes CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    rebuild = sub.add_parser("rebuild-lemmas", help="Rebuild lemma layer transactionally")
    rebuild.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to hermes_text.db")
    rebuild.add_argument("--dry-run", action="store_true", help="Compute diff/signature only")
    rebuild.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    return parser.parse_args()


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFC", value)
    text = text.strip().lower()
    # Normalize sigma forms consistently.
    return text.replace("ς", "σ")


def normalize_surface(value: str) -> str:
    return normalize_text(value)


def normalize_lemma(value: str) -> str:
    return normalize_text(value)


def compute_signature(sorted_lemmas: list[str]) -> str:
    joined = "\n".join(sorted_lemmas)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def ensure_schema_objects(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON;")

    # Canonical tables are expected to exist; these ensure lemma-layer objects are present.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS Lemma (
            LemmaId     INTEGER PRIMARY KEY AUTOINCREMENT,
            LemmaText   TEXT NOT NULL UNIQUE
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS TokenLemma (
            TokenId INTEGER NOT NULL,
            LemmaId INTEGER NOT NULL,
            PRIMARY KEY (TokenId, LemmaId),
            FOREIGN KEY (TokenId) REFERENCES Token(TokenId),
            FOREIGN KEY (LemmaId) REFERENCES Lemma(LemmaId)
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS LemmaMetadata (
            LemmaVersion TEXT NOT NULL,
            BuiltAt      TEXT NOT NULL,
            LemmaCount   INTEGER NOT NULL,
            Signature    TEXT NOT NULL,
            Notes        TEXT
        );
        """
    )


def load_tokens(connection: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = connection.execute(
        """
        SELECT TokenId, SurfaceForm
        FROM Token
        ORDER BY TokenId;
        """
    ).fetchall()
    return [(int(token_id), surface or "") for token_id, surface in rows]


def load_existing_state(connection: sqlite3.Connection) -> tuple[set[str], dict[int, str], str | None]:
    existing_lemmas = {row[0] for row in connection.execute("SELECT LemmaText FROM Lemma").fetchall()}

    existing_map_rows = connection.execute(
        """
        SELECT tl.TokenId, l.LemmaText
        FROM TokenLemma tl
        INNER JOIN Lemma l ON l.LemmaId = tl.LemmaId;
        """
    ).fetchall()
    existing_map = {int(token_id): lemma_text for token_id, lemma_text in existing_map_rows}

    latest = connection.execute(
        """
        SELECT Signature
        FROM LemmaMetadata
        ORDER BY BuiltAt DESC
        LIMIT 1;
        """
    ).fetchone()
    latest_sig = latest[0] if latest else None

    return existing_lemmas, existing_map, latest_sig


def build_new_lemmas(tokens: list[tuple[int, str]]) -> tuple[set[str], list[tuple[int, str]], str]:
    lemmatizer = GreekBackoffLemmatizer()

    unique_lemmas: set[str] = set()
    token_lemma_pairs: list[tuple[int, str]] = []

    for token_id, surface in tokens:
        normalized_surface = normalize_surface(surface)
        if not normalized_surface:
            continue

        result = lemmatizer.lemmatize([normalized_surface])
        raw_lemma = normalized_surface
        if result and len(result[0]) > 1 and (result[0][1] or "").strip():
            raw_lemma = result[0][1]

        lemma_text = normalize_lemma(raw_lemma)
        unique_lemmas.add(lemma_text)
        token_lemma_pairs.append((token_id, lemma_text))

    sorted_lemmas = sorted(unique_lemmas)
    signature = compute_signature(sorted_lemmas)
    return unique_lemmas, token_lemma_pairs, signature


def summarize_diff(
    old_lemmas: set[str],
    new_lemmas: set[str],
    old_map: dict[int, str],
    new_pairs: list[tuple[int, str]],
    signature: str,
) -> tuple[int, int, int, int, int]:
    new_map = {token_id: lemma for token_id, lemma in new_pairs}
    added = len(new_lemmas - old_lemmas)
    removed = len(old_lemmas - new_lemmas)
    changed_tokens = sum(1 for token_id, lemma in new_map.items() if old_map.get(token_id) != lemma)

    print(f"Old lemma count: {len(old_lemmas)}")
    print(f"New lemma count: {len(new_lemmas)}")
    print(f"Added: {added}")
    print(f"Removed: {removed}")
    print(f"Tokens changed: {changed_tokens}")
    print(f"Signature: {signature}")

    return len(old_lemmas), len(new_lemmas), added, removed, changed_tokens


def rebuild_transactional(
    connection: sqlite3.Connection,
    unique_lemmas: set[str],
    token_lemma_pairs: list[tuple[int, str]],
    signature: str,
) -> None:
    built_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    notes = (
        f"python={platform.python_version()};"
        f"cltk={cltk.__version__};"
        f"model={MODEL_VERSION}"
    )

    with connection:
        connection.execute("DROP TABLE IF EXISTS TokenLemma;")
        connection.execute("DROP TABLE IF EXISTS Lemma;")

        connection.execute(
            """
            CREATE TABLE Lemma (
                LemmaId     INTEGER PRIMARY KEY AUTOINCREMENT,
                LemmaText   TEXT NOT NULL UNIQUE
            );
            """
        )
        connection.execute(
            """
            CREATE TABLE TokenLemma (
                TokenId INTEGER NOT NULL,
                LemmaId INTEGER NOT NULL,
                PRIMARY KEY (TokenId, LemmaId),
                FOREIGN KEY (TokenId) REFERENCES Token(TokenId),
                FOREIGN KEY (LemmaId) REFERENCES Lemma(LemmaId)
            );
            """
        )

        lemma_id_by_text: dict[str, int] = {}
        for lemma_text in sorted(unique_lemmas):
            connection.execute("INSERT INTO Lemma (LemmaText) VALUES (?)", (lemma_text,))
            lemma_id = connection.execute(
                "SELECT LemmaId FROM Lemma WHERE LemmaText = ?",
                (lemma_text,),
            ).fetchone()[0]
            lemma_id_by_text[lemma_text] = int(lemma_id)

        for token_id, lemma_text in token_lemma_pairs:
            connection.execute(
                "INSERT INTO TokenLemma (TokenId, LemmaId) VALUES (?, ?)",
                (token_id, lemma_id_by_text[lemma_text]),
            )

        connection.execute(
            """
            INSERT INTO LemmaMetadata (LemmaVersion, BuiltAt, LemmaCount, Signature, Notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (LEMMA_VERSION, built_at, len(unique_lemmas), signature, notes),
        )


def command_rebuild_lemmas(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    connection = sqlite3.connect(db_path)
    try:
        ensure_schema_objects(connection)

        tokens = load_tokens(connection)
        old_lemmas, old_map, latest_sig = load_existing_state(connection)
        new_lemmas, new_pairs, new_sig = build_new_lemmas(tokens)

        summarize_diff(old_lemmas, new_lemmas, old_map, new_pairs, new_sig)

        # Determinism guard: same environment + existing metadata should produce same signature.
        if latest_sig is not None and latest_sig != new_sig and not args.force:
            print("WARNING: Signature differs from latest metadata. Aborting. Use --force to proceed.")
            return 2

        if args.dry_run:
            print("Dry-run complete. No database changes made.")
            return 0

        if not args.force:
            response = input("Proceed with transactional lemma rebuild? [y/N]: ").strip().lower()
            if response not in {"y", "yes"}:
                print("Cancelled.")
                return 0

        rebuild_transactional(connection, new_lemmas, new_pairs, new_sig)

        # Post-check determinism in current environment.
        refreshed_lemmas, refreshed_pairs, refreshed_sig = build_new_lemmas(tokens)
        if refreshed_sig != new_sig or len(refreshed_lemmas) != len(new_lemmas):
            print("WARNING: Determinism check failed after rebuild; signature changed unexpectedly.")
            return 3

        print("Rebuild committed.")
        print(f"Final lemma count: {len(new_lemmas)}")
        print(f"Final signature: {new_sig}")
        return 0
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    if args.command == "rebuild-lemmas":
        return command_rebuild_lemmas(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
