
# Republic Data Artifact

This folder contains the canonical source text and the derived database representation of Plato’s *Republic*.

It includes:

* The original TEI XML source
* The structured SQLite database built from that source

These files are deterministic artifacts. They can be rebuilt using the Hermes builder scripts.

---

# Contents

## 1. TEI Source File

The TEI XML file is the canonical Greek source text from the Perseus Digital Library’s `canonical-greekLit` repository.

It contains:

* Full Greek text
* Structured markup
* Stephanus milestone references
* Canonical identifiers

This file is the textual foundation for the database build process.

It is not modified by Hermes.

---

## 2. republic.db

This SQLite database is a structured representation of the TEI text.

It contains two implemented layers:

* Canonical segmentation
* Lexical (lemma) indexing

It is built, not hand-edited.

If necessary, it can be rebuilt from the TEI file using:

* `Hermes.Canonicalizer` (Layer 1)
* `Hermes.MorphBuilder` (Layer 2 — lemma indexing only)

---

# Database Structure

The database contains four tables:

* `Chunk`
* `Token`
* `Lemma`
* `TokenLemma`

---

## Chunk

Represents canonical text segments aligned to Stephanus references.

Columns:

* `ChunkId`
* `Sequence`
* `MilestoneRef`
* `CanonicalRef`
* `GreekText`

Each row corresponds to a Stephanus-aligned unit of the dialogue.

---

## Token

Represents individual word occurrences within a chunk.

Columns:

* `TokenId`
* `ChunkId`
* `Position`
* `SurfaceForm`

Each token preserves exact textual position.

---

## Lemma

Represents normalized dictionary forms.

Columns:

* `LemmaId`
* `LemmaText`

Each lemma appears once.

---

## TokenLemma

Maps each token to its lemma.

Columns:

* `TokenId`
* `LemmaId`

This table enables lexical recurrence analysis.

---

# What Is Not Included

This database does not store:

* Morphological parsing
* Tense, case, mood, etc.
* Etymological roots
* Dictionary definitions
* Interpretive annotations

Those belong to external systems or future conceptual layers.

---

# Rebuildability

The database is fully rebuildable from the TEI source.

The TEI file is the authoritative text.

The SQLite file is a structured projection of that text.

If the TEI source changes, the database should be rebuilt rather than edited manually.

---

# Design Intent

This folder represents a stable textual substrate.

It is meant to support:

* Canonical traversal
* Lexical recurrence tracing
* Structural analysis

It is not an interpretive engine.

It is the foundation upon which interpretation can be built.
