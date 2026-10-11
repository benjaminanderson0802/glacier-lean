# Whop Content Rewards integration research

Research checked against Whop's documentation and legal pages on 2026-10-11.

## API coverage

Whop's public developer API documents the `/bounties` and `/bounty_submissions` resources. The submission creation endpoint is explicitly for a **workforce bounty**, requires a user OAuth credential with `bounty:submission:create`, and sends a `deliverable` directly to review. The list endpoint requires `bounty:basic:read` and returns bounty submissions visible to the user. Those descriptions do not document Content Rewards campaigns, their CPM fields, connected social accounts, or their submission/status workflow.

Whop's separate Content Rewards guide describes creator marketing campaigns (including content clipping) that pay per 1,000 views after approval. The published API reference has no documented Content Rewards campaign or submission resource. The bounty endpoints therefore cannot be treated as a supported Content Rewards integration merely because both products involve paid submissions. Do not send Content Rewards clip URLs to `/bounty_submissions` unless Whop documents or confirms that mapping.

## Campaign pay and review

The Whop Content Rewards guide describes view-based rewards configured as a rate per 1,000 views and a campaign budget. Sellers can configure a minimum payout threshold and a maximum payout per video. A submission is reviewed, and an approved post is paid based on its views. The account's campaign page remains authoritative for each campaign's actual rate, budget, requirements, limits, and accepted platforms; do not infer those values from another campaign.

The published Whop Content Rewards terms say approved Deliverables are paid at the Offer's Rate until the Max Payout is reached or the End Date occurs. They say Whop deducts a 10% Content Reward Fee from the Seller's Whop account on amounts paid to Participants, and describe Participant compensation as Whop Credits. Those terms do not promise a fixed review or transfer schedule: transfers may occur in increments and at times Whop sets. The historical Whop-hosted app may have separate accepted Clippers terms; verify the terms shown for the owner's account before relying on these payment details. No universal creator minimum or maximum payout is documented: the campaign's configured threshold and cap control.

## Terms and automation status

Whop's current Terms of Service prohibit accessing or monitoring the Service through automated means, including robots, spiders, or scrapers, and prohibit scraping without Whop's written consent. A persistent Playwright profile, headed or headless, still automates access to the Service. The owner's authorization for use of his own account does not itself constitute Whop's written consent.

The Whop Developer API terms authorize API use only as described in its technical documentation, require compliance with Whop policies, and say unauthorized access to a Seller Store or User Data is prohibited. No supported API path for Content Rewards was found in the public docs reviewed here.

**Status: blocked pending Whop's written authorization for automated Content Rewards access or an official documented Content Rewards API.** Do not log in, inspect the live app, read browser storage, scrape pages, or submit clips with Playwright until that authorization is available. Do not use workforce bounty endpoints as a substitute.

## Safety rules for any later approved implementation

- Store any approved OAuth token only under `CLIP_HOME/tokens/whop.json`; never commit tokens, cookies, browser profiles, personal data, or account snapshots.
- Keep the default mode dry-run. Require the owner's explicit `live=true` configuration before a submission write.
- Never join a paid campaign. Auto-join may only join a campaign with a verified zero cost when `auto_join=true`.
- Select only a connected YouTube account matching the post's channel handle. Skip a clip already submitted to the same campaign.
- Respect campaign requirements, disclosure, platform, and clip-length rules. Never submit clips from disallowed platforms or edit content for a no-edit campaign.
- Submit no more than one channel per clip and do not reuse the same or overlapping segment (>30%) across channels. Preserve the venture's upload caps and spacing rules.
- Do not buy or fabricate engagement. If a submission is flagged, pause that campaign for that channel and record the reason.
- Make at most one Whop action at a time, with several seconds between actions, only after Whop's written authorization or official API support is established.

## Sources

- [Whop documentation index (`llms.txt`)](https://docs.whop.com/llms.txt)
- [Whop Content Rewards guide](https://docs.whop.com/memberships-and-access/third-party-apps/content-rewards)
- [Create Bounty Submission API](https://docs.whop.com/api-reference/beta/bounty-submissions/create-bounty-submission)
- [List Bounty Submissions API](https://docs.whop.com/api-reference/beta/bounty-submissions/list-bounty-submissions)
- [List Bounties API](https://docs.whop.com/api-reference/beta/bounties/list-bounties)
- [Whop Terms of Service](https://whop.com/tos/)
- [Whop Developer API Terms](https://whop.com/tos-developer-api/)
- [Whop Content Rewards Terms](https://whop.com/content-rewards-terms-of-service/)
- [Content Rewards Creator Terms (scope of legacy Whop-hosted campaigns)](https://b4e0vdqv6zgqeqj4pfgm.apps.whop.com/terms)
