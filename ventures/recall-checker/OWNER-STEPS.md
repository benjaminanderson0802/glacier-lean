# Owner steps — recall checker

**Current state:** the FSIS API canary passes and the first 50 source-linked pages are prepared. You can review the pages now. Public hosting and marketplace submission remain gated on the open independent fuzzy-match release review; borderline product matches stay uncertain.

## 1. Review the first 50 pages and choose a host

**Time:** about 15 minutes. **When:** ready now.

1. Open the prepared [first 50 local pages](evidence/first-50-pages/) from this worktree.
2. Review each of the first 50 pages: confirm its recall number and date, then open the linked official notice. Record any correction in the review report.
3. Choose the public host and enter its details in Glacier only if you want pages public. No hosting provider or account has been selected for you.

There are no host values to paste yet because the owner must choose the hosting provider and create/verify its account. The current flow does not publish pages. The packet was generated from current, alert-free CPSC, NHTSA, FDA and FSIS snapshots; see `evidence/first-50-pages-run.json`.

## 2. Publish the prepared extension and Actor listing

**Time:** about 20 minutes. **When:** after the independent fuzzy-match release review passes and after reviewing the first 50 pages.

1. Open [Apify Console → Actors](https://console.apify.com/actors) → the deployed **Product Recall Checker** Actor → **Settings**. Rename it to **Glacier Product Recall Checker**. Review the price and run limit; the prepared portfolio table suggests **$0.01 per `recall-check`**, but the owner chooses the final price. Publish the listing.
2. Open [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole) → the Recall Checker draft (or **New item**) → **Package**. Upload `ventures/recall-checker/store/recall-checker-extension-0.1.0.zip`.
3. Open **Store listing** and paste the title, summary, description, category, URLs and screenshots from [`store/STORE-LISTING.md`](store/STORE-LISTING.md). Upload `store/screenshots/01-local-check.png` and `store/screenshots/02-hosted-mode.png`; the 440 × 280 promo tile and 128 × 128 icon are also prepared locally.
4. Open **Privacy practices**. Paste the matching answers and Limited Use statement from `store/STORE-LISTING.md`; set the policy URL to `https://github.com/benjaminanderson0802/glacier-lean/blob/main/ventures/recall-checker/store/PRIVACY.md` after this card is merged. Review the permissions and in-popup token disclosure.
5. Open **Preview changes**, check the package/listing, then click **Submit for review**.

The extension listing uses the values in `store/STORE-LISTING.md`. It has no app price to choose. Stripe test prices are deferred until a paid-plan price is chosen; the free lookup and Web Store listing do not require a Stripe secret. Do not enable checkout or paste a secret key before then.

## Not owner steps

The FSIS API/official-source canary and the independent fuzzy-match review are build and verification work. They remain open in the venture evidence/claims and must be resolved by the technical lane before either owner action is useful. This venture does not depend on cold outreach.
