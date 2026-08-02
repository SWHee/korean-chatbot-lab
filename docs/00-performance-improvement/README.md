# 성능·품질 개선 기록

이 폴더는 POC 이후 가장 먼저 다시 볼 개선 기록이다. 응답 시간뿐 아니라 검색
정확도, 답변 신뢰성, 출력 안정성과 사용자 경험을 **개선 단위별로 분리**한다.
속도가 빨라져도 답변 품질이 낮아지면 개선으로 판단하지 않는다.

## 문서 작성 원칙

- 한 문서는 한 가지 방법이나 실험만 다룬다.
- 같은 문제를 해결해도 바꾼 기술이 다르면 문서를 나눈다.
- 여러 후보를 안내하는 문서는 폴더의 `README.md`로 두고 결과 문서처럼 취급하지 않는다.
- 아직 실행하지 않은 아이디어마다 빈 문서를 만들지 않는다.
- 비교에서는 한 번에 한 변수를 바꾸고 이전 기준선을 명시한다.

개별 개선 문서는 필요한 항목만 다음 순서로 작성한다.

1. **관찰과 기준선**: 발견한 문제, 현재 방식과 당시 선택 이유
2. **후보와 선택 근거**: 비교한 방법과 선택·제외 이유
3. **적용**: 바꾼 코드·데이터·설정과 고정한 조건
4. **비교 결과**: 이전·이후 수치와 대표 성공·실패 사례
5. **결정과 남은 한계**: 채택 여부, 해결하지 못한 문제와 다음 조건

구현 전에는 1~2번까지만 작성한다. 당시 선택 이유가 기록에 없으면 추측하지 않고
근거가 없다고 밝힌다.

## 개선 지도

| 개선 단위 | 현재 상태 | 확인된 결정 |
| --- | --- | --- |
| [`01-rag-latency`](01-rag-latency/) | 측정 설계 | 토큰 상한을 아직 변경하지 않음 |
| [`02-rag-response-reliability`](02-rag-response-reliability/) | Structured Output v2 구현 | 간결화 Prompt 후보는 미채택 |
| [`03-early-fallback-streaming`](03-early-fallback-streaming/) | 구현·단위 검증 | `can_answer=false` 즉시 고정 안내로 전환 |
| [`04-retrieval-robustness`](04-retrieval-robustness/) | 개선 지도 작성 | Agent POC 뒤 기술별 문서로 분리 |
| [`05-safe-answer-coverage`](05-safe-answer-coverage/) | 문제·비교 기준 정리 | 안전성을 유지하며 유효 답변 도달률 개선 |

검색 개선의 전체 후보와 순서는
[`04-retrieval-robustness/README.md`](04-retrieval-robustness/README.md)에서 찾는다.
과도한 거절과 금융 안내 안전성의 균형은
[`05-safe-answer-coverage/README.md`](05-safe-answer-coverage/README.md)에서 다룬다.
