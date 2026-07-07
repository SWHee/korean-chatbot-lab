"""Ollama HTTP API 기반 로컬 생성기"""

import json
from collections.abc import Iterator

import httpx


MODEL_ID = "qwen3:4b-instruct-2507-q4_K_M"
BASE_URL = "http://localhost:11434"
MAX_NEW_TOKENS = 1024
TIMEOUT_SECONDS = 60.0


class OllamaGenerator:
    """Ollama 서버의 양자화 Qwen3 모델로 답변 생성"""

    def _chat_payload(self, prompt: str, stream: bool) -> dict:
        """Ollama chat API 요청 본문 구성"""
        return {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            # Ollama backend의 생성 길이 상한
            "options": {"num_predict": MAX_NEW_TOKENS},
        }

    def generate(self, prompt: str) -> str:
        """사용자 문장을 Ollama chat API에 전달해 답변 문자열 반환"""
        response = httpx.post(
            f"{BASE_URL}/api/chat",
            json=self._chat_payload(prompt, stream=False),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def stream(self, prompt: str) -> Iterator[str]:
        """모델이 생성하는 답변 조각을 순차 반환"""
        with httpx.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json=self._chat_payload(prompt, stream=True),
            timeout=TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()

            # Ollama는 조각마다 JSON 한 줄을 전송
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get("done"):
                    break
                yield chunk["message"]["content"]
