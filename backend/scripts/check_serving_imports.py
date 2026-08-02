"""
서빙 경로 의존성 검사

app.main 에서 최상위(top-level) import만 따라가며 실제로 로드되는 모듈을 모으고,
그 안에 배치 전용 패키지(torch, transformers 등)가 섞여 있는지 확인
"""

import ast
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR / "app"

# 서빙 이미지에 설치되지 않는 패키지들 (requirements-batch.txt 전용)
FORBIDDEN = {"torch", "transformers", "accelerate", "apscheduler", "sklearn", "datasets"}

ENTRY = "app.main"


def _module_to_path(module: str) -> Path | None:
    """'app.rag.search' → 실제 .py 경로 (패키지면 __init__.py)."""
    rel = module.replace(".", "/")
    for candidate in (BACKEND_DIR / f"{rel}.py", BACKEND_DIR / rel / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _top_level_imports(path: Path) -> list[tuple[str, int]]:
    """
    파일의 최상위 import만 수집. 함수/메서드 안의 지연 임포트는 제외한다.
    반환: [(모듈명, 줄번호), ...]
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []

    for node in tree.body:  # tree.body만 보면 최상위만 본다
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.append((node.module, node.lineno))
            elif node.level > 0:
                # 상대 임포트 → 절대 경로로 환산
                pkg = path.parent.relative_to(BACKEND_DIR).as_posix().replace("/", ".")
                found.append((f"{pkg}.{node.module}" if node.module else pkg, node.lineno))
        elif isinstance(node, ast.If):
            # `if TYPE_CHECKING:` 같은 블록도 최상위로 간주해 훑는다
            for sub in ast.walk(node):
                if isinstance(sub, ast.Import):
                    for alias in sub.names:
                        found.append((alias.name, sub.lineno))
                elif isinstance(sub, ast.ImportFrom) and sub.module:
                    found.append((sub.module, sub.lineno))

    return found


def main() -> int:
    visited: set[str] = set()
    violations: list[str] = []
    queue = [ENTRY]

    while queue:
        module = queue.pop()
        if module in visited:
            continue
        visited.add(module)

        path = _module_to_path(module)
        if path is None:
            continue  # 프로젝트 외부(서드파티) 모듈은 여기서 멈춘다

        for imported, lineno in _top_level_imports(path):
            root = imported.split(".")[0].lower()
            if root in FORBIDDEN:
                rel = path.relative_to(BACKEND_DIR)
                violations.append(f"  {rel}:{lineno} — {imported}")
            if imported.startswith("app"):
                queue.append(imported)

    print(f"[검사] {ENTRY} 기준 프로젝트 모듈 {len(visited)}개 탐색")

    if violations:
        print("\n❌ 서빙 경로에 배치 전용 패키지가 최상위로 import되어 있습니다:")
        print("\n".join(violations))
        print("\n→ 해당 import를 함수 안으로 옮기세요 (지연 임포트).")
        return 1

    print("✅ 서빙 경로에 torch/transformers 등 배치 전용 패키지 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
