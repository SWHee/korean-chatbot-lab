import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"


def main() -> None:
    # 1. 토크나이저 적재
    print("토크나이저 적재")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    print(f"토크나이저 적재 완료: {tokenizer.__class__.__name__}")

    # 2. MPS 또는 CPU와 dtype 결정
    if torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16
    else:
        device = "cpu"
        dtype = torch.float32

    print(f"실행 장치: {device}, dtype: {dtype}")

    # 3. 모델 가중치 적재
    print("모델 가중치 적재")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype=dtype,
        device_map=device,
    )
    model.eval()
    print(f"모델 적재 완료: {model.__class__.__name__}, device: {model.device}")

    # 4. 사용자 메시지 구성
    prompt = "AI 서비스 개발자가 되기 위한 첫 단계는 무엇인가요?"
    messages = [
        {"role": "user", "content": prompt}
    ]

    # 5. chat template 적용
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    print(f"chat template 적용 결과:\n{text}")

    # 6. tensor 변환 및 장치 이동
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    print(f"input_ids shape: {model_inputs.input_ids.shape}")
    print(f"input_ids device: {model_inputs.input_ids.device}")

    # 7. 추론 모드에서 답변 생성
    print("답변을 생성하는 중입니다.")
    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=128,
        )

    # 8. 새로 생성된 token만 분리
    input_length = model_inputs.input_ids.shape[1]
    generated_ids = generated_ids[:, input_length:]

    # 9. 문자열로 decode하고 출력
    response = tokenizer.batch_decode(
        generated_ids,
        skip_special_tokens=True,
    )[0]
    print(f"모델 답변:\n{response}")


if __name__ == "__main__":
    main()
