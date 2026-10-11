# Owner rules: standing decisions for all venture and orchestration work

Benjamin (the owner) set these. Every agent, human and AI, reads this file before planning or building venture work. If a plan, card, research report or older document conflicts with this file, this file wins. Changes come only from the owner.

## What to prioritize
1. **Reliably consistent, mostly hands-off money comes first.** Prefer channels where customers find the product and pay without the owner selling: marketplace listings (Apify Store Actors, Chrome Web Store, Jobber / Shopify / ShipStation app marketplaces), government bids (SAM.gov / DIBBS), and recurring automated loops.
2. **Do not prioritize ventures that depend on cold email or cold outreach to survive.** Outreach-dependent ideas are lower priority. Where possible, convert them into a marketplace listing or an inbound channel instead.
3. **No phone calls, ever.** Never plan, script or schedule calls for the owner. Any outreach that does happen is written: email or the business's own website contact form. If a prospect won't close by email or text, move on to the next one.
4. **Pricing:** minimise profit, maximise accepted offers. Price so competitors make no sense; a base of past customers matters more than margin right now.
5. **Money:** ventures run only on money they earn. No spending, subscriptions or paid tools without the owner's explicit approval.
6. **Owner effort:** each venture should need at most one or two human-only steps. Prepare everything up to that step (pages filled, drafts written, links ready) and queue just that step.

## Venture decisions log
- 2026-10-11: added eBay (wholesale drop-ship, high-priced items in less-online niches with long shipping norms) and Depop (buy-first or seller-designed items). Dropped ventures: Pinterest and Vinted.
- 2026-10-11: Whop clipping only — owner approved fully automated posting to his linked YouTube channels and submission to Whop Content Rewards after one-time setup and explicit live configuration.

## Hard boundaries
- The owner (or the customer) personally does every legally binding or account action: signing, filing, paying, publishing, creating accounts, choosing prices, and sending messages. Agents prepare; they don't perform these.
- No invented testimonials, clients, statistics, guarantees or legal conclusions. Uncertain data stays "uncertain - please check".
- Free and open-source tools first.

## Orchestration rules (laptop workers)
- At most **5** Codex workers at once on the laptop (its Linux environment has about 9 GB of memory, and the C: drive is low on space). Heavy tasks (multi-backend tests, large benchmarks) run alone or in pairs.
- Delete a card's worktree as soon as its work is merged. Check memory and free disk before launching a wave.
- A worker must never write the checks that judge its own work.
