"""Read-only regression characterization of current PT beneficiary gating.

No live Stripe keys, database connections, payments or transfers are used.
The pending-influencer behavior is intentionally marked as current behavior,
not as acceptance of the future partial-settlement policy.
"""
import unittest
from unittest.mock import AsyncMock, patch

import pt_split


class PendingInfluencerCharacterization(unittest.IsolatedAsyncioTestCase):
    async def test_partner_ready_influencer_pending_currently_blocks_both(self):
        partner = {"id": "partner-test", "currency": "eur", "stripe_account_id": "acct_partner_test"}
        influencer = {"id": "influencer-test", "currency": "eur", "stripe_account_id": "acct_creator_test"}
        ready_partner = {"ok": True, "reason": "ready", "role": "partner", "account_id": "acct_partner_test"}
        pending_creator = {"ok": False, "reason": "connect_onboarding_or_transfers_pending",
                           "role": "influencer", "account_id": "acct_creator_test"}

        async def fake_find_one(collection, query, projection):
            return partner if query["id"] == "partner-test" else influencer

        with patch.object(pt_split.db.partners, "find_one", new=AsyncMock(return_value=partner)), \
             patch.object(pt_split.db.influencers, "find_one", new=AsyncMock(return_value=influencer)), \
             patch.object(pt_split, "_stripe_account",
                          side_effect=lambda account_id, expected_id, role:
                              ready_partner if role == "partner" else pending_creator):
            result = await pt_split.recipients_ready("partner-test", "influencer-test")

        self.assertTrue(result["partner"]["ok"])
        self.assertFalse(result["influencer"]["ok"])
        self.assertFalse(result["ok"])  # Existing defect: all-or-nothing gating.
        self.assertEqual(result["reason"], "connect_not_ready")

    async def test_missing_beneficiary_never_requests_stripe(self):
        with patch.object(pt_split.db.partners, "find_one", new=AsyncMock(return_value=None)), \
             patch.object(pt_split.db.influencers, "find_one", new=AsyncMock(return_value=None)), \
             patch.object(pt_split, "_stripe_account") as stripe_account:
            result = await pt_split.recipients_ready("missing-partner", "missing-creator")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "beneficiary_not_found")
        stripe_account.assert_not_called()


if __name__ == "__main__":
    unittest.main()
