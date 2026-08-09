"""로컬 RAG 평가 JSONL을 LangSmith Dataset으로 등록하는 실행 파일"""

from chatbot.evaluation.registry import main

# 평가 문항 원본은 data/evaluation에 유지
# Dataset 생성·갱신과 메타데이터 변환은 evaluation/registry.py 담당

if __name__ == "__main__":
    main()
