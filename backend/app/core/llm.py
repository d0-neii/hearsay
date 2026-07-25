"""
OpenAI 클라이언트 단일 인스턴스
"""

from openai import OpenAI

from app.core.config import settings

openai_client = OpenAI(api_key=settings.openai_api_key)
