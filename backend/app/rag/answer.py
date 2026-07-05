from openai import OpenAI
from dotenv import load_dotenv
import os

from .search import search_similar_posts

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask(query: str, stock_code: str = None) -> dict:
    """RAG 기반 질의응답"""

    # 1. 유사 게시글 검색
    similar_posts = search_similar_posts(query, stock_code=stock_code, top_k=5)

    if not similar_posts:
        return {
            "answer": "관련 게시글을 찾을 수 없습니다.",
            "sources": [],
        }

    # 2. source_type별로 컨텍스트 분리
    news_posts = [p for p in similar_posts if p.get("source_type") == "news"]
    community_posts = [p for p in similar_posts if p.get("source_type") != "news"]

    news_context = "\n".join([
        f"- {post['title']} ({post['posted_at'][:10]})"
        for post in news_posts
    ]) or "없음"

    community_context = "\n".join([
        f"- {post['title']} ({post['posted_at'][:10]})"
        for post in community_posts
    ]) or "없음"

    # 3. GPT에게 뉴스/커뮤니티 구분해서 질문에 직접 답하도록 요청
    prompt = f"""당신은 주식 뉴스와 커뮤니티 여론을 종합해서 사용자 질문에 답해주는 분석가입니다.

[사용자 질문]
{query}

[관련 뉴스 기사]
{news_context}

[관련 커뮤니티 게시글]
{community_context}

위 내용을 바탕으로 사용자 질문에 직접 답해주세요.
- 뉴스 기사가 있다면 팩트 기반 이유를 먼저 언급하세요.
- 커뮤니티 반응/여론을 추가로 설명하세요.
- 2~3문장으로 간결하게 답해주세요."""

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
