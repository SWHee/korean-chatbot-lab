"use client";

import { AgentResult, Product, productHeading } from "../lib/agent-stream";
import { createRateScale, RateScale, ratePosition } from "../lib/rate-scale";

/** 20260102 형태의 시행일을 2026.01.02로 표시 */
function formatEffectiveDate(value: string) {
  if (!/^\d{8}$/.test(value)) return value;
  return `${value.slice(0, 4)}.${value.slice(4, 6)}.${value.slice(6)}`;
}

/** 본문 각주와 맞추기 위해 S1 대신 "근거 1"로 표기 */
function sourceLabel(sourceId: string) {
  return `근거 ${sourceId.replace(/^S/i, "")}`;
}

function formatRate(rate: number | null) {
  return rate !== null ? `${rate.toFixed(2)}%` : "—";
}

function RateRange({ product, scale }: { product: Product; scale: RateScale }) {
  const basePosition =
    product.base_interest_rate === null
      ? null
      : ratePosition(product.base_interest_rate, scale);
  const maxPosition =
    product.max_interest_rate === null
      ? null
      : ratePosition(product.max_interest_rate, scale);
  const segmentStart =
    basePosition !== null && maxPosition !== null
      ? Math.min(basePosition, maxPosition)
      : null;
  const segmentWidth =
    basePosition !== null && maxPosition !== null
      ? Math.abs(maxPosition - basePosition)
      : null;
  const ratesMatch =
    product.base_interest_rate !== null &&
    product.base_interest_rate === product.max_interest_rate;

  return (
    <div className="rate-range">
      <div className="rate-track" aria-hidden="true">
        {segmentStart !== null && segmentWidth !== null && segmentWidth > 0 && (
          <span
            className="rate-segment"
            style={{ left: `${segmentStart}%`, width: `${segmentWidth}%` }}
          />
        )}
        {basePosition !== null && (
          <span
            className="rate-marker"
            data-kind={ratesMatch ? "same" : "base"}
            style={{ left: `${basePosition}%` }}
          />
        )}
        {maxPosition !== null && !ratesMatch && (
          <span
            className="rate-marker"
            data-kind="max"
            style={{ left: `${maxPosition}%` }}
          />
        )}
      </div>
      <div className="rate-values">
        <span>기본 {formatRate(product.base_interest_rate)}</span>
        <span>최고 {formatRate(product.max_interest_rate)}</span>
      </div>
    </div>
  );
}

type Props = {
  result: AgentResult;
  activeSourceId: string | null;
};

export function EvidencePanel({ result, activeSourceId }: Props) {
  const rateScale = createRateScale(
    result.products.flatMap((product) => [
      product.base_interest_rate,
      product.max_interest_rate,
    ]),
  );

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
              <h3>{productHeading(result.products)}</h3>
              <span className="group-count">{result.products.length}건</span>
            </div>
            {rateScale && (
              <div className="rate-axis" aria-label="모든 후보에 공통으로 적용된 금리 구간">
                <span>{rateScale.min.toFixed(2)}%</span>
                <span>{rateScale.max.toFixed(2)}%</span>
              </div>
            )}
            <div className="card-list">
              {result.products.map((product, index) => (
                <article
                  className="card"
                  key={`${product.product_type}-${product.company_code}-${product.product_code}-${product.term_months}-${product.reserve_type ?? "none"}`}
                  style={{ "--i": index } as React.CSSProperties}
                >
                  <p className="company-name">
                    {product.company_name} · {product.term_months}개월
                  </p>
                  <p className="product-name">{product.product_name}</p>
                  {product.product_type === "saving" && product.reserve_type_name && (
                    <p className="product-detail">{product.reserve_type_name}</p>
                  )}
                  {rateScale && <RateRange product={product} scale={rateScale} />}
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
