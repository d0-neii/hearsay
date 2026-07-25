<div align="center">

<img alt="logo" src="https://github.com/user-attachments/assets/6d745faa-dd14-47c2-a999-d8f129efeb42" style="width:360px; height:auto;"/>

**주식 커뮤니티의 목소리를 감성으로 읽다**

Hearsay는 네이버 종토방과 뉴스의 게시글을 실시간으로 수집하고,
한국어 금융 특화 AI 모델로 감성을 분석해 투자 심리를 한눈에 파악할 수 있는 대시보드입니다.
숫자 너머의 시장 분위기를 텍스트에서 읽어내고,
궁금한 점은 AI에게 바로 질문할 수 있습니다.

**커뮤니티의 소문(hearsay)이 인사이트가 됩니다.**


</div>
<br>

# 목차

- 🌱 기획 배경
- ⛓ 주요 기능 흐름
  - 데이터 파이프라인
  - 기능 소개
    - 종목 대시보드
    - 오늘의 요약
    - 시간대별 여론 추이
    - 커뮤니티 Q&A
    - 게시글 피드
- ⚙️ 기술 스택 및 도입 이유
- 🧩 개발 과정
  - 왜 범용 모델이 아니라 파인튜닝했나?
    - 도메인 특화 데이터는 어떻게 만들었나?
    - 학습 데이터 불균형은 어떻게 다뤘나?
    - 파인튜닝 전후 성능은 얼마나 달라졌나?
  - RAG를 어떻게 설계했나?
    - 쿼리와 문서 사이의 분포 차이 문제
    - 키워드 검색과 벡터 검색, 무엇을 믿어야 할까?
- 💭 개인 회고

<br>

# 🌱 기획 배경

출퇴근하기 바쁜 와중에도 오늘 왜 올랐는지, 왜 떨어졌는지는 항상 궁금했습니다. <br/>
그런데 막상 찾아보려면 뉴스, 커뮤니티, SNS를 따로따로 돌아다녀야 했고 <br/>
그렇게 모은 정보도 긍정 및 부정 의견이 뒤섞여 있어 결국 흐름을 파악하지 못한 채 포기하는 날이 더 많았습니다.

정보가 없는 게 아니라, 찾는 데 드는 시간과 수고가 너무 컸던 것입니다.

Hearsay는 그 불편함에서 시작됐습니다.

- 뉴스와 커뮤니티 게시글을 자동으로 수집하고
- 한국어 금융 특화 감성 분석 모델로 여론의 온도를 수치화하고
- "요즘 삼성전자 분위기 어때?" 같은 자연어 질문 하나로 바로 답을 얻을 수 있도록

정보를 모으는 시간을 줄이고, 판단에 더 집중할 수 있는 환경을 만드는 것이 목표입니다.

<br>

# ⛓ 주요 기능 흐름

## 데이터 파이프라인

```mermaid
flowchart TD
    subgraph Crawler["🕷 크롤러 (10분마다)"]
        C1[커뮤니티\n종목토론방]
        C2[뉴스]
        C3[KRX 거래 데이터]
    end

    subgraph DB["🗄 PostgreSQL + pgvector"]
        D1[posts]
        D2[post_embeddings]
        D3[BM25 인덱스]
    end

    subgraph AI["🤖 AI"]
        A1[KR-FinBERT\n감성 분석]
        A2[OpenAI Embeddings\n+ HyDE]
        A3[GPT-4o-mini\n요약 / 답변]
    end

    C1 & C2 --> D1
    C3 --> |매수·매도 비율| FE
    D1 --> A1 --> D1
    D1 --> A2 --> D2
    D1 --> D3

    subgraph Search["🔍 Hybrid Search"]
        S1[벡터 검색]
        S2[BM25 검색]
        S3[RRF 랭킹]
    end

    D2 --> S1 --> S3
    D3 --> S2 --> S3
    S3 --> A3

    D1 --> A3
    A3 --> FE[React 대시보드]
```

## 기능 소개

Hearsay는 아래와 같이 하나의 대시보드에서 종목별 수급, 여론, 커뮤니티 반응을 확인할 수 있습니다. 화면의 각 번호는 아래 기능 설명과 대응됩니다.

