# Local postcard proof limits

The shared mail helper creates a two-sided **6 × 4 inch (landscape) local review proof** with the installed Chromium browser. It preserves the supplied HTML structure and inline styles. Both sides are measured before PDF output; if either side exceeds its page box, the result is `blocked_overflow` and no proof PDF is returned. Reflow or shorten the copy and render again.

The back includes the sender name and return address supplied to the mail helper. The PDF labels itself as a local review proof and says it is not print-ready. This preview does not establish postal eligibility or production readiness and does not include bleed, postal indicia, stock, or color-profile settings.

Co-op street postcards use a **separate 11.5 × 6.25 inch USPS EDDM Retail flat review proof** in `ventures/coop-postcards/workflow.py`. That artifact is not the shared 6 × 4 inch postcard preview. Neither proof is a production master or authorization to order or mail.

The local renderer uses Chromium with network name resolution blocked. Inline CSS, data images, and data fonts can render. Remote fonts, remote images, linked stylesheets, and other network resources are unavailable in this offline proof. If Chromium is missing or cannot inspect/render the page, proof generation fails with a blocking error.
