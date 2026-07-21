# LangSmith 화면 연결 문제 해결

- 작성일: 2026-07-20

처음 Dataset을 연결했을 때 직접 주소에서는 열리지만 Application 목록에서는 보이지
않았던 문제를 정리한다. 같은 상황에서 Dataset을 다시 만들기 전에 확인할 내용만
남긴다.

## Application 목록에서 Dataset이 사라짐

### 증상

스크립트가 출력한 직접 주소에서는 Dataset과 Experiment가 열렸지만,
`korean-chatbot-rag-dev` Application의 `Datasets & Experiments` 목록에서는 보이지
않았다. 새로고침하면 다시 빈 화면이 나타났다.

### 원인과 해결

Dataset 생성 실패가 아니라 `Application: korean-chatbot-rag-dev` 리소스 태그가
연결되지 않은 상태였다.

1. `Settings > Resource tags`에서 `Application`을 연다.
2. `korean-chatbot-rag-dev` 값의 편집 버튼을 누른다.
3. `Datasets`에서 `korean-chatbot-rag-v1-dev`를 선택한다.
4. Application의 `Datasets & Experiments`에서 새로고침 후에도 보이는지 확인한다.

SDK 생성 성공과 Application 화면 노출은 별도 확인 항목이다. 목록에서 보이지 않을
때는 Dataset을 중복 생성하기 전에 리소스 태그부터 확인한다.

참고:

- [LangSmith resource tags](https://docs.langchain.com/langsmith/set-up-resource-tags)
