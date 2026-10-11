# Owner steps

The business scope is Cook County, Illinois, individual-homeowner self-file preparation. Glacier prepares evidence and instructions; the homeowner reviews, signs, and files. These are the only owner actions for this scope.

## Once: confirm scope (about 2 minutes)

1. Read the [Assessor appeal rules](https://www.cookcountyassessoril.gov/official-appeal-rules-cook-county-assessor) and [Board of Review rules](https://www.cookcountyboardofreview.com/board-review-official-rules).
2. Record this exact scope choice in the venture decision log or owner dashboard: `Cook County, Illinois; individual-homeowner self-file preparation only; Glacier prepares packets and guides; the homeowner reviews, signs, and files; no representation or filing by Glacier.`

## For each appeal: review, sign, and file (allow about 15–30 minutes per portal)

1. Open the generated files at `$GLACIER_HOME/ventures/property-tax/packets/case.json`, `case.md`, and `case-filing-guide.md`. Check the PIN, notice, comparable sales, source/page citations, requested value, and every `uncertain — please check` item. Do not file while required evidence is missing or uncertain.
2. Check the [current Assessor and appeal calendar](https://www.cookcountyassessoril.gov/assessment-calendar-and-deadlines) for the property's township and current filing window. Do not rely on a date copied from an older packet.
3. If choosing an Assessor appeal, open [File an Appeal Online](https://www.cookcountyassessoril.gov/online-appeals), select **Residential**, enter the 14-digit PIN, follow the application prompts, attach the reviewed evidence, review the completed application, and submit it yourself by the township deadline. The official page says to confirm the township is open before starting and to submit only one application by the deadline.
4. If choosing a Board of Review appeal, open the [residential appeal page](https://www.cookcountyboardofreview.com/assessment-appeals/residential) and [property-owner portal guide](https://www.cookcountyboardofreview.com/portal-guide-property-owners). Follow: **Login → Submit Appeal → Property Over Assessment → enter PIN → Associated PINs (select no for one PIN) → Submit → enter appellant details → choose hearing preference → enter purchase year or Other → Next → confirm details → initial → Submit → choose whether to add evidence → Browse → select each reviewed file → choose its document type → verify attachments → Submit**. Complete the signature/initial and submit actions yourself.
5. Copy case-specific values from the generated packet and case intake. The 50-row public roll sample supplies only parcel metadata; it does not supply the homeowner's personal contact details, notice, requested value, or sale evidence. Use only the customer's own confirmed values:

   | Portal field | Value to use |
   | --- | --- |
   | PIN | `parcel_id` in `case.json` |
   | Appellant name and mailing/contact details | homeowner-confirmed case intake |
   | Requested value and appeal explanation | `customer_requested_value` and the reviewed packet narrative |
   | Comparable properties and evidence | only source-linked, reviewed items in `case.json` / attached source documents |
   | Township and filing year | verify against the current official calendar and notice |

6. Save the portal's receipt, filing ID, or docket number with the case record and track later notices yourself. If the property is not titled in the individual filer's own name, stop and check the current official rules before filing; this guide does not decide eligibility.

The Assessor's official filing page gives its current steps and deadline reminders. The Board portal sequence above follows its official [property-owner guide](https://www.cookcountyboardofreview.com/portal-guide-property-owners). Portal labels and requirements can change; verify them on the linked official pages each time. No phone call is required by these steps.
