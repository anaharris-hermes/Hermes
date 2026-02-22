
# Hermes

Hermes is a layered textual infrastructure for Plato’s Greek corpus. It provides canonical segmentation and lemma-indexed lexical structure in a deterministic, rebuildable SQLite database. Hermes is designed not as a standalone interpreter, but as a structured substrate for disciplined, AI-assisted analysis.

The system establishes textual boundaries — canonical references, lexical recurrence, and structural position — so that interpretive reasoning, whether human or AI-assisted, remains anchored to the text itself. Hermes does not generate interpretation. It constrains it.

---

# Purpose

Hermes exists to separate text from interpretation.

When claims are made about Plato, Hermes provides the structural substrate necessary to:

* Locate the passage precisely.
* Trace lexical recurrence across the corpus.
* Examine vocabulary distribution and structural movement.
* Question interpretive assertions against the actual text.

Hermes is an enforcement layer. It ensures that interpretation operates within defined textual boundaries rather than detached from them.

---

# Architectural Principles

Hermes follows five core principles:

1. Canonical Stability
   Text is aligned to established reference systems (e.g., Stephanus) and is deterministically rebuildable from TEI sources.

2. Layer Separation
   Canonical text, lexical abstraction, and interpretive reasoning remain distinct layers.

3. Determinism
   Foundational layers do not embed probabilistic tagging or speculative grammatical interpretation.

4. Minimalism
   Only necessary structural data is stored.

5. Traversability
   The system serves as a structured instrument for navigating Plato’s corpus.

---

# Implemented Layers

Hermes currently implements two foundational layers.

## Layer 1 — Canonical Text

The canonical layer stores the Greek text segmented by established reference systems.

### Table: `Chunk`

* `ChunkId` — unique identifier
* `Sequence` — global order across the corpus
* `MilestoneRef` — canonical reference (e.g., 327a)
* `CanonicalRef` — CTS-style identifier
* `GreekText` — full Greek text of the segment

This layer is fixed and rebuildable from TEI source files.

It answers:

* What is the text?
* Where is it located?
* What is its canonical position?

---

## Layer 2 — Lexical (Lemma) Layer

The lexical layer maps surface word forms to dictionary lemmas.

### Table: `Token`

Represents a word occurrence.

* `TokenId`
* `ChunkId` (FK → Chunk)
* `Position` (within chunk)
* `SurfaceForm` (exact word form)

Each token preserves textual order and position.

---

### Table: `Lemma`

Represents normalized dictionary forms.

* `LemmaId`
* `LemmaText` (unique)

Each lemma appears once.

---

### Table: `TokenLemma`

Maps tokens to their lemma.

* `TokenId` (FK → Token)
* `LemmaId` (FK → Lemma)

This layer enables:

* Recurrence tracing (e.g., tracking καταβαίνω across dialogues)
* Vocabulary distribution analysis
* Structural clustering by lexical unit
* Frequency studies across the corpus

---

# What Hermes Does Not Do

Hermes intentionally does not:

* Perform morphological parsing
* Store tense, case, mood, or grammatical features
* Infer etymological roots
* Provide dictionary definitions
* Perform statistical or generative interpretation

Those functions belong to external linguistic systems.

Hermes focuses on textual stability and lexical structure.

---

# AI Integration

Hermes is designed as a substrate for AI-assisted reasoning, not as an autonomous interpretive system.

AI models operating on Hermes:

* Do not hallucinate passages.
* Do not operate on unstructured text.
* Must answer to canonical segmentation.
* Can trace lexical recurrence deterministically.
* Can question interpretive claims against the text.

Hermes constrains AI systems to the corpus and exposes the structural layers upon which interpretation depends.

Interpretation remains accountable to the text.

---

# Data and Rebuildability

All database artifacts are stored under:

```
data/
```

These files are:

* Deterministically rebuildable
* Derived from TEI sources
* Not manually edited

Builder scripts regenerate the database from canonical source material.

---

# Scope

Hermes is designed for Plato’s Greek corpus and is extensible to additional dialogues or classical texts using the same layered model.

The system does not aim to replace philology. It provides structured infrastructure upon which philological and interpretive work can be conducted with precision.

---

Hermes is not a commentary.

It is not an opinion.

It is a substrate.

And interpretation must answer to it.

# Attrubution

The Greek text contained in this repository is derived from the Perseus Digital Library’s canonical-greekLit TEI corpus. Plato’s works are in the public domain. The TEI markup and digital edition are provided by Perseus and remain subject to their original licensing terms.

Hermes stores a structured database representation of this text for canonical and lexical traversal. The database is a derived artifact and does not assert ownership over the original text.

## Third-Party Resources

Hermes does not redistribute proprietary lexica, morphological engines, or external linguistic databases.

The system does not bundle or embed:

- Perseus Morpheus
- Logeion
- LSJ or other dictionary content
- Treebank or morphological datasets

Hermes stores only:

- Canonical text derived from public-domain sources

- Deterministically generated structural metadata (chunking and lemma indexing)

- Any external linguistic tools used during development (e.g., lemmatizers) are not included in the repository and remain subject to their respective licenses.

Hermes provides structured textual infrastructure. It does not replicate or redistribute external scholarly resources.