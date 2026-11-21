export type EvidenceKind = "observed" | "inferred";

export function evidenceLabel(kind: EvidenceKind): string {
  if (kind === "observed") {
    return "Observed";
  }
  return "Inferred, not confirmed";
}
