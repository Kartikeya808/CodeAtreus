Implement Phase 1 of the CodeAtreus backend as per the execution plan.

Auth endpoints:
*   GitHub OAuth login
*   Refresh JWT access token
*   Return current authenticated user

Repository Import endpoints:
*   Accept GitHub URL, validate, detect default branch
*   List user's repos (powers dashboard page)
*   Repo detail (powers overview page)
*   Delete a repo record

Indexing Pipeline tasks:
*   Clone repo via GitPython (shallow clone, enforce size/time limits)
*   Ignore node_modules, dist, .git, binaries, lockfiles above size threshold
*   Tree-sitter parsing per language -> AST -> symbol table (functions, classes, imports)
*   Metadata extraction: framework detection (package.json/pyproject/pom.xml heuristics), entry points, file counts
*   Chunk code at function/class granularity -> generate embeddings (BGE-Small/Jina) -> upsert into ChromaDB collection per repo

Project Overview endpoint:
*   Language %, framework, entry points, key files, health score

Chat endpoints:
*   Retrieve top-k chunks from ChromaDB, call LLM via OpenRouter, return answer + cited file paths
*   Fetch prior chat messages for a repo session