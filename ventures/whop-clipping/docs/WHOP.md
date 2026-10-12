# Whop Content Rewards integration research

Research checked against Whop's documentation and legal pages on 2026-10-11.

## API coverage

Whop's public developer API documents the `/bounties` and `/bounty_submissions` resources. The submission creation endpoint is explicitly for a **workforce bounty**, requires a user OAuth credential with `bounty:submission:create`, and sends a `deliverable` directly to review. The list endpoint requires `bounty:basic:read` and returns bounty submissions visible to the user. Those descriptions do not document Content Rewards campaigns, their CPM fields, connected social accounts, or their submission/status workflow.

Whop's separate Content Rewards guide describes creator marketing campaigns (including content clipping) that pay per 1,000 views after approval. The published API reference has no documented Content Rewards campaign or submission resource. The bounty endpoints therefore cannot be treated as a supported Content Rewards integration merely because both products involve paid submissions. Do not send Content Rewards clip URLs to `/bounty_submissions` unless Whop documents or confirms that mapping.

## Campaign pay and review

The Whop Content Rewards guide describes view-based rewards configured as a rate per 1,000 views and a campaign budget. Sellers can configure a minimum payout threshold and a maximum payout per video. A submission is reviewed, and an approved post is paid based on its views. The account's campaign page remains authoritative for each campaign's actual rate, budget, requirements, limits, and accepted platforms; do not infer those values from another campaign.

The published Whop Content Rewards terms say approved Deliverables are paid at the Offer's Rate until the Max Payout is reached or the End Date occurs. They say Whop deducts a 10% Content Reward Fee from the Seller's Whop account on amounts paid to Participants, and describe Participant compensation as Whop Credits. Those terms do not promise a fixed review or transfer schedule: transfers may occur in increments and at times Whop sets. The historical Whop-hosted app may have separate accepted Clippers terms; verify the terms shown for the owner's account before relying on these payment details. No universal creator minimum or maximum payout is documented: the campaign's configured threshold and cap control.

## Terms and public-page access (checked 2026-10-11)

The public [robots.txt](https://contentrewards.com/robots.txt) currently says `Allow: /` and disallows `/api/`, `/confirmation`, `/dev/`, `/home`, `/onboarding`, `/partners`, `/refer`, and `/session-profile`. It has no `Crawl-delay` directive. [Discover](https://contentrewards.com/discover) redirects to the logged-out public page at `/c/discover`; its campaign cards link to public `/c/campaigns/<id>` detail pages. The current [Content Rewards Creator Terms](https://contentrewards.com/terms) define Discover as the page where Public Campaigns are listed and do not contain a ban on automated fetching or scraping. Sections 3 and 16 distinguish Content Rewards Inc.'s standalone Platform (account, Campaigns, Submissions, verification) from Whop (payment processing, withdrawals, and Whop account access). They state that the terms accepted for campaigns already joined in the earlier Whop-hosted experience continue to govern those campaigns; new campaigns use the current Creator Terms.

Whop's [Terms of Service](https://whop.com/tos/) separately prohibit automated access to or monitoring of information from the Whop Service, including by robots, spiders, or scrapers, and prohibit scraping Whop services without written consent. The terms define this restriction for the Whop Service; the current Content Rewards Terms identify the standalone Content Rewards platform as operated by Content Rewards Inc. Based on that separation and the public robots rules, this scout fetches only logged-out HTML hosted at `contentrewards.com`, follows same-host public-page redirects, and never requests `/api/` or a Whop page/endpoint. This is a narrow reading of the published terms, not an extension of permission to Whop pages or account data. Fetches are limited to one per URL per hour with a local HTML cache and an identifying User-Agent: `Glacier public campaign reader (contact: ben@andersoneducation.us)`. There is no robots crawl delay to apply. These public-page rules do not authorize account access, campaign joining, submissions, or use of Whop's Service; those actions remain manual. If the site terms or robots rules change, disable this scout and return to URL-only manual input until re-reviewed.

The Whop Developer API terms authorize API use only as described in the technical documentation, require compliance with Whop policies, and prohibit unauthorized access to Seller Stores or User Data. No supported API path for Content Rewards campaigns or submissions was found in the public docs reviewed here. Workforce bounty endpoints are not a substitute.

## Implemented operating decision (2026-10-11)

Producer's `PublicDiscoverScout` reads the logged-out public discover page and relevant public detail pages; it does not sign in or call APIs. It ranks only campaigns whose public URL the owner placed in `CLIP_HOME/joined_campaigns.txt`. The owner still joins campaigns manually, then pastes each URL once. High-value unjoined YouTube campaigns are stored locally and shown as “join these” suggestions in the Distributor status report; they are suggestions, not active campaigns. Producer parses available campaign requirements and source links from public detail HTML; fields not exposed on the logged-out page stay empty rather than being guessed. After YouTube upload, `ManualQueueSubmitter` records the Shorts URL, campaign, channel, caption, and required tags in the local ledger and regenerates `CLIP_HOME/submit-queue.html`. The owner submits from Content Rewards directly, checks the row, and downloads `submit-queue-done.json`; the next status read reconciles completed rows. Submissions stay manual unless written consent or an official documented Content Rewards API is available.

## Safety rules for any later approved implementation

- Never log in, read browser storage, use cookies, or access Whop pages/endpoints from this scout. No Whop OAuth token is used.
- Keep the default mode dry-run. Require the owner's explicit `live=true` configuration before a submission write.
- Never join a paid campaign. Auto-join may only join a campaign with a verified zero cost when `auto_join=true`.
- Select only a connected YouTube account matching the post's channel handle. Skip a clip already submitted to the same campaign.
- Respect campaign requirements, disclosure, platform, and clip-length rules. Never submit clips from disallowed platforms or edit content for a no-edit campaign.
- Submit no more than one channel per clip and do not reuse the same or any overlapping segment across channels. Preserve the venture's upload caps and spacing rules.
- Do not buy or fabricate engagement. If a submission is flagged, pause that campaign for that channel and record the reason.
- Make at most one Whop action at a time, with several seconds between actions, only after Whop's written authorization or official API support is established.

## Sources

- [Content Rewards robots.txt](https://contentrewards.com/robots.txt)
- [Content Rewards public Discover page](https://contentrewards.com/discover)
- [Content Rewards Creator Terms](https://contentrewards.com/terms)
- [Whop documentation index (`llms.txt`)](https://docs.whop.com/llms.txt)
- [Whop Content Rewards guide](https://docs.whop.com/memberships-and-access/third-party-apps/content-rewards)
- [Create Bounty Submission API](https://docs.whop.com/api-reference/beta/bounty-submissions/create-bounty-submission)
- [List Bounty Submissions API](https://docs.whop.com/api-reference/beta/bounty-submissions/list-bounty-submissions)
- [List Bounties API](https://docs.whop.com/api-reference/beta/bounties/list-bounties)
- [Whop Terms of Service](https://whop.com/tos/)
- [Whop Developer API Terms](https://whop.com/tos-developer-api/)
- [Whop Content Rewards Terms](https://whop.com/content-rewards-terms-of-service/)
- [Content Rewards Creator Terms (scope of legacy Whop-hosted campaigns)](https://b4e0vdqv6zgqeqj4pfgm.apps.whop.com/terms)
