export type ClaimStatus =
  | "DRAFT"
  | "DOCUMENTS_PENDING"
  | "READY_FOR_REVIEW"
  | "UNDER_REVIEW"
  | "NEEDS_INFORMATION"
  | "APPROVED"
  | "REJECTED"
  | "CLOSED";

export type Claim = {
  id: string;
  policy_id: string;
  product_line: string;
  policy_version: string | null;
  jurisdiction: string;
  customer_reference: string;
  claim_type: string;
  incident_date: string | null;
  status: ClaimStatus;
  created_at: string;
  updated_at: string;
};

export type ClaimDocument = {
  id: string;
  document_type: string;
  filename: string;
  extraction_status: string;
  extracted_fields: Record<string, unknown>;
  created_at: string;
};

export type ProposedAction = {
  id: string;
  claim_id: string;
  run_id: string | null;
  action_type: string;
  tool_server: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  reason: string;
  risk_level: "medium" | "high";
  status: string;
  proposed_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ClaimDetail = {
  claim: Claim;
  documents: ClaimDocument[];
  proposed_actions: ProposedAction[];
};

export type DocumentRequirement = {
  document_type?: string;
  requirement?: string;
  reason?: string;
  source_id?: string;
  source_title?: string;
  source_excerpt?: string;
};

export type ClaimReview = {
  run_id: string;
  claim_id: string;
  required_documents: string[];
  present_documents: string[];
  missing_documents: string[];
  optional_documents: string[];
  conditional_documents: string[];
  document_requirements: DocumentRequirement[];
  evidence_status: "sufficient" | "insufficient";
  evidence_reason: string;
  evidence: Array<{ source_id: string; title: string; url: string; source: string }>;
  recommendation: string;
  proposed_action: ProposedAction | null;
};

export async function readApiError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export function displayLabel(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export async function loadClaimsWithDetails() {
  const response = await fetch("/api/claims", { cache: "no-store" });
  if (!response.ok) throw new Error(await readApiError(response));
  const { claims } = (await response.json()) as { claims: Claim[] };
  const details = await Promise.all(
    claims.map(async (claim) => {
      const detailResponse = await fetch(`/api/claims/${claim.id}`, { cache: "no-store" });
      if (!detailResponse.ok) throw new Error(await readApiError(detailResponse));
      return (await detailResponse.json()) as ClaimDetail;
    })
  );
  return details;
}
