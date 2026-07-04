# Git 커밋

변경사항을 분석해서 논리적으로 그룹핑하고 커밋 메시지를 제안한 뒤 승인받아 커밋한다.
**push는 절대 하지 않는다.**

## 순서

### 1. 변경사항 파악
```bash
git status --short
git diff --stat
```

### 2. 변경 파일을 논리적으로 그룹핑
관련된 변경끼리 묶는다.
- `app/models.py`, `app/database.py` → DB 관련 → 커밋 1개
- `requirements.txt` → 환경 설정 → 커밋 1개
- `.env`는 커밋하지 않는다 (경고 표시)

### 3. 커밋 메시지 제안 및 승인 요청

컨벤션:
- `feat:` 새 기능
- `fix:` 버그 수정
- `chore:` 설정, 환경
- `refactor:` 코드 정리
- `docs:` 문서
- `style:` 포맷팅

메시지는 한국어로 작성한다.

사용자에게 이렇게 보여준다:
```
📦 커밋 계획

[커밋 1] feat: DB 모델 및 초기 테이블 스키마 설계
  → app/models.py, app/database.py

이대로 진행할까요?
```

### 4. 승인 후 실행
```bash
git add <파일들>
git commit -m "<메시지>"
```

### 5. 완료 보고
```
✅ 커밋 N개 완료!
```
