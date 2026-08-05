const STORY_PHASE_STARTS = [0, 0.36, 0.7] as const;
const STORY_PHASE_ENDS = [0.36, 0.7, 1] as const;

function clamp(value: number, min = 0, max = 1) {
  return Math.min(Math.max(value, min), max);
}

/** 전체 소개 스크롤 진행도를 세 개의 읽기 단계로 나눈다. */
export function storyPhaseAt(progress: number) {
  const current = clamp(progress);
  if (current < STORY_PHASE_STARTS[1]) return 0;
  if (current < STORY_PHASE_STARTS[2]) return 1;
  return 2;
}

/** 특정 단계 안에서의 진행도를 0~1로 반환한다. */
export function storyPhaseProgress(progress: number, phase: number) {
  const phaseIndex = Math.floor(clamp(phase, 0, STORY_PHASE_STARTS.length - 1));
  const start = STORY_PHASE_STARTS[phaseIndex];
  const end = STORY_PHASE_ENDS[phaseIndex];

  return clamp((clamp(progress) - start) / (end - start));
}