### 📷 전체 화면
<img width="2940" height="1595" alt="image 1" src="https://github.com/user-attachments/assets/2809535d-6670-4d17-bbfa-0c5d1ca791d4" />

### ① 종목 대시보드

- KRX 투자자별 실거래 금액 기준으로 매수와 매도 비율을 산출합니다. 개인, 기관, 외국인 세 그룹 중 순매수 우세 그룹의 비율을 표시하며, 장 마감 후 데이터가 없을 경우 커뮤니티 감성 분석 결과로 자동 대체됩니다.
- 수급 / 여론 / 오늘 언급량 / 핫 키워드 4종 통계 카드로 종목 현황을 한눈에 파악할 수 있습니다.

### ② 오늘의 요약

- 당일 게시글 제목 최대 40개를 GPT-4o-mini에 전달해 **호재 / 악재 / 이슈** 3가지 태그로 자동 분류 및 요약합니다.
- 10분 크롤링 주기마다 자동 갱신되며, 당일 게시글이 없는 경우 섹션 자체가 노출되지 않습니다.

### ③ 시간대별 여론 추이

- KR-FinBERT가 분석한 게시글별 감성 점수를 시간대 단위로 집계합니다. 조회수가 높은 게시글에 가중치를 부여해 단순 평균보다 실제 여론에 가까운 수치를 반영합니다.
- 0 기준선 위는 긍정, 아래는 부정 여론이며 특정 시간대에 마우스를 올리면 점수를 확인할 수 있습니다.

### ④ 커뮤니티 Q&A

- "오늘 왜 올랐어?", "지금 분위기 어때?" 같은 자연어 질문에 커뮤니티, 뉴스 기반 답변을 반환합니다.
- 쿼리를 HyDE로 가상 문서화한 뒤 BM25 + 벡터 검색 결과를 RRF로 통합해 검색 품질을 높입니다. 뉴스 기반 팩트와 커뮤니티 여론을 구분해 답변합니다.
- 종목을 전환하면 이전 대화가 초기화되어 항상 선택된 종목 기준의 맥락으로 질문할 수 있습니다.

### ⑤ 게시글 피드

- 선택한 종목의 최신 커뮤니티, 뉴스 게시글을 우측 피드에서 확인할 수 있습니다.
- 각 게시글에는 KR-FinBERT가 분석한 감성 점수가 함께 표시됩니다.

<br>

# ⚙️ 기술 스택 및 도입 이유

### AI

