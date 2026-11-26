from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.outbound.embeddings.openai_compatible import OpenAICompatibleEmbedder
from app.adapters.outbound.persistence.repositories.retrieval_repository import (
    RetrievalRepository,
)
from app.application.retrieve import RetrieveChunksUseCase
from app.core.config import get_settings
from app.core.database import get_sqlalchemy_url
from app.domain.chunking import DEFAULT_MAX_CHARS

_FIELDNAMES = [
    "pregunta",
    "tipo",
    "adr_esperado",
    "top1_correcto",
    "posicion_del_correcto",
    "similitud_top1",
]


@dataclass(frozen=True)
class EvalQuestion:
    question: str
    type: str
    expected_adr_code: str | None


def load_questions(path: Path) -> list[EvalQuestion]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalQuestion(item["question"], item["type"], item["expected_adr_code"])
        for item in raw
    ]


def build_results_table(
    use_case: RetrieveChunksUseCase, questions: list[EvalQuestion], top_k: int
) -> list[dict[str, object]]:
    """Runs every seed question through retrieval and reports, per question,
    whether the expected ADR landed in the top-1 and at what rank it
    appeared in the top-k, so threshold decisions aren't made by eye."""
    rows = []
    for eval_question in questions:
        chunks = use_case.execute(eval_question.question, top_k=top_k)
        similarity_top1 = chunks[0].similarity if chunks else None

        if eval_question.expected_adr_code is None:
            top1_correct: bool | str = "n/a"
            position: int | str = "n/a"
        else:
            top1_correct = bool(chunks) and (
                chunks[0].adr_code == eval_question.expected_adr_code
            )
            position = next(
                (
                    rank
                    for rank, chunk in enumerate(chunks, start=1)
                    if chunk.adr_code == eval_question.expected_adr_code
                ),
                "not_found",
            )

        rows.append(
            {
                "pregunta": eval_question.question,
                "tipo": eval_question.type,
                "adr_esperado": eval_question.expected_adr_code or "(ninguno)",
                "top1_correcto": top1_correct,
                "posicion_del_correcto": position,
                "similitud_top1": (
                    round(similarity_top1, 4) if similarity_top1 is not None else None
                ),
            }
        )
    return rows


def print_results_table(rows: list[dict[str, object]]) -> None:
    widths = {"pregunta": 60, "tipo": 14, "adr_esperado": 13, "top1_correcto": 9}
    header = (
        f"{'Pregunta':<{widths['pregunta']}} {'Tipo':<{widths['tipo']}} "
        f"{'ADR esperado':<{widths['adr_esperado']}} "
        f"{'Top-1 ok':<{widths['top1_correcto']}} {'Posición':<8} Similitud top-1"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        pregunta = row["pregunta"]
        if len(pregunta) > widths["pregunta"]:
            pregunta = pregunta[: widths["pregunta"] - 3] + "..."
        print(
            f"{pregunta:<{widths['pregunta']}} {row['tipo']:<{widths['tipo']}} "
            f"{row['adr_esperado']:<{widths['adr_esperado']}} "
            f"{row['top1_correcto']!s:<{widths['top1_correcto']}} "
            f"{row['posicion_del_correcto']!s:<8} {row['similitud_top1']}"
        )


def print_similarity_overlap(rows: list[dict[str, object]]) -> None:
    answered = [
        row["similitud_top1"]
        for row in rows
        if row["adr_esperado"] != "(ninguno)" and row["similitud_top1"] is not None
    ]
    unanswered = [
        row["similitud_top1"]
        for row in rows
        if row["adr_esperado"] == "(ninguno)" and row["similitud_top1"] is not None
    ]

    print()
    if answered:
        print(
            f"Con respuesta esperada ({len(answered)}): "
            f"similitud top-1 entre {min(answered):.4f} y {max(answered):.4f}"
        )
    if unanswered:
        print(
            f"Sin respuesta esperada ({len(unanswered)}): "
            f"similitud top-1 entre {min(unanswered):.4f} y {max(unanswered):.4f}"
        )
    if answered and unanswered and min(answered) <= max(unanswered):
        print(
            "Se solapan: ningún umbral fijo de similitud separa las preguntas "
            "sin respuesta de las que sí tienen una."
        )


def save_results_table(rows: list[dict[str, object]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the retrieval eval seed questions and report accuracy."
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("scripts/retrieval_eval_questions.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("scripts/retrieval_eval_results.csv")
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument(
        "--contextual-header",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Must match the strategy used at ingestion time, or nothing matches.",
    )
    args = parser.parse_args()

    questions = load_questions(args.questions)

    settings = get_settings()
    embedder = OpenAICompatibleEmbedder.from_settings(settings)

    engine = create_engine(get_sqlalchemy_url())
    with Session(engine) as session:
        repository = RetrievalRepository(session)
        use_case = RetrieveChunksUseCase(
            embedder,
            repository,
            max_chars=args.max_chars,
            contextual_header=args.contextual_header,
        )
        rows = build_results_table(use_case, questions, args.top_k)
    engine.dispose()

    print_results_table(rows)
    print_similarity_overlap(rows)
    save_results_table(rows, args.output)
    print(f"\nTabla guardada en {args.output}")


if __name__ == "__main__":
    main()
