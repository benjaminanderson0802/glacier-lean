"""One-command, owner-driven Stripe test-mode checkout and refund check."""
import argparse
import os

from . import CustomerError, checkout_link, refund


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-id", default=None, help="Stripe test price ID (or STRIPE_TEST_PRICE_ID)")
    parser.add_argument("--payment-intent", help="Refund an existing test PaymentIntent")
    parser.add_argument("--approval-id", help="Owner approval identifier required for refunds")
    args = parser.parse_args()
    try:
        if args.payment_intent:
            approval = args.approval_id or input("Owner approval ID for this Stripe test refund: ").strip()
            result = refund(args.payment_intent, approval_id=approval)
            print(f"Test refund: {result.get('id')} ({result.get('status')})")
            return 0
        price_id = args.price_id or os.environ.get("STRIPE_TEST_PRICE_ID", "")
        if not price_id:
            parser.error("provide --price-id or STRIPE_TEST_PRICE_ID")
        url = checkout_link("live_check", plans={"live_check": {"price_id": price_id, "mode": "payment"}})
        print("Stripe TEST checkout link (owner action required):")
        print(url)
        print("Complete it with test card 4242 4242 4242 4242, then copy its test PaymentIntent ID.")
        payment_intent = input("Test PaymentIntent ID (blank to stop after checkout): ").strip()
        if not payment_intent:
            print("Stopped without a refund.")
            return 0
        approval = input("Type an owner approval ID to authorize this test refund: ").strip()
        if not approval:
            print("Stopped without a refund: no approval ID was supplied.")
            return 0
        result = refund(payment_intent, approval_id=approval)
        print(f"Test refund: {result.get('id')} ({result.get('status')})")
        return 0
    except CustomerError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
