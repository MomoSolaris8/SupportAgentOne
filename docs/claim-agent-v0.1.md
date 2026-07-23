# Claim Agent Business Contract v0.1

## Outcome

SupportAgent assists a claim handler with reviewing an insurance claim. It may
read claim data, retrieve policy evidence, inspect submitted documents, and
propose external actions. It must not execute a claim-status change without a
persisted approval.

## Actors

- Claim handler: owns the claim in v0.1, reviews evidence, and approves or
  rejects proposed actions.
- Supervisor: future role for high-risk terminal transitions such as approved,
  rejected, or closed. Those transitions are deliberately not executable in
  v0.1.
- Administrator: configures MCP servers and tool policy; not part of the claim
  decision itself.

## Claim states

```text
DRAFT -> DOCUMENTS_PENDING -> READY_FOR_REVIEW -> UNDER_REVIEW
                                      |                |
                                      +-> NEEDS_INFORMATION
```

`APPROVED`, `REJECTED`, and `CLOSED` are recognized terminal states but are
outside the v0.1 execution scope.

## Claim data contract

Every new claim must identify the policy context used to select rules and
knowledge:

- `product_line` - household, residential building, vehicle, liability, or
  legal expense;
- `policy_version` - the applicable policy/rule version when known;
- `jurisdiction` - `DE` in the synthetic v0.1 dataset;
- `claim_type` - the incident category within the product line.

Document requirements are source-backed records classified as `required`,
`optional`, or `conditional`. Only absent `required` documents are blocking.
Few-shot examples teach review behavior and never act as policy facts.

## Action policy

| Action | Risk | v0.1 policy |
| --- | --- | --- |
| Retrieve policy or claim | Low/read | May run automatically |
| Inspect claim documents | Low/read | May run automatically |
| Create Jira issue | Medium/write | Persist proposal; require confirmation |
| Send Teams notification | Medium/write | Persist proposal; require confirmation |
| Update claim status | High/write | Persist proposal; require approval |

The model may propose an action. Only deterministic application code may
approve and later execute it. A browser confirmation flag is not evidence of
approval; approval must be stored with the actor and timestamp.

## v0.1 safety invariants

1. A user can only access claims that they own.
2. Proposed actions start in `WAITING_FOR_APPROVAL` for all writes.
3. An action cannot move to `APPROVED` without a persisted approval record.
4. A rejected, executed, or failed action cannot be approved again.
5. Claim status transitions are validated by deterministic code.
6. Terminal claim decisions are not executable in v0.1.

## First vertical slice

1. Create and read a claim.
2. Register document metadata against the claim.
3. Create a structured proposed action.
4. Approve or reject that proposal through an authenticated API.
5. Retain an audit event for every state-changing operation.

Tool execution, postcondition verification, and the claim-centered frontend are
the next slice built on this persisted contract.
