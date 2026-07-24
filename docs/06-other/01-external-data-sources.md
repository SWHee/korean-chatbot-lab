# 외부 데이터와 API

- 작성일: 2026-07-09
- Finlife 계약 확인: 2026-07-24

이 프로젝트는 외부 데이터를 두 가지 성격으로 나누어 사용한다. 법령 데이터는 이미
RAG corpus로 수집했고, 금융상품 한눈에 API는 인증키와 실제 응답 계약까지 확인했다.
Finlife 호출 함수와 LangGraph 연결은 아직 구현하지 않았다.

## 국가법령정보 Open API

현재 사용 중인 데이터 출처다.

- 출처: 국가법령정보 공동활용 Open API
- 공식 사이트: https://open.law.go.kr
- 사용 스크립트: `scripts/collect_laws.py`
- 저장 위치: `data/laws/`
- 현재 corpus:
  - 금융소비자 보호에 관한 법률
  - 금융소비자 보호에 관한 법률 시행령
  - 예금자보호법
  - 예금자보호법 시행령

법령 원문은 RAG가 보호 제도와 소비자 권리의 근거를 설명하는 데 사용한다. 상품
금리나 가입 조건처럼 자주 바뀌는 정보는 법령 RAG가 아니라 별도 상품 API에서
가져와야 한다.

법령 XML snapshot, 출처, 재수집 방법은 `data/laws/README.md`에 따로 정리되어
있다. API 인증 정보와 호출 IP 같은 신청 정보는 저장소에 남기지 않는다.

## 금융상품 한눈에 API

예·적금 상품 후보를 조회할 때 사용할 예정이다.

- 공식 사이트: https://finlife.fss.or.kr
- 신청 형태: 개인
- 사용 용도: WEB
- 사용 URL: `http://127.0.0.1:8000`
- 환경 변수 예시: `FINLIFE_API_KEY=<발급받은 인증키>`
- 첫 확인 endpoint:
  `GET https://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json`

API 호출은 FastAPI backend에서 처리하는 방향이 자연스럽다. 나중에 Streamlit을
붙이더라도 인증키는 화면 코드에 넣지 않고 `.env`나 backend 설정에서만 다룬다.

이 API로는 예·적금, 대출, 연금저축 같은 공시 상품 정보를 조회할 수 있다. 처음
연결할 때는 범위를 넓히지 않고 예금·적금 상품 후보 조회부터 시작한다.

### 실제 응답에서 확인한 계약

2026-07-24에 은행 권역(`topFinGrpNo=020000`), 정기예금, 1페이지를 인증키로 직접
호출했다. HTTP 200과 Finlife 본문 코드 `err_cd=000`을 받았고, 기본 상품 38건과
금리 옵션 152건이 반환됐다. 이 건수와 금리는 공시가 바뀌면 달라질 수 있으므로
고정된 제품 요구사항으로 사용하지 않는다.

응답의 `result`는 다음 구조였다.

| 구분 | 확인한 필드 |
| --- | --- |
| 호출 결과 | `err_cd`, `err_msg`, `total_count`, `max_page_no`, `now_page_no` |
| 상품 기본정보 | `baseList` |
| 기간·금리 옵션 | `optionList` |
| 상품 연결 키 | `dcls_month`, `fin_co_no`, `fin_prdt_cd` |

`baseList`에는 금융회사·상품명·가입 방법·우대조건·최고한도·공시일이 있고,
`optionList`에는 저축 기간과 기본금리 `intr_rate`, 최고 우대금리 `intr_rate2`가
있었다. 기본정보의 `max_limit`와 `dcls_end_day`는 일부 상품에서 `null`이었으므로
항상 값이 있다고 가정하면 안 된다.

이 필드명은 Finlife가 정한 원본 응답 계약이므로 외부 요청과 응답을 읽는
경계에서만 사용한다. 상품 정규화 단계부터는 프로젝트에서 뜻을 바로 알 수 있는
이름과 타입으로 바꾼다.

| Finlife 원본 | 프로젝트 내부 이름 | 의미 |
| --- | --- | --- |
| `fin_co_no` | `company_code` | 금융회사 코드 |
| `fin_prdt_cd` | `product_code` | 금융상품 코드 |
| `kor_co_nm` | `company_name` | 금융회사 이름 |
| `fin_prdt_nm` | `product_name` | 상품 이름 |
| `save_trm` | `term_months` | 가입 기간(개월) |
| `intr_rate` | `base_interest_rate` | 기본금리 |
| `intr_rate2` | `max_interest_rate` | 최고 우대금리 |

첫 API 호출 함수는 실제 응답 계약을 확인하기 위해 원본 `result`를 반환한다. 다음
정규화 함수가 이 값을 내부 이름으로 한 번 변환한 뒤에는 Graph 상태, Tool 결과와
API 응답에서 Finlife 약어를 직접 사용하지 않는다.

잘못된 권역코드로 호출했을 때도 HTTP 상태는 200이었지만 본문은
`err_cd=101`, `topFinGrpNo의 부적절한 값`을 반환했다. 따라서 구현은 HTTP 성공만
확인하지 않고 `result.err_cd == "000"`도 검사해야 한다.

첫 구현은 이 정상 경로와 본문 오류 한 건만 다룬다. 전체 페이지 순회, 적금 endpoint,
금리 정렬, 상품 추천, Graph 연결은 같은 작업에 넣지 않는다. 이후 순서는
[Finlife에서 LangGraph Agent까지 확장 명세](../07-langgraph-agent/01-finlife-agent-expansion-spec.md)를
기준으로 한다.

## 역할 구분

| 구분 | 역할 |
| --- | --- |
| 법령 RAG | 예금자보호 한도, 설명의무, 소비자 권리 같은 제도 설명 |
| 금융상품 한눈에 API | 현재 공시된 예금·적금 비교 후보 조회 |
| 상품 공시·설명서 | 개별 상품의 보호 여부와 세부 조건 최종 확인 |

예를 들어 "금리 높은 적금 알려줘"라는 질문은 법령 RAG만으로 답하기 어렵다. 이때는
금융상품 API로 비교 후보를 가져오고, 필요한 경우 RAG가 예금자보호나 소비자 유의
사항을 설명하는 식으로 역할을 나눈다. `intr_rate2`는 우대조건 충족 시 금리이므로
단순히 가장 큰 값을 개인에게 가장 유리한 상품으로 단정하지 않는다.

## 저장소에 남기는 기준

- API 키, 개인 신청 정보, 호출 IP는 커밋하지 않는다.
- 법령 XML처럼 출처와 snapshot을 밝힐 수 있는 원문은 저장소에 남길 수 있다.
- Chroma 인덱스, 모델 cache처럼 코드로 재생성 가능한 파생물은 커밋하지 않는다.
- 외부 API 응답을 새 데이터셋처럼 저장할 때는 출처, 수집일, 재배포 가능 여부를
  먼저 확인한다.
