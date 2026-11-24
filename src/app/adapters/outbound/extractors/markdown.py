from pathlib import Path


class MarkdownFileExtractor:
  """Implementación de DocumentExtractorPort para archivos .md."""

  def extract_markdown(self, source: Path) -> str:
    if not source.exists():
      raise FileNotFoundError(f"Archivo no encontrado: {source}")
    return source.read_text(encoding="utf-8")