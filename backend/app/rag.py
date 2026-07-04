from sqlalchemy import text
from openai import OpenAI
from app.database import SessionLocal
from app.embedder import get_embedding
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def search_similar_posts(query: str, stock_code: str = None, top_k: int = 5) -> list[dict]:
    """질문과 의미적으로 유사한 게시글 TOP K 검색. stock_code 지정 시 해당 종목만 검색"""
    query_vector = get_embedding(query)

    db = SessionLocal()
    try:
        if stock_code:
            result = db.execute(text("""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                WHERE p.stock_code = :stock_code
                ORDER BY distance ASC
                LIMIT :top_k
            """), {
                "query_vector": str(query_vector),
                "stock_code": stock_code,
                "top_k": top_k,
            })
        else:
            result = db.execute(text("""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                ORDER BY distance ASC
                LIMIT :top_k
            """), {
                "query_vector": str(query_vector),
                "top_k": top_k,
            })

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "stock_name": row.stock_name,
                "stock_code": row.stock_code,
                "title": row.title,
                "posted_at": str(row.posted_at),
                "distance": row.distance,
            }
            for row in rows
        ]
    finally:
        db.close()


def ask(query: str, stock_code: str = None) -> dict:
    """RAG 기반 질의응답"""

    # 1. 유사 게시글 검색
    similar_posts = search_similar_posts(query, stock_code=stock_code, top_k=5)

    if not similar_posts:
        return {
            "answer": "관련 게시글을 찾을 수 없습니다.",
            "sources": [],
        }

    # 2. 게시글 목록을 컨텍스트로 정리
    context = "\n".join([
        f"- [{post['stock_name']}] {post['title']} ({post['posted_at'][:10]})"
        for post in similar_posts
    ])

    # 3. Claude에게 여론 요약 요청
    prompt = f"""당신은 주식 커뮤니티 여론을 요약해주는 분석가입니다.
아래는 사용자 질문과 관련된 주식 커뮤니티 게시글 제목들입니다.

[질문]
{query}

[관련 게시글]
{context}

위 게시글들을 바탕으로 커뮤니티의 전반적인 여론과 분위기를 2~3문장으로 요약해주세요.
중요: 이것은 사실 분석이 아니라 커뮤니티 여론 요약입니다. 팩트체크가 아닌 분위기를 전달해주세요."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": similar_posts,
    }


if __name__ == "__main__":
    result = ask("요즘 분위기 어때?", stock_code="005930")  # 삼성전자
    print("=== 답변 ===")
    print(result["answer"])
    print("\n=== 참고 게시글 ===")
    for post in result["sources"]:
        print(f"  [{post['stock_name']}] {post['title']}")
