# Operational implementation progress

Status: **IN PROGRESS / NO-GO**. All changes committed directly to main without GitHub Actions.

## Implemented in current development pass
1. Supplementary defect capture after repair starts: AdditionalWork and migration 0002; staff can record and decline findings.
2. New defects are NOT silently approved and are NOT automatically charged; independent customer approval remains unavailable.
3. UI of work orders shows separate unapproved findings and lets adviser record them.
4. RepairTask and migration 0003; mechanic assignment scoped to tenant/branch, task start/finish and exclusive running task per mechanic.
5. Work order QA cannot start while tasks remain assigned or running.
6. New test contracts for additional works, task lifecycle and tenant isolation.

## Unfinished, high-priority commercial release features
- Signed/electronically authenticated customer additional work approval, legal evidence, estimate revision and change-order invoice integration.
- Invoice/approved line -> exact part SKU -> reservation -> movement -> cost lot traceability and returns.
- Sales/settlement integration, verified PSP notifications, Russian KKT/OFD receipts and compliant refunds.
- Completion of legal handover, warranty, repair closure and visit closure.
- Full payroll, labor costing, cash shift and inventory reconciliation, owner profit calculations.
- Staging PostgreSQL migrations and automated integration tests, TypeScript build, browser smoke tests and restore drill.

## Test environment constraints
GitHub connector was used for the code updates. Current execution runtime lacks Django and cannot resolve github.com via git clone; therefore the fresh backend tests and frontend bundle were NOT executed, and database migration results remain unverified. Do not deploy to paying clients until test suite is green in staging.
