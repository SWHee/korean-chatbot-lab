from collections.abc import Iterator

import httpx


MODEL_ID = "qwen3:4b-instruct-2507-q4_K_M"
BASE_URL = "http://localhost:11434"
MAX_NEW_TOKENS = 128
TIMEOUT_SECONDS = 60.0


class OllamaGenerator:
    """Ollama 서버의 양자화 Qwen3 모델로 답변 생성"""

    def generate(self, prompt: str) -> str:
        """사용자 문장을 Ollama chat API에 전달해 답변 문자열 반환"""
        response = httpx.post(
            f"{BASE_URL}/api/chat",
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                # HF Generator와 같은 생성 길이 상한
                "options": {"num_predict": MAX_NEW_TOKENS},
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def stream(self, prompt: str) -> Iterator[str]:
        """조각 응답은 후속 작업에서 구현"""
        raise NotImplementedError("OllamaGenerator.stream")
