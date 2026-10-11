# U-FIX1 acceptance plan

- **Checkpoint:** PH12.1, ventures view and needs-you inbox UI follow-up.
- **Dependencies:** PH12 depends on PH5 and PH9; both are still in progress. This card may proceed, but this work will not mark PH12.1 done.
- **Property and metric:** P-USABLE; improves the readability and reachability of venture cards and shell controls. M-TTFA is the related product metric.
- **Existing tool:** CSS and the existing React UI already provide the required room and panels. A maintained package does not supply this app-specific lowercase chrome treatment or center-panel scrolling; this is a small UI adjustment, so no dependency is needed.
- **Acceptance test:** a Playwright screen check verifies lowercase chrome and the exact preservation of mixed-case manifest content, verifies the venture list scrolls to its last card without scrolling the page, and saves screenshots at 1280x800, 1440x900, and 1920x1080 in English and Spanish. Existing live-status implementation is retained from commit `6981bac`.
