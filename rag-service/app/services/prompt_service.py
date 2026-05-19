from pathlib import Path

from app.core.config import settings
from app.schemas.rag import Citation


def _read_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_system_prompt() -> str:
    return _read_prompt(settings.SYSTEM_PROMPT_PATH)


def render_user_prompt(query: str, citations: list[Citation]) -> str:
    template = _read_prompt(settings.USER_PROMPT_PATH)
    context_blocks = []
    for index, citation in enumerate(citations[:5], start=1):
        article = f" | Điều/khoản: {citation.article}" if citation.article else ""
        source_url = f" | URL: {citation.source_url}" if citation.source_url else ""
        context_blocks.append(
            f"[Nguồn {index}] {citation.title}{article} | Score: {citation.score}{source_url}\n"
            f"{citation.snippet}"
        )
    context_text = "\n\n".join(context_blocks) if context_blocks else "Không có ngữ cảnh truy xuất được."
    return template.format(
        query=query.strip(),
        retrieved_context=context_text,
    )
