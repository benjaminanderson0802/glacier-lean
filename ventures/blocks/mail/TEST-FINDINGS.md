# Independent mail block findings

## Windows portability follow-up — 2026-10-11

The mail acceptance checks now read generated HTML as UTF-8. A new independent
check covers a UTF-8 suppression entry with non-ASCII address text. The product
helper currently reads suppression files with `Path.read_text()` and no encoding
in `engine.py`; on Windows this can decode UTF-8 using the active ANSI code page
and fail to match the customer's suppression entry. The check remains in place
and product code was not changed under this card.
