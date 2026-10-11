# Buy-first Depop resale: three owner steps

This is a manual-listing workflow. Depop's [official Terms of Service](https://depophelp.zendesk.com/hc/en-gb/articles/360001773148-Terms-of-Service) describes compliant third-party crosslisting platforms in general, and its [business/API page](https://depophelp.zendesk.com/hc/en-gb/articles/4411154329233-Selling-as-a-charity-or-business) says the API is not public and that Depop works with API-connected crosslisting tools. Neither public source identifies an approved provider by name. Until Depop confirms a named provider in writing, **manual listing in Depop is the only verified route prepared here**. The local CSV is a review aid, not an import contract. No crosslisting provider is recommended or called.

## 1. Buy inspected used stock within the ceilings — about 30–60 minutes per batch

Open the category table in [RESEARCH.md](RESEARCH.md) → choose a specific piece or small lot from a seller you selected → inspect the item, condition, exact contents, return restrictions, and total cost before paying → compare the full landed acquisition cost per sellable piece against that category's ceiling → buy only if it is permitted, authentic where branded, and a condition you can describe honestly. Keep the dated receipt or lot record. Use the link to [Goodwill's store locator](https://www.goodwill.org/locate-a-thrift-store/) or its [official ShopGoodwill listing site](https://shopgoodwill.com/listing?catIds=&layout=grid) only if useful; this does not recommend or reserve any particular item.

**Value to use:** the owner-checked price ceiling in `RESEARCH.md`; substitute a current comparable sale price you personally verify before purchase. The listed sale prices are screening assumptions, not current quotes or guarantees. No catalogue drop-shipping, stock photos, or items not physically received.

## 2. Take original photos and enter item facts — about 10–15 minutes per item

After the item is physically in hand, photograph the exact item yourself (front, back, brand/size labels, and every flaw). Open the private inventory CSV using the columns in the existing input template at `ventures/depop-resale/tests/fixtures/inventory.csv`; keep the live copy outside this repository. Add one row with a unique `item_id`, only verified facts, actual used source, condition `Good` or `Satisfactory`, and `photo_origin` set to `owner_original` only after taking the photos. Save photos in your private photo folder. Do not claim unverified brand, era, material, authenticity, or condition.

From the repo root, create the local draft CSV:

```bash
~/w/glacier-lean/.venv/bin/python ventures/depop-resale/scripts/depop_prep.py listings \
  --input /path/to/your-inventory.csv \
  --photo-root /path/to/your-photos \
  --output /path/to/private/depop-listing-handoff.csv
```

Use your actual private paths in place of the three path values. The script does not upload files or contact Depop.

## 3. Approve each draft and list manually — about 5–10 minutes per item

Open the generated private CSV → compare title, description, tags, size, condition, price, category, and each photo path against the physical item and your own photos → correct input and regenerate if anything is wrong → sign in to [Depop](https://www.depop.com/) yourself → click `Sell now` → add your original photos → enter the checked title/description and choose the accurate category, shipping, brand, size, condition, and your final price → review and click `Post listing` only when it exactly matches the item. You can save a draft instead. Follow Depop's [official listing steps](https://depophelp.zendesk.com/hc/en-gb/articles/360032716413-How-to-list-an-item). This approval/publication remains yours; Glacier does not upload or publish.

Before physical-goods sales, check the [Georgia DOR dealer guidance](https://dor.georgia.gov/tax-registration). If it says registration applies and it is not already active, complete the free [Georgia Tax Center registration](https://dor.georgia.gov/how-register-sales-and-use-tax-account) yourself. Georgia [Form ST-5](https://dor.georgia.gov/document/form/st-5-sales-tax-certificate-exemption/download) is for qualifying tax-exempt wholesale purchases for resale; do not use it for personal-use clothing or assume a secondhand store purchase qualifies. Ask Georgia DOR or your tax professional if applicability is unclear. This is a conditional owner subtask within launch review, not a fourth Depop preparation step.

## After a sale

Packing, buying the shipping label, dispatch, and tracking are physical owner actions when an item sells. Use Depop's current [US shipping instructions](https://depophelp.zendesk.com/hc/en-gb/articles/16523051318033-How-to-ship-US) and the local checklist command in [README.md](README.md). These later fulfillment actions are outside the three-step preparation/onboarding count; they are not automated here.
