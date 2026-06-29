"""Step 01. 토크나이저.

역할:
    원본 한국어 문장을 토큰과 토큰 id로 바꾸고, 다시 사람이 읽을 수 있는
    문장으로 되돌린다.

학습 포인트:
    - 토큰화(tokenization)가 무엇인지 이해하기,
    - 모델이 문자열 대신 숫자를 입력으로 받는 이유 이해하기,
    - 작은 어휘 사전(vocabulary)을 만드는 방법 익히기,
    - encode/decode 함수가 어떤 역할을 해야 하는지 이해하기.

나중의 프로젝트 구조:
    학습용 step 접두사가 필요 없어지면 이 파일은 `tokenizer.py`가 될 수 있다.
"""

from pathlib import Path


UNKNOWN_TOKEN = "<unk>"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "seed_corpus.txt"


def load_corpus(path: Path = DEFAULT_CORPUS_PATH) -> str:
    """corpus 파일을 읽어서 하나의 문자열로 반환"""

    return path.read_text(encoding="utf-8")


def tokenize(text: str) -> list[str]:
    """문자열을 문자 단위 토큰 리스트로 나누기"""

    return list(text)


def build_vocabulary(tokens: list[str]) -> list[str]:
    """중복 없는 토큰 목록을 만든다.

    UNKNOWN_TOKEN은 나중에 corpus에 없던 문자가 들어왔을 때 사용한다.
    """

    unique_tokens = set(tokens)
    sorted_tokens = sorted(unique_tokens)

    vocabulary = [UNKNOWN_TOKEN]    # 먼저 넣기
    vocabulary.extend(sorted_tokens)    # ex) ["<unk>", " ", ".", "녕", "안"]

    return vocabulary


def build_token_maps(vocabulary: list[str]) -> tuple[dict[str, int], dict[int, str]]:
    """token -> id, id -> token 변환용 dictionary를 만든다.
        
        문자와 숫자 사이의 번역 사전
    """

    token_to_id = {}
    id_to_token = {}

    for token_id, token in enumerate(vocabulary):
        token_to_id[token] = token_id   # 입력을 token id로 바꾸기 위해
        id_to_token[token_id] = token   # 출력을 token으로 바꾸기 위해

    return token_to_id, id_to_token


def encode(text: str, token_to_id: dict[str, int]) -> list[int]:
    """문자열을 token id 리스트로 바꾼다."""

    unknown_id = token_to_id[UNKNOWN_TOKEN]
    tokens = tokenize(text)
    token_ids = []

    for token in tokens:
        if token in token_to_id:
            token_id = token_to_id[token]
        else:
            token_id = unknown_id

        token_ids.append(token_id)

    return token_ids


def decode(token_ids: list[int], id_to_token: dict[int, str]) -> str:
    """token id 리스트를 다시 문자열로 바꾼다."""

    tokens = []

    for token_id in token_ids:
        token = id_to_token[token_id]
        tokens.append(token)

    text = "".join(tokens)
    return text


def main() -> None:
    """토크나이저의 전체 흐름을 작은 예제로 확인한다."""

    corpus = load_corpus()
    tokens = tokenize(corpus)
    vocabulary = build_vocabulary(tokens)
    token_to_id, id_to_token = build_token_maps(vocabulary)

    sample_text = "나는 한국어 챗봇을 만들고 있어요."
    encoded = encode(sample_text, token_to_id)
    decoded = decode(encoded, id_to_token)

    print(f"corpus 전체 문자 수: {len(corpus)}")
    print(f"전체 토큰 수: {len(tokens)}")
    print(f"vocabulary 크기: {len(vocabulary)}")
    print(f"vocabulary 앞 20개: {[repr(token) for token in vocabulary[:20]]}")
    print(f"샘플 문장: {sample_text}")
    print(f"encoded: {encoded}")
    print(f"decoded: {decoded}")
    print(f"복원 성공 여부: {sample_text == decoded}")


if __name__ == "__main__":
    main()
