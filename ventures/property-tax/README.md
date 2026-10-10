# Property tax appeals

This venture prepares customer-reviewed Cook County property-tax evidence packets and local postcard proofs. The first county choice is **Cook County, Illinois**, because its Assessor Parcel Universe is already registered in the shared public-data feeds block. The owner must confirm the county and current representation rules before launch. Cook County packets are customer-filed only; Glacier does not represent customers or submit appeals.

Refresh the roll with **Refresh Cook County parcel records**. The public dataset can take several minutes to synchronize and may return a source alert; do not use an incomplete or stale snapshot. Case input belongs in `$GLACIER_HOME/ventures/property-tax/incoming/case.json`, with the current assessment notice and at least three recent sale documents. Each sale needs a source URL and customer confirmation that it was arm's-length. The reader records page citations and returns `uncertain — please check` whenever its independent engines disagree or a required value is missing. The packet reports a comparable value estimate for customer review; the customer chooses the requested value and decides whether the evidence supports an appeal.

Flow commands use `$GLACIER_REPO` and `$GLACIER_PYTHON` when set. Defaults are `$HOME/w/glacier-lean` and `$HOME/w/glacier-lean/.venv/bin/python`, matching the local Glacier install. In a development worktree the command locates this venture under `$HOME/w/workers` if the default repository does not contain it.

The public feed used here currently returns parcel PIN, tax year, property class, township and ZIP fields. It does not currently return owner mailing addresses or assessed values. A complete contact/notice record must therefore be supplied by the owner/customer; the script will not invent an address or say that a parcel is over-assessed from the parcel roll alone. Packet files are stored locally and customer uploads should be removed 30 days after the job closes unless the customer asks to keep them.

Postcard input belongs in `$GLACIER_HOME/ventures/property-tax/incoming/postcard.json`. The mail block creates an address-checked local HTML/PDF proof and honors its do-not-mail list. This flow never mails real recipients. A real mailing would need its own approval showing the exact recipient list, card, sender and spend. No Lob, Stripe or e-sign account is created here; Lob test mode is optional and live keys are not used.

The reader, rules, feeds, deadlines, customer, mail and filer block contracts were reviewed. This venture imports the feeds, reader, deadlines, customer and mail blocks and does not modify shared block code. The reader and rules directories currently provide `CHECK.md` files but no top-level `README.md`.

## Your steps

1. Confirm Cook County as the first county and resolve the county representation-rule check before launch.
2. Complete Texas property-tax consultant registration and any required association before adding Texas counties. Review current requirements at [Texas Department of Licensing and Regulation](https://www.tdlr.texas.gov/).
3. Review the first postcard design and mailing list, confirm the sender and budget, and approve any external send separately.

Each customer supplies their notice and sale evidence, confirms the requested value, then signs and submits any county filing themselves. If a signer is supplied in the case file, the customer block prepares a local signature request for the evidence packet; the request link must be shared by the owner through an approved channel. The flow does not send the packet or file with a county. Customer uploads are eligible for deletion 30 days after a case closes unless the customer asks to keep them. The retention flow lists the exact files first and requires a Glacier approval before removal; it only accepts paths under the venture's incoming folder.

Run the focused checks listed in [PROOF.md](PROOF.md). Test records are fixtures; real county feed availability and customer comparable documents are tracked separately in the proof record.
