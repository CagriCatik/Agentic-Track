# Scaling a RAG System: Indexing Strategies, Retrieval Evaluation, and Corpus Growth

> How should a RAG system index and manage its documents as the corpus continuously grows, without unnecessarily recomputing everything while still maintaining high retrieval quality?

A RAG system is a bit like a library run by robots. The robots slice documents into pieces, convert those pieces into vectors (embeddings), and store them in a vector database so that later a query can retrieve the most relevant pieces. As the corpus grows, the question becomes: how should indexing evolve so the system remains accurate and efficient?

The naive idea is to **reindex everything every time the corpus changes**. That works, but it becomes extremely expensive and slow as the corpus grows. Most production systems avoid this and instead rely on **incremental indexing and change detection**.

---

First, consider the three typical situations that occur when a corpus grows.

If **new documents are added**, the correct approach is **incremental indexing**.
Only the new documents are processed.

The pipeline usually looks like this:

1. A document is ingested.
2. It is split into chunks (for example 300–800 tokens).
3. Each chunk is converted into an embedding vector.
4. The vectors are inserted into the vector database.

No existing data needs to be touched. This keeps indexing fast and cheap.

---

If **existing documents change**, then you use **selective reindexing**.

A practical way to do this is by using a **content hash**. A hash is a short fingerprint of the document content (for example SHA-256). If the content changes, the hash changes.

The pipeline becomes:

1. Compute a hash of the document.
2. Compare it with the hash stored during the last indexing.
3. If the hash is the same → skip the document.
4. If the hash changed → delete the old chunks for that document.
5. Re-chunk and re-embed the document.
6. Insert the new vectors.

This prevents unnecessary re-embedding.

---

If **the indexing strategy itself changes**, then a **full reindex** is often necessary.

Examples include:

* changing the embedding model
* changing chunk size or chunking logic
* changing metadata structure
* switching vector databases
* changing tokenization assumptions

Embeddings from different models are not compatible in the same vector space. If the embedding model changes, the old vectors often become unreliable. In that situation a complete rebuild of the index is the safest solution.

---

As the corpus grows, the bigger challenge is often not indexing but **retrieval quality**. Large corpora make it harder to retrieve the right chunks.

To evaluate retrieval performance, several metrics are commonly used.

---

**Recall@k**

Recall measures whether the correct information appears among the retrieved results.

If the system retrieves the top **k** chunks, recall asks:

“Did we retrieve the correct chunk at all?”

Example:

* correct chunk exists
* system retrieves top 5 chunks
* the correct chunk is among them

Then **Recall@5 = 1 (success)**.

If the correct chunk is not in the top 5 results:

**Recall@5 = 0 (failure)**.

High recall means the system is able to find the relevant information somewhere in its retrieved set.

---

**MRR (Mean Reciprocal Rank)**

MRR measures **how early the correct result appears**.

The reciprocal rank is:

1 / rank

Example:

correct chunk is at position 1 → score = 1/1 = 1
correct chunk is at position 2 → score = 1/2 = 0.5
correct chunk is at position 5 → score = 1/5 = 0.2

If the correct chunk is missing entirely, the score is 0.

The **mean** reciprocal rank is the average across many queries.

MRR rewards systems that return the correct result **very early in the ranking**, which matters because RAG pipelines often only pass the top few chunks to the LLM.

---

**nDCG (Normalized Discounted Cumulative Gain)**

nDCG measures **ranking quality when multiple results may be relevant**.

It considers two ideas:

1. Relevant results are better than irrelevant ones.
2. Results appearing earlier in the ranking matter more.

The “discount” means lower-ranked results contribute less value.

Example idea:

rank 1 result → very important
rank 5 result → less important
rank 20 result → almost irrelevant

nDCG also normalizes the score so that values range between 0 and 1.

A score close to **1** means the ranking is nearly optimal.

This metric is useful when multiple chunks may contain useful information rather than a single perfect answer.

---

As the corpus grows, several architectural practices become important.

One important technique is **index versioning**.

Instead of modifying the active index directly, systems often build a new index version:

```
kb_v1
kb_v2
kb_v3
```

The new index is built in parallel, tested, and then traffic is switched to it. If something fails, the system can roll back to the previous version.

---

Another useful design pattern is **hybrid retrieval**.

Vector search captures semantic similarity, but it sometimes misses exact keyword matches. Hybrid systems combine two retrieval methods:

semantic vector search
keyword search (BM25 or similar)

The results are merged and optionally reranked using a neural reranker. This typically improves retrieval quality in large corpora.

---

Duplicate and outdated content also become a problem as the corpus grows.

If many chunks contain almost identical text, the vector database can return multiple nearly identical results. This wastes context window space and reduces answer quality.

Typical mitigation strategies include:

* deduplicating documents during ingestion
* keeping document version metadata
* filtering out outdated versions
* removing boilerplate text

---

A typical **production RAG indexing pipeline** often follows this structure:

Document ingestion
→ compute document hash
→ compare with stored hash
→ skip if unchanged
→ chunk document
→ generate embeddings
→ attach metadata (doc_id, version, timestamp)
→ upsert vectors into the database

Periodic evaluation then measures retrieval performance using recall, MRR, or nDCG.

---

The core idea is simple but powerful:
**Only reindex what actually changed, and measure retrieval quality continuously.**

Full reindexing becomes an occasional maintenance task rather than the default workflow.

As the corpus grows into hundreds of thousands or millions of chunks, careful indexing strategy matters less than something deeper: how well the system organizes knowledge. Chunk structure, metadata design, and retrieval evaluation gradually become the real engineering work behind effective RAG systems.
