"""등록된 24문항으로 법령 RAG 평가를 실행하는 실행 파일"""

from chatbot.evaluation.runner import main

# 현재 RAG Graph를 Dataset 전체에 실행하는 명령
# 검색·충실도 지표와 LangSmith Experiment 기록은 evaluation/runner.py 담당

if __name__ == "__main__":
    main()
