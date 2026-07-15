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

    def _format_post(post: dict) -> str:
        """제목 + 본문 요약 + 감성 점수를 한 블록으로 포맷"""
        score = post.get("sentiment_score")
        score_str = f"{score:+.2f}" if score is not None else "N/A"
        content = post.get("content") or ""
        content_preview = content[:200].replace("\n", " ") if content else ""
        lines = [f"- [{score_str}] {post['title']} ({post['posted_at'][:10]})"]
        if content_preview:
            lines.append(f"  └ {content_preview}")
        return "\n".join(lines)

    news_context = "\n".join([_format_post(p) for p in news_posts]) or "없음"
    community_context = "\n".join([_format_post(p) for p in community_posts]) or "없음"

    # 3. 감성 점수 분포 요약
    scores = [p["sentiment_score"] for p in similar_posts if p.get("sentiment_score") is not None]
    if scores:
        avg_score = sum(scores) / len(scores)
        pos_count = sum(1 for s in scores if s > 0.1)
        neg_count = sum(1 for s in scores if s < -0.1)
        neu_count = len(scores) - pos_count - neg_count
        sentiment_summary = (
            f"평균 감성 점수: {avg_score:+.2f} "
            f"(긍정 {pos_count}건 / 중립 {neu_count}건 / 부정 {neg_count}건)"
        )
    else:
        sentiment_summary = "감성 점수 데이터 없음"

    # 4. GPT에게 뉴스/커뮤니티 구분 + 감성 수치 포함해서 답하도록 요청
    prompt = f"""당신은 주식 뉴스와 커뮤니티 여론을 종합해서 사용자 질문에 답해주는 분석가입니다.
주식, 투자, 기업, 경제와 관련 없는 질문에는 "주식 관련 질문만 답변할 수 있어요."라고만 답하세요.

[사용자 질문]
{query}

[감성 분석 요약]
{sentiment_summary}

[관련 뉴스 기사] (감성점수: -1.0 부정 ~ +1.0 긍정)
{news_context}

[관련 커뮤니티 게시글] (감성점수: -1.0 부정 ~ +1.0 긍정)
{community_context}

위 내용을 바탕으로 사용자 질문에 직접 답해주세요.
- 뉴스 기사가 있다면 팩트 기반 이유를 먼저 언급하세요.
- 커뮤니티 반응/여론과 감성 점수를 근거로 여론 분위기를 설명하세요.
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
