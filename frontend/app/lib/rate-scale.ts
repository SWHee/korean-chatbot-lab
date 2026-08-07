const RATE_SCALE_STEP = 0.5;

export type RateScale = {
  min: number;
  max: number;
};

/** 후보 전체가 공유하는 0.5%p 단위 금리 구간 */
export function createRateScale(rates: Array<number | null>): RateScale | null {
  const values = rates.filter(
    (rate): rate is number => typeof rate === "number" && Number.isFinite(rate),
  );
  if (values.length === 0) return null;

  let min = Math.floor(Math.min(...values) / RATE_SCALE_STEP) * RATE_SCALE_STEP;
  let max = Math.ceil(Math.max(...values) / RATE_SCALE_STEP) * RATE_SCALE_STEP;

  if (min === max) {
    min = Math.max(0, min - RATE_SCALE_STEP);
    max += RATE_SCALE_STEP;
  }

  return { min, max };
}

/** 공유 금리 구간 안에서 사용할 백분율 위치 */
export function ratePosition(rate: number, scale: RateScale): number {
  const position = ((rate - scale.min) / (scale.max - scale.min)) * 100;
  const clamped = Math.min(Math.max(position, 0), 100);
  return Math.round(clamped * 100) / 100;
}
