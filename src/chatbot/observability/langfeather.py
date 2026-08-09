"""LangFeather 선택적 연결 경계"""

import os


def load_langfeather():
    """선택적 로컬 추적 SDK 로드"""
    try:
        import langfeather
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "LangFeather 추적에는 'uv sync --group tracing'이 필요합니다."
        ) from error
    return langfeather


def configure_langfeather():
    """환경 변수에 따른 LangFeather SDK 준비"""
    enabled = os.getenv("LANGFEATHER_ENABLED", "false").strip().lower() == "true"
    if not enabled:
        return None

    sdk = load_langfeather()
    sdk.configure(endpoint=os.getenv("LANGFEATHER_ENDPOINT") or None)
    return sdk


def wrap_runnable(runnable, *, sdk, name: str):
    """활성 SDK가 있는 경우 Runnable 추적 래핑"""
    if sdk is None:
        return runnable
    return sdk.wrap_runnable(runnable, name=name)


def shutdown_langfeather(sdk, *, timeout_seconds: float) -> None:
    """활성 SDK의 대기 중 trace 전송 종료"""
    if sdk is not None:
        sdk.shutdown(timeout=timeout_seconds)
