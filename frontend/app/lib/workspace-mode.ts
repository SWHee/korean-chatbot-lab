export type WorkspaceMode = "welcome" | "searching" | "evidence" | "answer";

type WorkspaceState = {
  hasTurns: boolean;
  isStreaming: boolean;
  hasEvidence: boolean;
  hasError: boolean;
};

export function getWorkspaceMode({
  hasTurns,
  isStreaming,
  hasEvidence,
  hasError,
}: WorkspaceState): WorkspaceMode {
  if (!hasTurns) return "welcome";
  if (hasEvidence) return "evidence";
  if (isStreaming) return "searching";
  if (hasError) return "answer";
  return "answer";
}