| 기술                                                                                                                                                                                                                                    | 도입 이유                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| ![PyTorch](https://img.shields.io/badge/PyTorch-3A3A3A?style=for-the-badge\&logo=pytorch\&logoColor=EE4C2C) ![Transformers](https://img.shields.io/badge/Transformers-4A4A4A?style=for-the-badge\&logo=huggingface\&logoColor=FFD21E) | 대상 텍스트가 한국어, 금융 도메인, 커뮤니티 은어 중심이라 범용 감성 모델의 정확도가 낮았습니다. 금융 텍스트로 사전학습된 모델을 직접 라벨링한 데이터로 파인튜닝해 도메인에 맞는 감성 분석 성능을 확보합니다.                           |
| ![pgvector](https://img.shields.io/badge/pgvector-5A5A5A?style=for-the-badge) ![BM25](https://img.shields.io/badge/BM25-3A3A3A?style=for-the-badge) ![RRF](https://img.shields.io/badge/RRF-4A4A4A?style=for-the-badge)               | 벡터 검색만으로는 종목명, 티커, 수치처럼 정확히 일치해야 하는 키워드를 놓칠 수 있습니다. BM25와 함께 검색한 뒤 Reciprocal Rank Fusion(RRF)으로 결합해, 점수 정규화 없이 순위만으로 두 검색기를 통합하고 검색 안정성을 높입니다. |
| ![HyDE](https://img.shields.io/badge/HyDE-5A5A5A?style=for-the-badge)                                                                                                                                                                 | "요즘 분위기 어때?"처럼 추상적인 질문은 게시글과 임베딩 분포가 달라 검색 성능이 떨어질 수 있습니다. 질문 대신 LLM이 생성한 가상의 관련 문서를 임베딩해 검색 정확도를 높입니다.                                         |
| ![OpenAI](https://img.shields.io/badge/OpenAI-3A3A3A?style=for-the-badge\&logo=openai\&logoColor=412991)                                                                                                                              | 임베딩과 답변 생성 모델을 목적에 맞게 분리해 사용합니다. 임베딩은 한국어 성능 대비 비용 효율이 높은 소형 모델을, 답변 생성은 품질 대비 비용이 적절한 모델을 선택하며 임베딩은 배치 호출로 API 요청 수를 줄입니다.                    |

### Frontend

| 기술                                                                                                                                                                                                                            | 도입 이유                                                                                                     |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| ![React](https://img.shields.io/badge/React_19-3A3A3A?style=for-the-badge\&logo=react\&logoColor=61DAFB) ![TypeScript](https://img.shields.io/badge/TypeScript-4A4A4A?style=for-the-badge\&logo=typescript\&logoColor=3178C6) | 종목 선택 하나로 피드, 차트, 요약, 질의응답이 함께 갱신되는 화면이라 선언적 UI가 적합합니다. API 응답을 타입으로 관리해 백엔드 스키마 변경을 컴파일 단계에서 확인합니다.      |
| ![TanStack Query](https://img.shields.io/badge/TanStack_Query-5A5A5A?style=for-the-badge\&logo=reactquery\&logoColor=FF4154)                                                                                                  | 대부분의 상태가 서버 데이터이며 10분 주기로 갱신됩니다. 캐싱, 중복 요청 제거, 로딩·에러 처리를 TanStack Query로 관리해 별도의 전역 상태 관리 라이브러리 없이 구현합니다. |
| ![Vite](https://img.shields.io/badge/Vite-4A4A4A?style=for-the-badge\&logo=vite\&logoColor=646CFF)                                                                                                                            | 빠른 HMR로 개발 생산성을 높이고, `server.proxy`를 통해 `/api` 요청을 FastAPI로 전달해 CORS 설정 없이 개발 환경을 구성합니다.                  |
| ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS_v4-5A5A5A?style=for-the-badge\&logo=tailwindcss\&logoColor=06B6D4)                                                                                                  | 대시보드 레이아웃을 컴포넌트 단위에서 빠르게 구성하고 수정하기 위해 사용합니다. 감성 색상은 CSS 변수로 관리해 일관된 디자인을 유지합니다.                           |


### Backend

| 기술                                                                                                                                                                                                 | 도입 이유                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| ![FastAPI](https://img.shields.io/badge/FastAPI-3A3A3A?style=for-the-badge\&logo=fastapi\&logoColor=009688)                                                                                        | 타입 힌트를 기반으로 OpenAPI 문서를 자동 생성해 프론트엔드와 API 계약을 일관되게 유지합니다.                                  |
| ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4A4A4A?style=for-the-badge\&logo=postgresql\&logoColor=4169E1) ![pgvector](https://img.shields.io/badge/pgvector-5A5A5A?style=for-the-badge) | 게시글 메타데이터와 임베딩을 하나의 데이터베이스에서 관리합니다. 별도 벡터 DB 없이 조건 필터링과 벡터 검색을 하나의 쿼리로 처리해 구조를 단순화합니다.     |
| ![APScheduler](https://img.shields.io/badge/APScheduler-3A3A3A?style=for-the-badge)                                                                                                                | 크롤링 작업을 애플리케이션 내부에서 주기적으로 실행합니다. 현재 규모에서는 별도 워커와 메시지 브로커 없이도 단순한 구조로 운영할 수 있습니다.           |
| ![Requests](https://img.shields.io/badge/requests-4A4A4A?style=for-the-badge) ![BeautifulSoup4](https://img.shields.io/badge/BeautifulSoup4-5A5A5A?style=for-the-badge)                            | 대상 사이트가 서버 사이드 렌더링이라 헤드리스 브라우저 없이 수집합니다. 상세 페이지는 스레드 풀로 병렬 요청하고 요청 간 지연을 적용해 서버 부하를 조절합니다. |

