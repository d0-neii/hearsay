import re
from collections import Counter

# 키워드 추출용 불용어
STOP_WORDS = {
    '있는', '없는', '이건', '그냥', '진짜', '완전', '너무', '정말', '이제', '근데',
    '그래', '다시', '지금', '오늘', '어제', '이거', '그거', '이게', '그게', '뭔가',
    '이렇게', '저렇게', '어떻게', '왜냐면', '그래서', '하지만', '그런데', '그리고',
    '합니다', '입니다', '있습니다', '없습니다', '했습니다', '됩니다', '같습니다',
}


def extract_hot_keyword(titles: list[str], exclude: set[str] = frozenset()) -> str | None:
    if not titles:
        return None

    base_exclude = STOP_WORDS | exclude | {w for name in exclude for w in name.split()}

    # 문서 빈도(DF) 계산: 전체 제목의 50% 이상에 등장하면 종목명 변형으로 간주하고 자동 제외
    # → "NAVER" stock에서 "네이버"처럼 stock_name과 표기가 다른 경우도 처리
    doc_freq: Counter = Counter()
    token_list: list[str] = []
    for title in titles:
        tokens = re.findall(r'[가-힣]{2,}|[A-Za-z]{2,}', title)
        doc_freq.update(set(tokens))   # 문서당 1번만 카운트
        token_list.extend(tokens)

    # DF 1위 단어 = 종목명 표기 변형일 가능성이 가장 높으므로 무조건 제외
    # (예: stock_name이 "NAVER"여도 제목엔 "네이버"로 등장)
    top_by_df = {w for w, _ in doc_freq.most_common(2) if w not in base_exclude}
    exclude_words = base_exclude | top_by_df

    filtered = [w for w in token_list if w not in exclude_words]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]
