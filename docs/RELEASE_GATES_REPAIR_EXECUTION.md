# Commercial completion — repair execution, stock, finance and delivery

Status: **IN PROGRESS / NO-GO**. There are API contracts and UI changes, but no verified running PostgreSQL tests, npm build or browser walkthrough in this session.

## Delivered in current iteration
- AdditionalWork model + DB migration for supplemental defects during a repair.
- POST /api/v1/workorders/<order>/additional-works supports recording supplemental work, price and reason while in repair or QA.
- GET list and explicit decline; approval deliberately cannot be fabricated by an employee.
- Supplemental findings are not added to already approved estimates or invoices.
- UI surfaces proposed findings and lets reception record a new issue.
- Tests explicitly reject unsupported employee approval and post-ready additions.

## Hard commercial blockers
P0 — Customer-evidenced electronic approvals, invoice revisions/supplement invoices, line-level stock reservations and cost lot attribution, cancellation/returns, verified fiscal receipt/PSP, complete delivery documents and guarantee.
P0 — Executed PostgreSQL migrations & integration suite; browser/mobile end-to-end; tested disaster recovery with backup integrity.
P1 — Mechanic task assignment and time tracking, shop capacity planning, shift close reconciliation, payroll and managerial P&L.
P1 — Full customer-portal access verification, notifications, identity and multi-tenant penetration testing.
Do not mark release as GO until P0 is proven complete on an isolated deployment.

## Acceptance path
1. Owner creates a branch, invites users and verifies role isolation.
2. Adviser books and checks in customer vehicle, records intake photos and signed condition report.
3. Mechanic diagnoses and accepts assigned tasks; client independently approves estimate.
4. Parts clerk links issued parts to approved invoice lines, receiving/cost lots and exact repairs.
5. Mechanic submits unexpected problem -> supplemental quote -> independent client approval -> follow-on payable item. Attempting to bypass consent MUST fail.
6. QA confirms tests; cashier verifies payment/returns/receipt; adviser issues signed delivery documents, warranty record and closes visit. No hidden status jump.
7. Owner closes shift, reconciles physically counted cash, parts, time, wages and purchase documents, then inspects real P&L.
8. Expired subscription cannot mutate any tenant business record; owner retains export/read rights as agreed.
9. Complete teardown and restore test from backup, plus simulated concurrent parts reservation and PSP webhooks.
