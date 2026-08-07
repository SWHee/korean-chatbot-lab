type CryptoWithRandomUuid = {
  randomUUID?: () => string;
};

export function createThreadId(_cryptoApi?: CryptoWithRandomUuid) {
  const cryptoApi = _cryptoApi ?? globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") return cryptoApi.randomUUID();

  const randomPart = Math.random().toString(36).slice(2, 12) || "0";
  return `thread-${Date.now()}-${randomPart}`;
}
