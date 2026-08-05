"use client";

import { AgentResult, Product } from "../lib/agent-stream";

/** 20260102 형태의 시행일을 2026.01.02로 표시 */
function formatEffectiveDate(value: string) {
  if (!/^\d{8}$/.test(value)) return value;
  return `${value.slice(0, 4)}.${value.slice(4, 6)}.${value.slice(6)}`;
}

/** 본문 각주와 맞추기 위해 S1 대신 "근거 1"로 표기 */
function sourceLabel(sourceId: string) {
  return `근거 ${sourceId.replace(/^S/i, "")}`;
}

/** 모든 후보를 같은 축에서 비교하기 위한 금리 최대값 */
function maxRate(products: Product[]) {
  const rates = products.flatMap((product) =>
    [product.base_interest_rate, product.max_interest_rate].filter(
      (rate): rate is number => typeof rate === "number",
    ),
  );
  return rates.length > 0 ? Math.max(...rates) : 0;
}

function RateRow({
  kind,
  label,
  rate,
  ceiling,
}: {
  kind: "base" | "max";
  label: string;
  rate: number | null;
  ceiling: number;
}) {
  const ratio = rate !== null && ceiling > 0 ? Math.max(rate / ceiling, 0.04) : 0;

  return (
    <div className="rate-row" data-kind={kind}>
      <span>{label}</span>
      <span className="rate-track">
        <span className="rate-fill" style={{ width: `${ratio * 100}%` }} />
      </span>
      <span className="rate-value">{rate !== null ? `${rate.toFixed(2)}%` : "—"}</span>
    </div>
  );
}

type Props = {
  result: AgentResult;
  activeSourceId: string | null;
};

export function EvidencePanel({ result, activeSourceId }: Props) {
  const ceiling = maxRate(result.products);

  return (
    <section className="evidence" aria-label="이 답변의 근거">
      <header className="evidence-head">
        <h2>이 답변의 근거</h2>
        <p>답변을 작성할 때 실제로 사용한 자료입니다.</p>
      </header>

      <div className="evidence-body scroll">
        {result.sources.length > 0 && (
          <div className="evidence-group">
            <div className="group-head">
              <h3>법령 조문</h3>
              <span className="group-count">{result.sources.length}건</span>
            </div>
            <div className="card-list">
              {result.sources.map((source, index) => (
                <article
                  className="card"
                  key={`${source.source_id}-${source.article_no}-${source.effective_date}-${index}`}
                  style={{ "--i": index } as React.CSSProperties}
                  data-active={activeSourceId === source.source_id}
                >
                  <p className="source-line">
                    <span className="source-chip">{sourceLabel(source.source_id)}</span>
                    <span className="law-name">{source.law_name}</span>
                  </p>
                  <p className="article-no">{source.article_no}</p>
                  <p className="effective-date">
                    시행 {formatEffectiveDate(source.effective_date)}
                  </p>
                </article>
              ))}
            </div>
          </div>
        )}

        {result.products.length > 0 && (
          <div className="evidence-group">
            <div className="group-head">
              <h3>정기예금 후보</h3>
              <span className="group-count">{result.products.length}건</span>
            </div>
            <div className="card-list">
              {result.products.map((product, index) => (
                <article
                  className="card"
                  key={`${product.company_code}-${product.product_code}-${product.term_months}`}
                  style={{ "--i": index } as React.CSSProperties}
                >
                  <p className="company-name">
                    {product.company_name} · {product.term_months}개월
                  </p>
                  <p className="product-name">{product.product_name}</p>
                  <div className="rate-rows">
                    <RateRow
                      kind="base"
                      label="기본"
                      rate={product.base_interest_rate}
                      ceiling={ceiling}
                    />
                    <RateRow
                      kind="max"
                      label="최고"
                      rate={product.max_interest_rate}
                      ceiling={ceiling}
                    />
                  </div>
                  <p className="disclosure">{product.disclosure_month} 공시 기준</p>
                </article>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
