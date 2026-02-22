import sqlite3
import sys
import uuid
from pathlib import Path

from cltk.lemmatize.grc import GreekBackoffLemmatizer


PUNCTUATION_CHARS = ".,;:?!\"'()[]{}<>/\\|`~!@#$%^&*-_=+·«»“”"


def default_db_path() -> Path:
    return (Path(__file__).resolve().parent.parent.parent / "data" / "plato" / "republic" / "republic.db").resolve()


def resolve_db_path() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return default_db_path()


def normalize_token(raw: str) -> str:
    return raw.strip(PUNCTUATION_CHARS)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in text.split():
        token = normalize_token(raw)
        if token:
            tokens.append(token)
    return tokens


def lemmatize_surface(lemmatizer: GreekBackoffLemmatizer, surface_form: str) -> str:
    result = lemmatizer.lemmatize([surface_form])
    if result and len(result[0]) > 1:
        lemma = (result[0][1] or "").strip()
        if lemma:
            return lemma
    return surface_form


def ensure_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS Token (
            TokenId TEXT PRIMARY KEY,
            ChunkId TEXT NOT NULL,
            Position INTEGER NOT NULL,
            SurfaceForm TEXT NOT NULL
        );
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS Lemma (
            LemmaId TEXT PRIMARY KEY,
            LemmaText TEXT NOT NULL UNIQUE
        );
        """
    )

    connection.execute("DROP TABLE IF EXISTS TokenMorphology;")
    connection.execute("DROP TABLE IF EXISTS TokenLemma;")
    connection.execute(
        """
        CREATE TABLE TokenLemma (
            TokenId TEXT NOT NULL,
            LemmaId TEXT NOT NULL,
            FOREIGN KEY (TokenId) REFERENCES Token(TokenId),
            FOREIGN KEY (LemmaId) REFERENCES Lemma(LemmaId)
        );
        """
    )


def clear_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM TokenLemma;")
    connection.execute("DELETE FROM Token;")
    connection.execute("DELETE FROM Lemma;")


def main() -> None:
    db_path = resolve_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    lemmatizer = GreekBackoffLemmatizer()

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        ensure_tables(connection)
        clear_tables(connection)

        chunks = connection.execute(
            "SELECT ChunkId, GreekText FROM Chunk ORDER BY Sequence;"
        ).fetchall()

        lemma_ids: dict[str, str] = {}
        total_tokens = 0
        total_mappings = 0

        for chunk_id, greek_text in chunks:
            position = 0
            for surface_form in tokenize(greek_text or ""):
                token_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO Token (TokenId, ChunkId, Position, SurfaceForm)
                    VALUES (?, ?, ?, ?);
                    """,
                    (token_id, chunk_id, position, surface_form),
                )

                lemma_text = lemmatize_surface(lemmatizer, surface_form)
                lemma_id = lemma_ids.get(lemma_text)
                if lemma_id is None:
                    lemma_id = str(uuid.uuid4())
                    lemma_ids[lemma_text] = lemma_id
                    connection.execute(
                        """
                        INSERT INTO Lemma (LemmaId, LemmaText)
                        VALUES (?, ?);
                        """,
                        (lemma_id, lemma_text),
                    )

                connection.execute(
                    """
                    INSERT INTO TokenLemma (TokenId, LemmaId)
                    VALUES (?, ?);
                    """,
                    (token_id, lemma_id),
                )

                total_tokens += 1
                total_mappings += 1
                position += 1

        connection.commit()

        print(f"Total tokens inserted: {total_tokens}")
        print(f"Total unique lemmas: {len(lemma_ids)}")
        print(f"Total token-lemma mappings inserted: {total_mappings}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
