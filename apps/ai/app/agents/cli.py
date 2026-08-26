"""Run one synthetic audit through the complete C11 graph."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv

from app.agents import AgentDependencies, DocumentRef, build_audit_graph, initial_audit_state
from app.agents.documents import FallbackPdfDocumentProcessor
from app.agents.investigator import OpenAIInvestigatorModel
from app.embeddings import OpenAIEmbeddingClient
from app.llm import CachedLLMClient, OpenAIResponsesClient
from app.retrieval import PostgresRuleStore, RegulationRetriever, load_corpus
from app.retrieval.database import managed_database_engine
from app.retrieval.ingest import ingest_chunks
from app.schemas.ground_truth import GroundTruthCase
from app.schemas.mortgage import CanonicalModel, MortgageAccount
from app.tools import ToolDependencies
from app.tools.dependencies import (
    AuditRecord,
    InMemoryAuditDataSource,
    InMemoryMissingInformationSink,
)
from app.tools.engine import EngineFinding, HttpReconciliationEngine

DOCUMENT_IDS = {
    "old_servicer_statement.pdf": "doc_old_servicer_statement",
    "new_servicer_statement.pdf": "doc_new_servicer_statement",
    "transfer_notice.pdf": "doc_transfer_notice",
    "escrow_analysis.pdf": "doc_escrow_analysis",
    "property_tax_bill.pdf": "doc_property_tax_bill",
}


class AuditRunResult(CanonicalModel):
    audit_id: str
    account_id: str
    status: Literal["COMPLETE", "REQUIRES_REVIEW"]
    findings: list[EngineFinding]
    missing_information: list[str]
    steps_used: int
    cost_usd: Decimal
    trace_path: Path


def load_case(path: Path, case_id: str) -> GroundTruthCase:
    cases = [
        GroundTruthCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [case for case in cases if case.case_id == case_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one ground-truth case {case_id}; found {len(matches)}")
    return matches[0]


def load_account(path: Path, account_id: str) -> MortgageAccount:
    suffix = account_id.removeprefix("SS-")
    account_path = path / f"account-{suffix}.json"
    if not account_path.is_file():
        raise ValueError(f"account file does not exist: {account_path}")
    account = MortgageAccount.model_validate_json(account_path.read_text(encoding="utf-8"))
    if account.account_id != account_id:
        raise ValueError(f"account file contains {account.account_id}; expected {account_id}")
    return account


def document_refs(root: Path, audit_id: str, account_id: str) -> list[DocumentRef]:
    account_root = root / account_id
    return [
        DocumentRef(
            audit_id=audit_id,
            document_id=document_id,
            path=account_root / filename,
        )
        for filename, document_id in DOCUMENT_IDS.items()
    ]


def run_audit(args: argparse.Namespace) -> AuditRunResult:
    case = load_case(args.ground_truth, args.case)
    account = load_account(args.accounts, case.account_id)
    documents = document_refs(args.documents, case.case_id, case.account_id)
    source = InMemoryAuditDataSource(
        [AuditRecord(audit_id=case.case_id, account=account)],
        [],
    )
    missing = InMemoryMissingInformationSink()
    embeddings = OpenAIEmbeddingClient.from_env()
    investigator = OpenAIInvestigatorModel.from_env()
    extraction_provider = OpenAIResponsesClient.from_env()
    extraction_client = CachedLLMClient(
        extraction_provider,
        args.extraction_cache,
        namespace=(
            f"{extraction_provider.api_base}|{extraction_provider.model}|c8-provider-v2"
        ),
    )
    with managed_database_engine() as engine:
        corpus = load_corpus(args.corpus)
        ingest_chunks(corpus, embeddings, engine)
        regulations = RegulationRetriever(PostgresRuleStore(engine), embeddings)
        tools = ToolDependencies(
            audit_data=source,
            engine=HttpReconciliationEngine.from_env(),
            regulations=regulations,
            missing_information=missing,
        )
        graph = build_audit_graph(
            AgentDependencies(
                tools=tools,
                document_store=source,
                documents=FallbackPdfDocumentProcessor(extraction_client),
                investigator=investigator,
                trace_root=args.trace_dir,
            )
        )
        state = initial_audit_state(case.case_id, documents)
        result = graph.invoke(
            state,
            {"configurable": {"thread_id": str(uuid4())}},
        )
    requires_review = bool(result["requires_review"] or "__interrupt__" in result)
    return AuditRunResult(
        audit_id=case.case_id,
        account_id=account.account_id,
        status="REQUIRES_REVIEW" if requires_review else "COMPLETE",
        findings=result["final_findings"],
        missing_information=result["missing_information"],
        steps_used=result["steps_used"],
        cost_usd=result["cost_usd"],
        trace_path=args.trace_dir / f"{case.case_id}.jsonl",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth/cases.jsonl"),
    )
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument("--corpus", type=Path, default=Path("knowledge-base/chunks.jsonl"))
    parser.add_argument("--trace-dir", type=Path, default=Path("data/traces"))
    parser.add_argument(
        "--extraction-cache",
        type=Path,
        default=Path("data/traces/extraction_llm_cache.jsonl"),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    result = run_audit(_parse_args())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
