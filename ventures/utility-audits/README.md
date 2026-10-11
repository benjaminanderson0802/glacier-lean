# Utility audits

This venture prepares customer-reviewed Indiana utility exemption estimates and unsigned application data. Indiana is the recommended launch state; Benjamin must confirm it before customer work. The state decides whether an application qualifies and issues any utility exemption certificate.

## Two Indiana paths

### Restaurant election

A restaurant that meets Indiana's 75% prepared-food receipts test may elect a 50% exemption of sales tax on electricity measured through one meter by applying on Form ST-200R. Use Bulletin #11 for the restaurant rule and Bulletin #29 Appendix B for the prepared-food calculation. The customer confirms annual totals across all Indiana establishments and supplies twelve consecutive months of meter and receipt records.

### Predominant-use utility study

Other qualifying businesses may apply using Form ST-200 and a utility study. Bulletin #55 is the current DOR bulletin specifically about utility sales tax and says the 100% meter exemption requires more than 50% exempt use; each meter is considered separately. Bulletin #64 provides current manufacturing and production exemption definitions, effective October 1, 2026. A business that does not meet the predominant-use threshold may have a separate partial production exemption, which this calculator does not determine.

The included CSV path expects twelve monthly rows for one meter and utility. `usage_units` and `sales_tax_paid` are transcribed from bills. `exempt_use_units` is a separate customer or qualified-preparer study allocation, not a figure provided by utility bills. The tool checks the arithmetic and period coverage; it cannot create, certify, or validate an engineering study. It estimates the full meter's annual tax exemption only as a future amount after approval when the documented ratio is above 50%.

## Run the predominant-use fixture

From the repository root:

```sh
python ventures/utility-audits/scripts/utility_audit.py study \
  --input ventures/utility-audits/tests/fixtures/indiana_predominant_use_bills.csv \
  --output /tmp/utility-audit-st200-study.json
```

The synthetic fixture produces a 64% exempt-use screen and unsigned ST-200 application data. It contains no real customer details. For customer work, keep bills and study files on the customer's device.

The older `utility-audit-calculator` flow estimates the restaurant election. `utility-predominant-use` runs the CSV study screen and prepares local ST-200 application data. Both flows stop for human review. Neither signs, pays, contacts a utility, creates accounts, or submits a filing.

## Owner steps

1. Confirm Indiana as the launch state and provide case-specific records locally. Read the official [DOR utility exemption page](https://www.in.gov/dor/i-am-a/business-corp/utility-sales-tax-exemption/), [Bulletin #11](https://www.in.gov/dor/files/reference/sib11.pdf), [Bulletin #29](https://www.in.gov/dor/files/reference/sib29.pdf) when using the restaurant path, and [Bulletin #55](https://www.in.gov/dor/files/sib55.pdf) for a utility study. Select the applicable form from the [DOR forms index](https://www.in.gov/dor/tax-forms/business/sales-tax-forms/index.html).
2. Review and complete the official ST-200R or ST-200, attach source bills and any required study, then sign and submit it yourself. After DOR approval, send the issued certificate to the utility.

Billing remains disabled until the owner records approval of a fee model and its legal basis. No refund-share or first-year-savings fee is enabled.

See [DECISION.md](DECISION.md) for the launch-state comparison and source checks, and [PROOF.md](PROOF.md) for test and live-status evidence. Test data is synthetic.
