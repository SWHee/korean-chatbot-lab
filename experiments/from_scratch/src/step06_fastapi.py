"""Step 06. FastAPI.

역할:
    학습한 생성 함수를 최소한의 웹 API로 감싼다.

학습 포인트:
    - 요청/응답 schema,
    - async FastAPI endpoint,
    - 서버 시작 시 모델 로딩,
    - 아직 학습된 모델이 없을 때 명확한 에러를 반환하는 방법.

나중의 프로젝트 구조:
    모델 파이프라인이 충분히 이해되면 이 파일은 `main.py`, `api.py` 또는
    작은 FastAPI 앱 패키지로 바뀔 수 있다.
"""
