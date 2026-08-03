const DEFAULT_API_URL = "http://127.0.0.1:8000";
const AGENT_STREAM_PATH = "/ask-agent/stream";

export async function POST(request: Request) {
  let question: unknown;
  let threadId: unknown;

  try {
    ({ question, threadId } = await request.json());
  } catch {
    return new Response("질문 형식을 확인해 주세요.", { status: 400 });
  }

  if (typeof question !== "string" || !question.trim()) {
    return new Response("질문을 입력해 주세요.", { status: 400 });
  }

  if (typeof threadId !== "string" || !threadId.trim()) {
    return new Response("새 대화를 시작한 뒤 다시 시도해 주세요.", { status: 400 });
  }

  const apiUrl = process.env.CHATBOT_API_URL ?? DEFAULT_API_URL;

  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}${AGENT_STREAM_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, message: question.trim() }),
      cache: "no-store",
    });

    if (!response.ok) {
      return new Response("법령 답변 서버가 요청을 처리하지 못했습니다.", {
        status: response.status,
      });
    }

    if (!response.body) {
      return new Response("법령 답변 서버의 스트림이 비어 있습니다.", { status: 502 });
    }

    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
      },
    });
  } catch {
    return new Response(
      "FastAPI에 연결하지 못했습니다. FastAPI 실행 상태를 확인해 주세요.",
      { status: 502 },
    );
  }
}
