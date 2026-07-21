# Chroma 인덱스 확인 가이드

- 작성일: 2026-07-06

현재 프로젝트의 공개 경계인 `build_index.py`, `open_collection()`, `search()`를
사용해 저장 결과와 검색을 확인하는 방법이다. 모든 명령은 프로젝트 루트에서
실행한다.

## 1. 인덱스 생성

```bash
uv run python scripts/build_index.py
```

법령 XML 4건을 파싱·청킹하고 KURE-v1으로 임베딩해
`data/index/chroma/`에 `statutes` 컬렉션을 만든다. 정상 실행 결과는 조문
260개, 청크 322개다.

## 2. 저장 개수와 레코드 확인

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
collection = open_collection()
print('청크 수:', collection.count())
record = collection.peek(1)
print('ID:', record['ids'][0])
print('metadata:', record['metadatas'][0])
print('본문:', record['documents'][0][:100])
print('벡터 차원:', len(record['embeddings'][0]))"
```

한 레코드에서 청크 ID, 본문, 출처 metadata, 1024차원 벡터가 함께 저장된 것을
확인할 수 있다.

## 3. metadata로 조문 확인

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
result = open_collection().get(where={'article_no': '제18조'})
for item_id in result['ids']:
    print(item_id)"
```

이 명령은 의미 검색이 아니라 조문번호가 같은 저장 레코드를 직접 조회한다.
긴 조문은 `|0`, `|1`처럼 여러 자식 청크가 있을 수 있다.

## 4. 질문으로 의미 검색

```bash
uv run python -c "
from chatbot.embedding import load_encoder, embed_texts
from chatbot.vectorstore import open_collection, search

question = '예금자보호 한도가 얼마예요?'
encoder = load_encoder()
query_vector = embed_texts(encoder, [question])[0]

for result in search(open_collection(), query_vector, top_k=3):
    print(
        f\"{result['similarity']:.3f}  \"
        f\"{result['law_name']} {result['article_no']}({result['title']})\"
    )"
```

질문을 KURE-v1 벡터로 바꾼 뒤 코사인 유사도가 높은 청크 세 개를 본문과 출처
metadata와 함께 받는다.

## 5. 평가 질문으로 검색 검증

```bash
uv run python scripts/verify_index.py
```

15개 질문에서 Chroma와 전체 벡터 직접 비교의 top-5 조문이 같은지, 정답 조문이
top-5에 있는지 확인한다. 현재 기록된 기준선은 15/15 일치, Hit@5 12/15다.

## 선택적 실험

Chroma collection 자체는 metadata filter와 문자열 포함 조건도 제공한다.

```python
collection.query(
    query_embeddings=[query_vector],
    n_results=3,
    where={"law_name": "예금자보호법 시행령"},
)

collection.get(where_document={"$contains": "1억원"})
```

두 기능은 현재 애플리케이션의 기본 `search()`에는 포함하지 않았다. 검색 개선
후보일 뿐이며, 적용하려면 같은 평가 질문으로 기본 검색보다 나아지는지 먼저
측정해야 한다.
