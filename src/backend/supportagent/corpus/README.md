# Corpus generator

Generates the Confluence/Jira knowledge base **and its gold evaluation set** from
one world model (`world_model.yaml`).

## Why

Hand-written seed content gives a corpus small enough that retrieval never fails:
every configuration scores perfectly, so chunking, hybrid search, `top_k` and
rerankers cannot be compared. Difficulty has to be built in deliberately.

## The invariant everything rests on

**Every fact variant is stated in exactly one place.** The generator records that
place in `Corpus.homes`, which is what lets `evalgen` compute labels instead of
requiring annotation:

| label | derived from |
|---|---|
| `expected_sources` | the fact's canonical home |
| `must_not_use` | sibling tariff pages, superseded archive pages, restricted pages |
| `expect_refusal` | restricted facts, out-of-scope questions |
| `expected_answer` | the variant's value |

Adding a product to the world model therefore adds documents *and* graded
questions. `tests/unit/corpus/` asserts the invariant so the labels cannot rot
silently.

## Where difficulty comes from

- **tariff variants** — near-identical pages differing in one value: high lexical
  overlap, only one is right
- **superseded editions** — an outdated value stays retrievable in the archive
- **`placement: jira_only`** — the answer exists only in a Jira resolution comment
- **`visibility: restricted`** — the answer exists but must never reach the asker
- **distractor issues** — Jira issues that discuss an attribute and point at the
  authoritative page without restating the value
- **noise issues** — operational chatter carrying no answerable fact
- **`out_of_scope`** — plausible questions nothing can answer

## Usage

```bash
python -m supportagent.corpus --stats-only          # inspect
python -m supportagent.corpus                       # write files
python -m supportagent.corpus --jira-patterns-per-variant 4 --noise-issues 60
```

Writes `data/corpus/{projects,confluence_pages,jira_issues}.json` (gitignored) and
`evals/rag_qa.generated.jsonl` (committed — it is an asset, not a build artifact).

Page and issue shapes match what `supportagent.seed` consumes, so publishing is a
matter of pointing the seeder at the generated files. Generation stays local on
purpose: creating hundreds of pages in a live Confluence tenant should be an
explicit action, not a side effect.

## Scaling

Jira volume scales with `--jira-patterns-per-variant` (76 issues at 1, 259 at 4).
Page and gold-case volume scale with the number of facts in `world_model.yaml` —
that axis is content work, and it is where the remaining effort belongs.
