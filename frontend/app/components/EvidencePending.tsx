type Props = {
  message: string;
};

export function EvidencePending({ message }: Props) {
  return (
    <section className="evidence evidence-pending" aria-label="근거 확인 중">
      <header className="evidence-head">
        <h2>답변의 근거를 확인하고 있어요</h2>
        <p>확인된 자료만 같은 자리에서 정리해 드립니다.</p>
      </header>

      <div className="evidence-pending-body">
        <svg viewBox="0 0 260 180" aria-hidden="true">
          <path className="pending-path pending-path-one" d="M34 44C82 44 74 90 124 90S172 46 226 46" />
          <path className="pending-path pending-path-two" d="M38 142C78 142 82 108 124 108S180 144 224 144" />
          <circle cx="34" cy="44" r="5" />
          <circle cx="226" cy="46" r="5" />
          <circle cx="38" cy="142" r="5" />
          <circle cx="224" cy="144" r="5" />
          <rect x="101" y="68" width="48" height="62" rx="8" />
          <path className="pending-document-line" d="M113 86h24M113 98h18M113 110h22" />
        </svg>
        <p>{message}</p>
        <span>법령·공시·상품 정보를 연결하는 중</span>
      </div>
    </section>
  );
}
