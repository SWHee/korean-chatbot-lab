/** Agent SSE 스트림의 타입과 파서 */

export type Stage = "analyze" | "tools" | "generate" | "clarify" | "out_of_scope";

export type Source = {
  source_id: string;
  law_name: string;
  article_no: string;
  effective_date: string;
};

export type Product = {
  product_type: "deposit" | "saving";
  disclosure_month: string;
  company_code: string;
  product_code: string;
  company_name: string;
  product_name: string;
  term_months: number;
  base_interest_rate: number | null;
  max_interest_rate: number | null;
  reserve_type?: string;
  reserve_type_name?: string;
};

/** 후보 상품 유형에 맞춘 근거 패널 제목 */
export function productHeading(products: Product[]) {
  if (products.length === 0) return "금융상품 후보";
  if (products.every((product) => product.product_type === "saving")) {
    return "적금 후보";
  }
  if (products.every((product) => product.product_type === "deposit")) {
    return "정기예금 후보";
  }
  return "금융상품 후보";
}

export type ToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  status: string | null;
};

export type AgentResult = {
  thread_id: string;
  answer: string;
  route: string;
  product_preferences: Record<string, unknown>;
  missing_fields: string[];
  tools: ToolCall[];
  sources: Source[];
  products: Product[];
  execution_seconds: number;
};

export type StreamEvent =
  | { event: "status"; stage: Stage; tools?: string[] }
  | { event: "token"; text: string }
  | { event: "result"; result: AgentResult }
  | { event: "error"; message: string };

/** 기다리는 동안 보여 줄 안내 문장. 단계 이름이 아니라 지금 무엇을 하는지로 쓴다. */
export const WAITING_MESSAGE: Record<Stage, string> = {
  analyze: "질문을 살펴보고 있어요",
  tools: "법령과 상품 정보를 찾고 있어요",
  generate: "답변을 정리하고 있어요",
  clarify: "필요한 조건을 확인하고 있어요",
  out_of_scope: "안내할 수 있는 내용인지 확인하고 있어요",
};

/** SSE 한 블록(event/data 한 쌍)을 StreamEvent로 변환 */
export function parseEventBlock(block: string): StreamEvent | null {
  const name = block.match(/^event: (.+)$/m)?.[1];
  const payload = block.match(/^data: (.+)$/m)?.[1];
  if (!name || !payload) return null;

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(payload);
  } catch {
    return null;
  }

  if (name === "status") {
    return {
      event: "status",
      stage: (data.stage as Stage) ?? "analyze",
      tools: Array.isArray(data.tools) ? (data.tools as string[]) : undefined,
    };
  }
  if (name === "token") {
    return { event: "token", text: typeof data.text === "string" ? data.text : "" };
  }
  if (name === "result") {
    return { event: "result", result: data as unknown as AgentResult };
  }
  if (name === "error") {
    const message = typeof data.message === "string" ? data.message : "알 수 없는 오류가 발생했어요.";
    return { event: "error", message };
  }
  return null;
}

/** Response body를 읽어 StreamEvent를 순서대로 내보내는 async generator */
export async function* readAgentStream(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const streamEvent = parseEventBlock(block);
      if (streamEvent) yield streamEvent;
    }
  }
}
