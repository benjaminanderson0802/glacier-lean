# Utility audits

Utility audits prepares a simple estimate for a narrow Indiana rule: a seller may qualify for the restaurant electricity election when its annual statewide prepared-food sales percentage is at least 75%; the election is 50% of the sales tax on electricity through one meter. The calculator requires the customer to confirm annual statewide totals using DOR's published food-sales formula, including all of the seller's Indiana establishments. It keeps those seller-level threshold totals separate from the selected meter's ST-200R form figures. Indiana DOR decides whether an application is accepted.

The calculator requires customer-confirmed annual statewide food-sales totals and 12 consecutive months of selected-meter sales figures and bills. It prepares field data for Indiana Form ST-200R and lists missing details. Indiana DOR issues ST-109R after it accepts the application; Glacier does not create that certificate. An optional flat-rate scenario compares customer-entered published rates, annual kWh, fixed charges, and source links. It does not fetch or validate links, confirm plan availability, or account for demand charges, taxes, riders, and other tariff charges; the customer must confirm the full tariff with the utility. This version does not read PDFs or connect to UtilityAPI/Arcadia. It never signs forms, contacts a utility, or files with the state. The customer must verify every number, complete missing fields, attach bills, sign and submit the application. The customer also sends any certificate issued by DOR to their utility provider.

Keep source bills and receipts on the customer's machine. The customer or owner should remove incoming records and closed-job drafts within 30 days after the job closes unless the customer asks to retain them. This version does not delete files automatically.

Launch state recommendation: Indiana. **The owner must confirm Indiana before any customer launch.** Billing is disabled. A share of refunds or first-year savings remains unavailable until the owner records approval of the model and its legal basis. This build uses only standard-library Python and local customer-supplied records.

## Your steps

1. Confirm Indiana as the launch state before offering the service. Read the [DOR utility exemption page](https://www.in.gov/dor/i-am-a/business-corp/utility-sales-tax-exemption/), [Bulletin #11](https://www.in.gov/dor/files/sib11.pdf), and [Bulletin #29 Appendix B](https://www.in.gov/dor/files/sib29.pdf).
2. Provide 12 months of monthly receipt records and electricity bills, and confirm the single meter. Use the official [ST-200R form](https://forms.in.gov/Download.aspx?id=16301).
3. Review the prepared fields against ST-200R, complete gaps, sign and submit the application yourself. After DOR approval, send the issued ST-109R to the utility.

See PROOF.md for focused checks and the rule sources. Test data is synthetic.
