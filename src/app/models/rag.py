from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  pass


class Document(Base):
  __tablename__ = "documents"

  id: Mapped[int] = mapped_column(primary_key=True)
  adr_code: Mapped[str] = mapped_column(
      String(32), unique=True, nullable=False
  )
  title: Mapped[str] = mapped_column(String(255), nullable=False)
  source_url: Mapped[str] = mapped_column(String(512), nullable=False)
  content_hash: Mapped[str] = mapped_column(
      String(64), unique=True, nullable=False
  )

  chunks: Mapped[list["Chunk"]] = relationship(
      back_populates="document", cascade="all, delete-orphan"
  )


class Chunk(Base):
  __tablename__ = "chunks"
  __table_args__ = (
      UniqueConstraint("document_id", "ordinal", name="uq_document_ordinal"),
  )

  id: Mapped[int] = mapped_column(primary_key=True)
  document_id: Mapped[int] = mapped_column(
      ForeignKey("documents.id", ondelete="CASCADE"), index=True
  )
  ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
  heading_path: Mapped[str] = mapped_column(String(512), nullable=False)
  content: Mapped[str] = mapped_column(Text, nullable=False)

  document: Mapped["Document"] = relationship(back_populates="chunks")
  embeddings: Mapped[list["ChunkEmbedding"]] = relationship(
      back_populates="chunk", cascade="all, delete-orphan"
  )


class ChunkEmbedding(Base):
  __tablename__ = "chunk_embeddings"
  __table_args__ = (
      UniqueConstraint("chunk_id", "model_name", name="uq_chunk_model"),
  )

  id: Mapped[int] = mapped_column(primary_key=True)
  chunk_id: Mapped[int] = mapped_column(
      ForeignKey("chunks.id", ondelete="CASCADE"), index=True
  )
  model_name: Mapped[str] = mapped_column(
      String(100), nullable=False, index=True
  )
  dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
  # Vector() sin argumento permite almacenar 3072, 1536 o 384 dims según el modelo
  embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)

  chunk: Mapped["Chunk"] = relationship(back_populates="embeddings")