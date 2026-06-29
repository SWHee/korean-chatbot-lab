"""Step 02. 데이터셋.

역할:
    인코딩된 토큰 id를 다음 토큰 예측 학습용 입력/정답 예제로 바꾼다.

학습 포인트:
    - 입력 시퀀스와 정답 시퀀스가 한 칸씩 밀리는 구조 이해하기,
    - 언어 모델이 다음 토큰을 예측하며 학습하는 이유 이해하기,
    - Python 리스트가 PyTorch 텐서로 바뀌는 과정 익히기,
    - 학습 전에 텐서 shape를 어떻게 준비하는지 이해하기.

나중의 프로젝트 구조:
    데이터 흐름이 커지면 이 파일은 `dataset.py`가 되거나 `data.py` 계열
    모듈로 분리될 수 있다.
"""


def make_next_token_example(token_ids: list[int]) -> tuple[list[int], list[int]]:
    """하나의 token id 리스트를 입력 x와 정답 y로 나눈다.

    예:
        token_ids = [10, 20, 30, 40]
        x = [10, 20, 30]
        y = [20, 30, 40]
    """

    input_ids = token_ids[:-1]
    target_ids = token_ids[1:]

    return input_ids, target_ids


def make_fixed_length_examples(token_ids: list[int], context_size: int) -> list[tuple[list[int], list[int]]]:
    """긴 token id 리스트에서 일정 길이의 학습 예제를 여러 개 만든다.

    context_size는 모델이 한 번에 볼 토큰 개수다.
    """
    examples = []
    window_size = context_size + 1

    last_start_index = len(token_ids) - window_size

    for start_index in range(last_start_index + 1):
        end_index = start_index + window_size
        window = token_ids[start_index:end_index]

        input_ids, target_ids = make_next_token_example(window)
        example = (input_ids, target_ids)
        examples.append(example)

    return examples


def main() -> None:
    """dataset 생성 흐름을 작은 예제로 확인한다."""

    sample_token_ids = [10, 20, 30, 40, 50]
    input_ids, target_ids = make_next_token_example(sample_token_ids)
    examples = make_fixed_length_examples(sample_token_ids, context_size=3)

    print(f"원본 token ids: {sample_token_ids}")
    print(f"입력 x: {input_ids}")
    print(f"정답 y: {target_ids}")
    print()
    print("context_size=3일 때 만들어지는 학습 예제")

    for index, example in enumerate(examples):
        example_input_ids, example_target_ids = example
        print(f"example {index}")
        print(f"  x: {example_input_ids}")
        print(f"  y: {example_target_ids}")


if __name__ == "__main__":
    main()
