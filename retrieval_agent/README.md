# Similar-Ticket Retrieval Agent

Finds historical tickets similar to a new one. **There is one ticket store: the knowledge base's
`ticket_records` table.** The agent has no table or ingestion of its own.

## Flow
1. Candidates = `ticket_records` rows with `curation_status` in (`AutoApproved`, `SMEApproved`) and an embedding
   (`database.py`; the row is mapped to the pipeline shape by `to_candidate`: module -> system, raw_text -> description,
   category -> ticket_type, resolution_type -> fix_path, title -> summary).
2. `pipeline.py` ranks them with BM25 + vector cosine fused by reciprocal rank fusion, plus small system/recency boosts.
3. The chat model reranks the top candidates and returns match strength, why similar, what differs and reusable info.
   Matches can only be IDs that were retrieved.

Ticket embeddings are created by `backend/step4_store_embeddings.py`. Their dimension is the `EMBEDDING_DIMENSIONS` env var (the repository's `sample.env` and `db/schema.sql` use 1536); query and stored vectors must match it. New tickets are embedded at query time with the same model/dimension.

KB card embeddings use the separate `KB_EMBEDDING_DIMENSIONS` setting (default 1536, matching the existing KB card vectors). The KB loader and resolver must use the same value; if existing vectors have a different size, re-embed the KB cards with `python scripts/kb_load.py` after setting the intended dimension.

## Config
Reads the repository root `.env` (`PG_*` or `AZURE_PG_*`, `AZURE_OPENAI_*`). Optional: `RETRIEVAL_MIN_SCORE` (0.68),
`RETRIEVAL_MIN_BM25_SCORE` (1.0), `RETRIEVAL_RRF_CONSTANT`, `RETRIEVAL_TEMPORAL_BOOST_DAYS`, `RETRIEVAL_TEMPORAL_BOOST_MAGNITUDE`.

## Run / test
```bash
uvicorn app.main:app --port 7000      # POST /retrieve and POST /api/tickets/similar
python -m unittest retrieval_agent.tests -v   # database-free
```
Not implemented yet: searching chat/RCA, release-note and runbook sources (tickets only for now).
