from chatbot.generator import Generator


PROMPT = "AI 서비스 개발자가 되기 위한 첫 단계는 무엇인가요?"


def main() -> None:
    """로컬 생성기를 실행해 답변을 출력한다."""
    generator = Generator()
    response = generator.generate(PROMPT)
    print(f"모델 답변:\n{response}")


if __name__ == "__main__":
    main()
