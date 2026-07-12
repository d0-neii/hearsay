from openai import OpenAI
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models import Post, PostEmbedding
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# OpenAI Embeddings API 배치 최대 크기
_EMBED_BATCH_SIZE = 100


def get_embedding(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환 (단일 호출용 — HyDE 등에서 사용)"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    여러 텍스트를 한 번의 API 호출로 임베딩.
    OpenAI는 input에 리스트를 받아 순서 보장된 벡터 배열을 반환.
    _EMBED_BATCH_SIZE 단위로 나눠서 호출 (API 제한 대비).
    """
    results: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        chunk = texts[i : i + _EMBED_BATCH_SIZE]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk,
        )
        # response.data는 index 순서가 보장됨
        chunk_vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        results.extend(chunk_vectors)
    return results


def embed_unprocessed_posts():
    """아직 임베딩 안 된 게시글을 찾아서 배치 임베딩 후 저장"""
    db = SessionLocal()

    try:
        # 임베딩 안 된 게시글 조회 (post_embeddings에 없는 것들)
        result = db.execute(text("""
            SELECT p.id, p.title, p.content
            FROM posts p
            LEFT JOIN post_embeddings pe ON p.id = pe.post_id
            WHERE pe.id IS NULL
            LIMIT 500
        """))
        posts = result.fetchall()

        if not posts:
            print("새로 임베딩할 게시글 없음")
            return

        print(f"{len(posts)}개 게시글 배치 임베딩 시작...")

        # 텍스트 준비 (제목 + 본문)
        texts_to_embed = [
            f"{title} {content or ''}".strip()
            for _, title, content in posts
        ]

        try:
            vectors = get_embeddings_batch(texts_to_embed)
        except Exception as e:
            print(f"  ❌ 배치 임베딩 API 호출 실패: {e}")
            return

        # DB 저장
        saved = 0
        for (post_id, _, _), vector in zip(posts, vectors):
            try:
                db.add(PostEmbedding(post_id=post_id, embedding=vector))
                db.commit()
                saved += 1
            except Exception as e:
                db.rollback()
                print(f"  ❌ post_id={post_id} 저장 실패: {e}")

        print(f"임베딩 완료! ({saved}/{len(posts)}개 저장)")

    finally:
        db.close()


if __name__ == "__main__":
    embed_unprocessed_posts()
