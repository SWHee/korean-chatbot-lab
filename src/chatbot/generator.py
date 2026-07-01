import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
MAX_NEW_TOKENS = 128


class Generator:
    """Qwen3 모델로 사용자 질문의 답변 생성"""

    def __init__(self) -> None:
        """토크나이저와 모델을 한 번 적재"""
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

        # Apple Silicon은 MPS와 float16으로 메모리 사용 절감
        if torch.backends.mps.is_available():
            device = "mps"
            dtype = torch.float16
        else:
            device = "cpu"
            dtype = torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=dtype,
            device_map=device,
        )
        self.model.eval()

    def generate(self, prompt: str) -> str:
        """사용자 문장을 모델 입력으로 바꿔 답변 문자열 반환"""
        messages = [
            {"role": "user", "content": prompt}
        ]

        # Qwen3가 학습한 대화 형식으로 변환
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # 입력 tensor를 모델과 같은 장치로 이동
        model_inputs = self.tokenizer(
            [text],
            return_tensors="pt",
        ).to(self.model.device)

        # 추론 시 gradient 계산 생략
        with torch.inference_mode():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=MAX_NEW_TOKENS,
            )

        # 입력 token을 제외하고 새로 생성된 답변만 복원
        input_length = model_inputs.input_ids.shape[1]
        response_ids = generated_ids[:, input_length:]

        return self.tokenizer.batch_decode(
            response_ids,
            skip_special_tokens=True,
        )[0]
