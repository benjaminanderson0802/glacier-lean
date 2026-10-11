# Questions for the trade lawyer before launch

Ask a U.S. trade lawyer who advises customs brokers to review the actual
workflow, pricing, customer terms, and broker contract. Give counsel this
README, `venture.json`, the batch flow, sample customer-facing screens, and a
sample draft CSV. Ask for a written opinion that addresses the proposed
service as implemented, including any conditions or changes required before
launch. Do not treat this checklist, an automated check, or a broker's
informal view as the required opinion.

## Questions to ask

1. **Does any part of this product conduct “customs business” for another
   person?** The service reads certificates and lab reports, extracts fields,
   checks tariff and citation codes, and prepares a CPSC registry CSV, but it
   does not certify or submit it. Given that customs-business definition
   includes certain document preparation and related activities for CBP, and
   CPSC certificate data may be provided in an ACE PGA Message Set, does any
   current feature constitute regulated customs business? Which precise
   features, statements, or handoffs must be removed, limited to an importer,
   or performed under a licensed broker? [19 U.S.C. § 1641(a)(2), (b)(1)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1641&num=0&edition=prelim);
   [CPSC eFiling FAQ](https://www.cpsc.gov/FAQ/eFiling-Frequently-Asked-Questions-FAQ).

2. **Who may prepare, review, certify, and transmit each CPSC data element in
   these proposed workflows?** Please apply the rules to an importer, a broker
   acting as importer of record, a broker identifying another responsible
   certifier, and this software vendor. Which action must remain with the
   importer or certifier, and which may an authorized broker perform? Is the
   current owner review and certification gate sufficient, or does the
   product need a different role or authorization model? [16 C.F.R.
   §§ 1110.7, 1110.11](https://www.ecfr.gov/current/title-16/chapter-II/subchapter-B/part-1110);
   [CPSC eFiling resources for importers](https://www.cpsc.gov/efiling/importers);
   [CPSC eFiling resources for brokers](https://www.cpsc.gov/efiling/brokers).

3. **Is the proposed flat monthly software/portal charge lawful in the broker
   arrangement described here?** The venture would charge a broker a fixed
   monthly amount for a white-label portal and batch-preparation software. It
   would not take a percentage of brokerage fees, refunds, duties, or entries,
   and it would not receive a per-entry referral commission. Under 19 C.F.R.
   § 111.36(b), would this arrangement nevertheless cause fees or other
   benefits from customs-business services for others to inure to an
   unlicensed person? What facts about the service, contract, payment flow,
   broker control, or customer relationship change that analysis? [19 C.F.R.
   § 111.36](https://www.ecfr.gov/current/title-19/section-111.36).

4. **Can the venture separately sell the $19/$29/$49 batch plans to
   importers?** Does charging an importer directly to extract, validate, and
   format certificate data create a licensing issue even if the importer
   reviews and certifies the output and sends it to its own broker? What
   boundaries or disclosures should apply, and should direct batch sales be
   disabled until a license or other arrangement is in place? [19 U.S.C.
   § 1641(a)(2), (b)(1)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1641&num=0&edition=prelim);
   [19 C.F.R. §§ 111.2, 111.36](https://www.ecfr.gov/current/title-19/part-111).

5. **Does the white-label broker portal or its marketing create a separate
   problem?** May the broker use its name and branding on this portal, invite
   importer customers, and describe the service as broker-supported
   preparation? What must make clear that Glacier is software, is not a
   customs broker, does not give a binding classification or compliance
   determination, and does not certify or file? Could the broker's use of the
   portal or name allow an unlicensed person to participate in the promotion,
   control, or direction of the broker's business? [19 U.S.C. § 1641(b)(1)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1641&num=0&edition=prelim);
   [19 C.F.R. §§ 111.28, 111.36](https://www.ecfr.gov/current/title-19/part-111).

6. **What may the software say about tariff codes and CPSC applicability?**
   The CPSC HTS list is a screening aid and the output currently checks a
   provided tariff code against that list and validates supplied CPSC rule
   citations. May the service present these results as matches or gaps, or
   would that cross into customs classification advice, broker work, or a
   compliance determination? What review, source citation, wording, and
   escalation should be required for an unknown or disputed code? [19 U.S.C.
   § 1641(a)(2)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1641&num=0&edition=prelim);
   [CPSC eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library).

7. **What contract and operating controls are required before the first
   broker is onboarded?** Please review the actual flat-fee agreement and
   customer terms for prohibited fee-sharing or referrals, broker independence
   and supervision, direct importer-broker communications, representations
   about licensing, responsibility for source data and errors, retention and
   access to supporting records, confidentiality, and liability. Which terms
   or controls are required by law, and which would you require as a condition
   of your opinion? [19 C.F.R. §§ 111.21, 111.28, 111.36](https://www.ecfr.gov/current/title-19/part-111);
   [19 U.S.C. § 1641(f), (i)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1641&num=0&edition=prelim).

8. **What must change before any future Product Registry API integration?**
   The current venture only creates a local draft; it has no CPSC account or
   API credential and does not transmit records. If that scope changes, may a
   software vendor operate with an importer or broker's token, what account
   and authorization must the account holder create, and what testing or
   security conditions apply before production data is used? [CPSC eFiling API
   Specifications V4](https://www.cpsc.gov/s3fs-public/eFiling-API-Specifications_V4.pdf);
   [CPSC eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library).

## Required written conclusion

Please state whether the venture, with the exact features and fee flows above,
may launch under the proposed structure; identify any facts you still need;
list required product, pricing, contract, or operational changes; and say
whether the flat monthly broker fee and direct per-batch plan each pass your
analysis. If you cannot conclude that both channels are permitted, specify
which channel must stay disabled. The broker-launch flow remains blocked until
the owner attaches and confirms this written opinion. The owner still signs
contracts, creates accounts, pays, certifies each batch, and submits any
filing.
