"""The 7-step indexing pipeline (matches the frontend PIPELINE_STEPS)."""
from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.index_job import IndexJob
from app.models.repo import Repo
from app.services.indexing.chunker import chunk_files
from app.services.indexing.clone import clone_repo
from app.services.indexing.graph import build_graph
from app.services.indexing.metadata import extract_metadata
from app.services.indexing.progress import ProgressReporter
from app.services.indexing.symbols import extract_symbols
from app.services.indexing.walk import walk_repo
from app.services.vectorstore import VectorStore

logger = get_logger("indexing.pipeline")


def run_index_pipeline(repo_id: str, job_id: str) -> None:
    """Execute the full pipeline for a repo. Owns its own DB session."""
    db = SessionLocal()
    try:
        repo = db.get(Repo, repo_id)
        job = db.get(IndexJob, job_id)
        if repo is None or job is None:
            logger.error("pipeline: repo/job missing (%s/%s)", repo_id, job_id)
            return

        reporter = ProgressReporter(db, job, repo)
        reporter.start()

        # 1 — Git Clone
        reporter.step(1, "Git Clone", f"Cloning {repo.full_name}…")
        clone_path = clone_repo(repo.github_url, repo.default_branch, repo.id)
        repo.local_path = str(clone_path)
        walk = walk_repo(clone_path)
        reporter.log(f"Cloned {walk.file_count} source files ({walk.total_bytes // 1024} KB)")

        # 2 — AST Parsing
        reporter.step(2, "AST Parsing", "Building symbol tables…")
        symbols = extract_symbols(walk.files)
        n_funcs = sum(len(s.functions) for s in symbols)
        n_classes = sum(len(s.classes) for s in symbols)
        reporter.log(f"Parsed {len(symbols)} files — {n_funcs} functions, {n_classes} classes")

        # 3 — Metadata Extraction
        reporter.step(3, "Metadata Extraction", "Detecting framework & key files…")
        meta = extract_metadata(clone_path, walk)
        lang_dist = walk.language_distribution()
        repo.primary_language = meta.primary_language
        repo.framework = meta.framework
        repo.file_count = walk.file_count
        repo.size_bytes = walk.total_bytes
        repo.health_score = meta.health_score
        repo.architecture = None  # invalidate cached summary on re-index
        repo.overview = {
            "language_dist": lang_dist,
            "framework": meta.framework,
            "file_count": walk.file_count,
            "size": _humanize(walk.total_bytes),
            "health": meta.health_score,
            "entry_points": meta.entry_points,
            "key_files": meta.key_files,
            "symbol_counts": {"functions": n_funcs, "classes": n_classes},
        }
        reporter.log(f"Detected {meta.framework} · primary language {meta.primary_language}")

        # 4 — Embedding Generation
        reporter.step(4, "Embedding Generation", "Chunking & embedding code…")
        chunks = chunk_files(walk.files)
        collection = f"repo_{repo.id.replace('-', '')}"
        store = VectorStore(collection)
        store.add_chunks(chunks)
        repo.chroma_collection = collection
        reporter.log(f"Embedded {len(chunks)} code chunks into collection {collection}")

        # 5 — Dependency Analysis
        reporter.step(5, "Dependency Analysis", "Resolving module imports…")
        graph = build_graph(symbols)
        reporter.log(
            f"Resolved {len(graph['edges'])} dependencies "
            f"across {len(graph['nodes'])} modules"
        )

        # 6 — Knowledge Graph
        reporter.step(6, "Knowledge Graph", "Assembling knowledge graph…")
        repo.graph = graph
        reporter.log("Knowledge graph persisted")

        # 7 — Ready
        reporter.complete()
        logger.info("indexing complete for %s", repo.full_name)
    except Exception as exc:  # noqa: BLE001 - surface failure to the job row
        logger.exception("indexing failed for %s", repo_id)
        try:
            repo = db.get(Repo, repo_id)
            job = db.get(IndexJob, job_id)
            if repo and job:
                ProgressReporter(db, job, repo).fail(str(exc))
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


def _humanize(size_bytes: int) -> str:
    from app.services.presenter import humanize_size

    return humanize_size(size_bytes)
