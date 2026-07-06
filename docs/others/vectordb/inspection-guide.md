# 벡터스토어 직접 확인·테스트 가이드

Chroma 인덱스(`data/index/chroma/`)를 직접 열어보고 검색을 실험하는 방법
모음. 모든 명령은 프로젝트 루트에서 실행한다.

인덱스가 없다면(clone 직후) 먼저 생성한다.

```bash
uv run python scripts/build_index.py
```

## 0단계. 파일 구조 보기

```bash
find data/index -type f -exec du -h {} \;
```

- `chroma.sqlite3` — 본체. 원문·메타데이터·(현재 규모에선) 벡터까지 저장
- `<UUID>/` 디렉터리 — HNSW 인덱스 바이너리

## 1단계. 개수와 설정 확인

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
col = open_collection()
print('청크 수:', col.count())
print('설정:', col.configuration_json['hnsw'])"
```

- 청크 수 322, `space: cosine` 확인
- 설정 해석 주의: `batch_size`(기본 100)는 brute-force 버퍼가 인메모리
  HNSW로 넘어가는 크기, `sync_threshold`(기본 1000)는 인메모리 HNSW를
  디스크에 저장하는 주기다. 검색은 HNSW와 버퍼의 혼합 경로로 실행된다

## 2단계. 레코드 한 건 통째로 구경 (peek)

한 청크 = "id + 원문 + 메타데이터 + 1024차원 벡터" 묶음임을 확인한다.

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
p = open_collection().peek(1)
print('id:', p['ids'][0])
print('metadata:', p['metadatas'][0])
print('원문 앞부분:', p['documents'][0][:100])
print('벡터 앞 5개:', p['embeddings'][0][:5], '... 총', len(p['embeddings'][0]), '차원')"
```

예시 출력:

```text
id: 예금자보호법 시행령|제1조|0
metadata: {'law_name': '예금자보호법 시행령', 'effective_date': '20250901',
           'chunk_index': 0, 'title': '목적', 'article_no': '제1조'}
원문 앞부분: [예금자보호법 시행령 제1조 | 목적] 제1조(목적) 이 영은 ...
벡터 앞 5개: [-0.0211, 0.0312, -0.0432, ...] ... 총 1024 차원
```

## 3단계. 조문 번호로 바로 꺼내기 (검색 아님)

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
g = open_collection().get(where={'article_no': '제18조'})
for i in g['ids']: print(i)"
```

네 법령의 '제18조'가 모두 나온다. 긴 조문은 `|0`, `|1`처럼 자식 청크
여러 개로 저장된 것을 볼 수 있다. 특정 법령으로 좁히려면:

```python
where={"$and": [{"law_name": "예금자보호법 시행령"}, {"article_no": "제18조"}]}
```

## 4단계. 키워드 포함 검색 (전문검색)

벡터 없이 문자 그대로 포함된 청크를 찾는다. 문서 저장 시 Chroma가
자동으로 만드는 전문검색 인덱스를 쓴다.

```bash
uv run python -c "
from chatbot.vectorstore import open_collection
g = open_collection().get(where_document={'\$contains': '1억원'})
for i in g['ids']: print(i)"
```

## 5단계. 의미 검색 실험 (질문 → top-k)

모델 로드에 수십 초 걸린다. `q`를 바꿔가며 top-3이 어떻게 변하는지 보는
것이 가장 좋은 학습이다.

```bash
uv run python -c "
from chatbot.embedding import load_encoder
from chatbot.vectorstore import open_collection, search
col = open_collection(); enc = load_encoder()
q = '예금자보호 한도가 얼마예요?'   # 여기를 바꿔가며 실험
v = enc.encode([q], normalize_embeddings=True)[0].tolist()
for r in search(col, v, top_k=3):
    print(f\"{r['similarity']:.3f}  {r['law_name']} {r['article_no']}({r['title']})\")"
```

예시 출력:

```text
0.621  예금자보호법 시행령 제18조(보험금의 계산방법의 예외 등)
0.619  예금자보호법 시행령 제18조(보험금의 계산방법의 예외 등)
0.608  예금자보호법 제30조의4(예금보험기금의 적립액 목표규모의 설정 등)
```

메타데이터 필터와 결합하려면:

```python
col.query(query_embeddings=[v], n_results=3,
          where={"law_name": "예금자보호법 시행령"})
```

## 6단계. SQLite 원본 열기 (심화)

표준 sqlite3 CLI로 저장 구조를 직접 본다.

```bash
sqlite3 data/index/chroma/chroma.sqlite3 ".tables"
sqlite3 data/index/chroma/chroma.sqlite3 \
  "SELECT key, substr(string_value,1,60) FROM embedding_metadata WHERE id=1;"
sqlite3 data/index/chroma/chroma.sqlite3 \
  "SELECT count(*) FROM embeddings_queue;"
```

- `embedding_metadata` — 메타데이터 5개 + `chroma:document` 키로 원문 저장
- `embeddings_queue` — 장애 복구용 WAL. 행이 남아 있다고 해서 벡터가
  HNSW에 반영되지 않았다는 뜻은 아니다

## 해석할 때 주의할 점

- **유사도 절대 임계값은 아직 근거가 없다.** A1 문항의 분포가
  0.32~0.63으로 좁았다 — 고정 임계값을 쓰려면 전체 질문 분포 측정이
  먼저다. 현재는 순위(top-k)를 신호로 쓴다.
- **검색 결과 일치 검증 재현**: `uv run python scripts/verify_index.py`
  (브루트포스 대비 top-5 조문 일치 여부, 15문항).
- corpus 밖 질문(예: 중도해지 불이익)도 0.5대 유사도의 조문이 나온다 —
  "뭐라도 반환"이 벡터 검색의 기본 성질이며, 범위 밖 거절은 상위
  레이어(프롬프트)의 몫이다.
- 배경 결정은 ADR 0005(임베딩)·0006(벡터스토어), 탐색 기록은
  `docs/devlog/rag/vector-store-exploration.md` 참고.
