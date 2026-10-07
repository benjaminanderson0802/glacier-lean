# Glacier funding and maintenance proposal

**Research checked: 7 October 2026. Proposal only; this does not approve spending, fundraising, or a change to project policy.** Glacier is Apache-2.0 and is intended to stay free, local-first, portable, and usable without telemetry, ads, paid-only features, or a hosted service.

## Costs to cover

- **Maintainer time:** review, releases, security reports, documentation, and support are the main recurring cost. There is no honest public price for volunteer hours; the owner would need to choose a time budget and any stipend target.
- **CI beyond free use:** GitHub says standard Actions runners are free for public repositories. For private GitHub Free use, the published allowance is 2,000 minutes/month; beyond included allowances, current baseline rates vary by runner (Linux 2-core $0.006/min, Windows 2-core $0.010/min, macOS $0.062/min). Glacier is public, so ordinary public-repository CI currently has no runner-minute bill. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- **Code signing later:** do not assume this needs a budget line. SignPath Foundation advertises OSS signing at no charge, but it has eligibility, release, repository, role, and policy requirements. [SignPath OSS terms](https://signpath.org/terms.html)
- **Docs hosting:** GitHub Pages is available for public repositories on GitHub Free, at $0; subject to its limits and acceptable-use rules. A custom domain is optional and its registrar price varies. [GitHub Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

## Funding options

All options below fund the same public Apache-2.0 product. None requires a cloud-only version, telemetry, ads, selling user data, or withholding features. “Effort” is a practical estimate, not a vendor quote.

### 1. GitHub Sponsors

Supporters give one-time or monthly donations through a project or maintainer profile. **Fees:** GitHub charges no fee for individual-account sponsorships; organization sponsorships can have fees up to 6% (3% service and 3% card processing; invoicing can avoid the card portion). Payment and tax rules depend on location. **Give up:** public tiers can create pressure to offer perks; keep tiers to thanks/recognition and never promise priority that changes project decisions. **Effort:** low to start, modest ongoing bookkeeping. Similar project: [Homebrew Sponsors](https://github.com/sponsors/homebrew), which says funds support maintainers, CI hosting, and project work. [Fee details](https://docs.github.com/en/sponsors/sponsoring-open-source-contributors/about-sponsorships-fees-and-taxes)

### 2. Open Collective through a fiscal host

Contributions and expenses appear in a public budget; a host can provide legal and financial administration without Glacier forming its own entity. **Fees:** Open Source Collective currently lists a 10% fee on funds raised; processor charges may also apply. Other hosts set their own rates (Open Collective says commonly 4–10%). **Give up:** the host handles money under its rules; admins must publish budgets/expenses and accept host eligibility and reporting requirements. **Effort:** medium to apply, then ongoing expense records. Similar project: [Homebrew on Open Collective](https://opencollective.com/homebrew). [OSC fees](https://opencollective.com/opensource/apply/intro), [host pricing](https://documentation.opencollective.com/why-open-collective/pricing)

### 3. NLnet / NGI-style grants

Apply for a defined public-interest deliverable, such as portable workflows, local-first usability, or security. **Fees:** no applicant fee is listed; grant amount depends on the call and approved budget. As of this check, NLnet says the NGI0 Commons Fund final call has closed; future calls should be checked rather than assumed. **Give up:** application and milestone/reporting work, with grant scope and eligibility constraints; results remain open source. **Effort:** high for an application and delivery reporting. Similar projects include [Mastodon for institutions](https://nlnet.nl/project/MastodonInstitutions/) and [Manyfold](https://nlnet.nl/project/Manyfold/). [Current NGI Zero calls](https://nlnet.nl/NGIzero/)

### 4. Sovereign Tech Agency public funding

Seek a commissioned investment for a specific security, resilience, or maintenance package that serves public digital infrastructure. Applications are possible, but selection is competitive and suitability depends on the Agency’s priorities. **Fees:** no application fee is published; funding amount is scoped per project and is not a standard grant price. **Give up:** delivery contracts, legal/procurement checks, public reporting, and defined work packages; no product lock-in is needed, but the work must fit public-interest priorities. **Effort:** high. Similar projects include [FreeBSD infrastructure modernization](https://www.freebsd.org/status/report-2025-01-2025-03/foundation-infrastructure-modernization/) and [Drupal security work](https://www.drupal.org/association/blog/drupal-to-enhance-security-and-developer-tools-thanks-to-sovereign-tech-fund-investment). [Agency program](https://www.sovereign.tech/programs/fund)

### 5. Paid support or consulting for organisations

Organisations pay for onboarding, migration, training, or help using the same public software; no exclusive features or hosted dependency. **Fees:** set by the provider and agreed per engagement; there is no platform fee if contracted directly, though payment, tax, and legal costs may apply. **Give up:** maintainer time and potential conflicts; publish the scope and keep support from buying influence over roadmap or security decisions. **Effort:** medium to high per engagement. Similar model: [Homebrew offers paid support tiers through Sponsors](https://github.com/sponsors/homebrew); [Nextcloud lists commercial support](https://nextcloud.com/support/).

### 6. Donated CI capacity

A company or community donates runner time or hardware for testing, without access to private user data or control over release decisions. Prefer public, auditable runners and reproducible jobs. **Fees:** $0 cash to Glacier if donated; the donor bears hardware, power, network, and administration costs. Public GitHub Actions standard runners are already free, so this only helps for capacity or platforms beyond the free public setup. **Give up:** some operational independence and time to review runner security, access, and availability; keep donated capacity replaceable. **Effort:** medium to set up, ongoing security review. Similar example: [GitHub says public-repository Actions are free](https://github.com/features/actions); [OpenSSF Alpha-Omega works directly with open-source projects on security improvements](https://openssf.org/community/alpha-omega/), though this is funding/support rather than a generic runner-donation program.

## Recommended first step

**Owner decision:** decide whether to enable a simple GitHub Sponsors profile with donation-only tiers and no feature promises. It is the lowest-admin, reversible way to learn whether supporters exist; it does not require changing Glacier’s free/local product. Before activation, the owner would need to check personal or organization eligibility and supported payment country, provide required tax and bank details privately to GitHub, choose the receiving account and public wording, and decide whether individual-only donations are acceptable. If the project later needs transparent expense handling or a legal entity, compare fiscal hosts before accepting organisational funds. No account or funding page is created by this proposal.

## If the owner does nothing

Glacier continues to work as free, public Apache-2.0 software. Public CI and public docs hosting currently have free paths, and eligible OSS code signing may also be free. The main risk is maintainer time: releases, review, support, security response, and platform changes may slow or pause if volunteer capacity runs out. There is no new user lock-in or product breakage from choosing no funding model.
