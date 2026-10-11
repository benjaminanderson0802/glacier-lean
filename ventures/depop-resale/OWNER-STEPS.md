# Owner step: buy, photograph, review, list, and fulfill used inventory

This is the venture's one human-only workflow. Use the research ceilings to choose and personally buy used stock, then take your own photos after each item is physically received. Never list catalog drop-shipped goods, and never use stock, supplier, or another seller's photos.

## Before listing each item

1. Open [RESEARCH.md](RESEARCH.md) and compare your intended purchase against the category ceiling. Open a local thrift store or used-lot listing you chose yourself, inspect the item or lot contents and condition, divide the lot's full landed cost (item price, buyer's premium, inbound shipping, tax, and handling) across the sellable pieces, and only then choose whether to buy. Keep the receipt or lot record. Do not buy a lot if you cannot verify the items are permitted, authentic where branded, and in a condition you can describe honestly.
2. After the item arrives, put it in your inventory and assign a unique `item_id`. Enter only facts you can verify in `tests/fixtures/inventory.csv`'s column format; keep your live inventory sheet outside the repository. Use `uncertain - please check` for any unknown fact.
3. Take your own clear photos of the exact item, including front, back, brand/size labels, and every flaw. Save them in a private local photo folder. Do not upload someone else's images.
4. From the repository root, make a local CSV handoff:

   ```bash
   ~/w/glacier-lean/.venv/bin/python ventures/depop-resale/scripts/depop_prep.py listings \
     --input /path/to/your-inventory.csv \
     --photo-root /path/to/your-photos \
     --output /path/to/private/depop-listing-handoff.csv
   ```

5. Open the CSV and compare every title, description, tag, size, condition, price, and photo path against the physical item and your own photos. Correct any mistake in your input and regenerate the file. A draft is a suggestion, not a verified claim.
6. If you use a crosslisting tool, first verify with Depop that the specific tool has API authorization. Depop's public materials do not name approved vendors. Do not pay for a tool without your approval. Import/map the CSV only if that vendor's documented import format matches; otherwise list manually in Depop. You choose the final price and manually approve and publish the listing.
7. To list manually on Depop.com, log in yourself, click **Sell now**, add your own item photos, enter the checked title and description, choose the correct category, shipping price, brand, and condition, set your final item price, then click **Post listing** only when the exact item and draft are correct. You can save a draft instead. These are Depop's current [listing steps](https://depophelp.zendesk.com/hc/en-gb/articles/360032716413-How-to-list-an-item).

## When an item sells

1. Confirm the sold order in Depop. Check the item ID, shipping address, selected shipping method, parcel size, and dispatch deadline in the live order.
2. From the repository root, prepare a local checklist without entering a buyer address:

   ```bash
   ~/w/glacier-lean/.venv/bin/python ventures/depop-resale/scripts/depop_prep.py shipping \
     --item-id JKT-001 --buyer-name "Private order" --sold-at 2026-10-11 \
     --carrier USPS --output /path/to/private/shipping-checklist.md
   ```

3. If you selected Depop Shipping, open the order's Depop-generated label and use that label only. On the web, click your profile picture → **Your selling hub** → **Sold** → the order. If you selected **Other**, arrange tracked shipping yourself, use the buyer address in the receipt, and enter the tracking carefully. Depop's [US shipping instructions](https://depophelp.zendesk.com/hc/en-gb/articles/16523051318033-How-to-ship-US) give the current screen paths.
4. Pack the item securely, dispatch it, and retain carrier acceptance/tracking proof. On the order, follow the current Depop screen to confirm tracking or mark as shipped. If it sold elsewhere, remove the Depop listing promptly; if there was a double sale, resolve the buyer issue yourself.

The tool stores no credentials and makes no network requests. Keep live inventory, photos, buyer names, addresses, labels, and tracking numbers out of this repository.
