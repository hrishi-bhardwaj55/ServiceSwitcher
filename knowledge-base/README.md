# Knowledge base

`chunks.jsonl` contains 47 concise, retrieval-sized summaries curated from current
primary sources:

- 12 CFR § 1024.17, escrow accounts;
- 12 CFR § 1024.33, mortgage servicing transfers;
- 12 CFR § 1024.38, general servicing policies and procedures;
- CFPB Bulletin 2014-01, mortgage servicing transfer guidance.

Every record has a stable `id`, `source`, `section`, `title`, `url`, and `content`.
The content is a faithful operational summary rather than a legal conclusion or a
substitute for the linked source. `apps/ai/app/retrieval/corpus.py` rejects malformed
metadata, non-CFPB URLs, duplicate IDs, and corpora outside the required 30–50 chunk
range.
