# B-MAIL-PROOF independent acceptance case

## Drift check

- Checkpoint: PH12.7, shared mail/acquisition engine; this card supplies evidence for the mail proof portion.
- Dependencies: PH5 and PH9 are not at exit. The owner-approved PH12 wave and assigned card authorize this scoped work to start; this case makes no phase-exit or checkpoint-done claim.
- Defining properties and metrics: P-USABLE and P-CONTROL; M-VERIFIED and M-AUDIT.
- Existing-tool check (I-01): the card directs reuse of the available pinned browser/PDF renderer. Existing mail acceptance covers render-only output, but not the completeness/layout cases below; this file specifies checks and adds no renderer.
- Acceptance test first (I-03): run the cases below against local generated proof artifacts; each must satisfy every listed criterion or return a visible blocking overflow result. No order or send is part of acceptance.

## Frozen acceptance criteria

1. **Long copy:** Render front and back copy that each exceed sixteen visual lines. Include unique markers at the beginning, middle, and end of each side. The proof must visibly contain every marker and all supplied copy. If it cannot fit, it must return an explicit blocking overflow result; it must not report a successful proof while omitting content.
2. **Styled copy:** Render HTML with headings, emphasized text, a list, a link, and unique text markers in each element. The review artifact must retain all words and make the content structure legible. If any content cannot be represented, block the proof explicitly rather than silently stripping or truncating it.
3. **Sender details:** Include a synthetic sender name and complete return address in the input. The resulting review proof must show those exact details, with no omission or substitution. The proof's presence does not authorize mailing.
4. **Page dimensions:** Inspect page boxes in inches. The shared standard postcard preview is 6 × 4 inches (the 4 × 6 format, landscape); the co-op EDDM review proof is a separate 11.5 × 6.25 inch artifact. Each must match its own dimensions and be identified as the corresponding preview; neither output may be mislabeled as the other format.
5. **Readiness wording:** The preview must be described as a local review/text proof, not “print-ready,” a production master, or ready to print. A successful render is not evidence of USPS or press readiness.

## Existing coverage gap

`ventures/blocks/mail/tests/test_mail_acceptance.py::test_no_key_is_render_only_and_produces_print_proof` checks that a short plain-text example creates files, but does not check complete copy, sender details in the PDF, page dimensions, or readiness wording. The co-op acceptance test checks claim readiness and render-only behavior, while its proof record separately documents the 11.5 × 6.25 inch EDDM artifact. These criteria add no edits to those checks.
