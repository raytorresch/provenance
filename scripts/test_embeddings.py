import os
from dotenv import load_dotenv
from openai import OpenAI
import math
from pgvector.psycopg import register_vector
import psycopg

load_dotenv()
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
models = [
    "text-embedding-3-small",
    "gemini-embedding-001"
]
# P R E D I C T I O N S
# The most similar ones
# - phrases 1 & 2 - offline-sync
# - phrases 3 & 4 - roles & permissions 
# - phrases 1 & 6 - sync and tenant isolation
# The most distant
# - phrase 5 cook recipe

# C O R P U S   S E L E C T I O N
sentences = [
    (
        "The mobile app syncs local database changes once network"
        " connectivity is restored."
    ),  # 0: Offline sync 1
    (
        "Offline data synchronization handles local queue conflicts"
        " automatically."
    ),  # 1: Offline sync 2
    (
        "Project administrators can assign custom roles and specific"
        " projects."
    ),  # 2: Roles/perms 1
    (
        "User access control restricts project modifications based on"
        " assigned roles."
    ),  # 3: Roles/perms 2
    (
        "To bake a chocolate cake, mix flour, sugar, cocoa powder, and"
        " eggs."
    ),  # 4: Cooking recipe
    (
        "Tenant data isolation ensures that organization boundaries cannot be"
        " crossed."
    ),  # 5: Org data isolation
]

print("Generating embeddings with model "+models[1]+"...")

# E M B E D D I N G S
response = client.embeddings.create(
    input=[s for s in sentences], model=models[1]
)

# extract response's vectors
vectors = [item.embedding for item in response.data]
#  C A L C U L A T I O N
#  Norms - Dot product - Cosine
def dot_product(v1, v2):
    return sum(a * b for a, b in zip(v1, v2))

def vector_norm(v):
  return math.sqrt(sum(a * a for a in v))

def cosine_similarity(v1, v2):
  dot = dot_product(v1, v2)
  n1 = vector_norm(v1)
  n2 = vector_norm(v2)
  # avoid division by zero for safety
  if n1 == 0 or n2 == 0:
    return 0.0
  return dot / (n1 * n2)

print("\n--- NORM COMPROVATION ---")
for i, v in enumerate(vectors):
  n = vector_norm(v)
  # gemini-embedding-001 devuelve vectores normalizados por defecto (unit
  # length), lo que simplifica la fórmula del coseno a solo el producto
  # punto (dot product).
  assert math.isclose(n, 1.0, abs_tol=1e-4), f"Vector {i} norma {n:.4f} no es 1.0"
  print(f"Vector {i} norma: {n:.4f}")

print("\n--- MATRIZ DE SIMILITUD DE COSENO (15 pares) ---")
n_sentences = len(sentences)
pairs_results = []

for i in range(n_sentences):
  for j in range(i + 1, n_sentences):
    sim = cosine_similarity(vectors[i], vectors[j])
    pairs_results.append((sim, i, j))

# Ordenar de mayor a menor similitud
pairs_results.sort(key=lambda x: x[0], reverse=True)

for sim, i, j in pairs_results:
  print(f"Coseno({i}, {j}) = {sim:.4f}  |  '{sentences[i][:30]}...' <-> '{sentences[j][:30]}...'")


# Ajusta tus credenciales locales VECTOR_DB_URL
DB_URL = os.getenv("VECTOR_DB_URL")

# Detectamos automáticamente la dimensión de los vectores generados (ej. 3072 o 1536)
dim = len(vectors[0])

with psycopg.connect(DB_URL) as conn:
  # 1. Habilitar extensión y registrar el tipo vector en psycopg
  conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
  register_vector(conn)

  with conn.cursor() as cur:
    # 2. Crear tabla temporal dentro de esta misma sesión
    cur.execute(f"""
            CREATE TEMP TABLE temp_embeddings (
                id INT PRIMARY KEY,
                content TEXT,
                embedding vector({dim})
            );
        """)

    # 3. Inserción eficiente en lote (executemany)
    rows = [(i, sentences[i], vectors[i]) for i in range(len(sentences))]
    cur.executemany(
        "INSERT INTO temp_embeddings (id, content, embedding) VALUES (%s, %s,"
        " %s);",
        rows,
    )

    # 4. Verificar similitud de coseno en Postgres vs Python puro
    # <=> calcula distancia de coseno, así que (1 - distancia) = similitud de coseno
    cur.execute("""
            SELECT
                a.id AS id_a,
                b.id AS id_b,
                1 - (a.embedding <=> b.embedding) AS pg_cosine
            FROM temp_embeddings a
            CROSS JOIN temp_embeddings b
            WHERE a.id < b.id
            ORDER BY pg_cosine DESC;
        """)

    print("\n--- SIMILITUDES EN PGVECTOR VS PYTHON (15 pares) ---")
    max_diff = 0.0
    for id_a, id_b, pg_cosine in cur.fetchall():
      py_cosine = cosine_similarity(vectors[id_a], vectors[id_b])
      diff = abs(pg_cosine - py_cosine)
      max_diff = max(max_diff, diff)
      print(
          f"Par ({id_a}, {id_b}) -> Postgres: {pg_cosine:.6f} | Python:"
          f" {py_cosine:.6f} | diff: {diff:.2e}"
      )

    # pgvector guarda los embeddings en float32 y Python los calcula en
    # float64, así que se espera una diferencia máxima del orden de 1e-7
    # entre ambos cálculos de coseno (sin medir todavía).
    print(f"\nDiferencia máxima Postgres vs Python: {max_diff:.2e}")