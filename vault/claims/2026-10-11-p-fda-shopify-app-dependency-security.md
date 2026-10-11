---
id: CLM-2026-10-11-P-FDA-SHOPIFY-APP-DEPENDENCY-SECURITY
filed_by: V-FDA
run_id: null
node_id: null
checkpoint: PH12.15
kind: bug
summary: Pinned Shopify app dependency tree has unresolved high-severity security advisories
evidence: "From ventures/shopify-fda-app, `npm audit --omit=dev` reports 7 vulnerabilities (6 high, 1 low), including deepmerge-ts/effect through Prisma and Vite 7.3.1 advisories. `npm audit fix --dry-run` leaves the Prisma and Shopify CLI advisories and reports that full remediation would force Prisma 6.12.0 and @shopify/cli 3.77.1, both breaking-version changes from the pinned dependencies; no dependency files were changed."
attempts_made: 0
status: filed
assigned_to: app-security-fixer
resolution: null
resolution_evidence: null
---

Before App Store submission, review the reported advisories against the pinned production and development dependency graph. Resolve them with compatible, deliberately pinned free/open-source versions, then rerun the app tests, typecheck, build, and Shopify automated checks. Do not use `npm audit fix --force` without reviewing the proposed Prisma and Shopify CLI changes and proving the app still works.
