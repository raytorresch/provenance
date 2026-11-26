import re

from app.domain.entities import ChunkData

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")

CHUNKING_ALGORITHM = "by_heading_v1"
DEFAULT_MAX_CHARS = 1500


def build_chunking_strategy(
    max_chars: int = DEFAULT_MAX_CHARS, *, contextual_header: bool
) -> str:
    """Encodes the algorithm name and every parameter that changes what gets
    stored under this label. If max_chars or the header-injection choice
    changes, the label changes with it, instead of silently reusing chunks
    produced under a different configuration."""
    header_flag = 1 if contextual_header else 0
    return f"{CHUNKING_ALGORITHM}:max={max_chars}:hdr={header_flag}"


def _split_long_section(text: str, max_chars: int) -> list[str]:
    """Divide una sección larga por párrafos sin romper bloques de código.

    max_chars es un techo duro salvo por un único caso: un bloque atómico
    (un párrafo o un bloque ``` ``` sin líneas en blanco internas) que por
    sí solo ya supera max_chars se mantiene entero, porque esta función no
    rompe bloques atómicos.
    """
    if len(text) <= max_chars:
        return [text]

    # Agrupar bloques atómicos (párrafos normales o bloques ```...``` completos)
    blocks: list[str] = []
    current_block: list[str] = []
    in_code = False

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_code = not in_code
            current_block.append(line)
            continue

        if not in_code and stripped == "":
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
        else:
            current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block))

    # Ensamblar sub-chunks respetando max_chars con 1 bloque de overlap
    parts: list[str] = []
    current_part: list[str] = []
    current_len = 0

    for block in blocks:
        block_len = len(block)
        # Si agregar este bloque excede el límite y ya tenemos contenido, cerramos parte
        if current_part and current_len + block_len + 2 > max_chars:
            parts.append("\n\n".join(current_part))
            # Overlap: conservamos el último bloque como contexto del
            # siguiente part, pero solo si cabe junto al bloque que lo
            # dispara; si no, el overlap por sí solo volvería a desbordar
            # max_chars (el bloque disparador ya se comprobó solo, no junto
            # al overlap).
            last_block = current_part[-1]
            overlap = (
                last_block
                if len(last_block) < max_chars // 2
                and len(last_block) + block_len + 2 <= max_chars
                else ""
            )
            current_part = [overlap] if overlap else []
            current_len = len(overlap)

        current_part.append(block)
        current_len += block_len + 2

    if current_part:
        parts.append("\n\n".join(current_part))

    return parts


def chunk_markdown(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[ChunkData]:
    """Divide un documento Markdown (ADR) en chunks semánticos con ruta de encabezados."""
    h1: str | None = None
    h2: str | None = None
    h3: str | None = None

    buffer: list[str] = []
    raw_sections: list[tuple[str, str]] = []
    in_code_block = False

    def current_path() -> str:
        levels = [lvl for lvl in (h1, h2, h3) if lvl]
        return " > ".join(levels) if levels else "Preamble"

    def flush_buffer() -> None:
        content = "\n".join(buffer).strip()
        if content:
            raw_sections.append((current_path(), content))
        buffer.clear()

    for line in text.splitlines():
        stripped = line.lstrip()

        # Detectar apertura o cierre de bloques de código
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            buffer.append(line)
            continue

        # Solo evaluar encabezados fuera de bloques de código
        if not in_code_block:
            match = _HEADING_RE.match(stripped)
            if match:
                flush_buffer()
                hashes, title = match.groups()
                # Headings often carry a trailing ":" in the source ADR
                # ("## Context:"), which must not leak into heading_path.
                clean_title = title.strip().rstrip(":").strip()
                level = len(hashes)

                if level == 1:
                    h1, h2, h3 = clean_title, None, None
                elif level == 2:
                    h2, h3 = clean_title, None
                elif level == 3:
                    h3 = clean_title
                continue

        buffer.append(line)

    # Vaciar el contenido restante al final del archivo
    flush_buffer()

    # Subdividir secciones muy largas y asignar ordinal secuencial
    chunks: list[ChunkData] = []
    ordinal = 0
    for path, content in raw_sections:
        for sub_content in _split_long_section(content, max_chars=max_chars):
            chunks.append(
                ChunkData(
                    ordinal=ordinal,
                    heading_path=path,
                    content=sub_content,
                )
            )
            ordinal += 1

    return chunks
