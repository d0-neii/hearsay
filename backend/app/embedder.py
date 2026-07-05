from openai import OpenAI
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models import Post, PostEmbedding
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def embed_unprocessed_posts():
    """아직 임베딩 안 된 게시글을 찾아서 임베딩 후 저장"""
    db = SessionLocal()

    try:
        # 임베딩 안 된 게시글 조회 (post_embeddings에 없는 것들)
        result = db.execute(text("""
            SELECT p.id, p.title, p.content
            FROM posts p
            LEFT JOIN post_embeddings pe ON p.id = pe.post_id
            WHERE pe.id IS NULL
            LIMIT 100
        """))
        posts = result.fetchall()

        if not posts:
            print("새로 임베딩할 게시글 없음")
            return

        print(f"{len(posts)}개 게시글 임베딩 시작...")

        for post_id, title, content in posts:
            # 제목 + 본문을 합쳐서 임베딩 (본문 없으면 제목만)
            text_to_embed = f"{title} {content or ''}".strip()

            try:
                vector = get_embedding(text_to_embed)

                embedding = PostEmbedding(
                    post_id=post_id,
                    embedding=vector,
                )
                db.add(embedding)
                db.commit()
                print(f"  ✅ post_id={post_id} 임베딩 완료")

            except Exception as e:
                db.rollback()
                print(f"  ❌ post_id={post_id} 실패: {e}")

        print("임베딩 완료!")

    finally:
        db.close()


if __name__ == "__main__":
    embed_unprocessed_posts()
