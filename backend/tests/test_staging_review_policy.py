from staging_review_policy import (
    ReviewerIdentity,
    can_view_dashboard,
    can_perform_preview_action,
)


def reviewer(**overrides):
    attrs = dict(
        subject="google-sub-staging",
        authenticated=True,
        account_active=True,
        actual_role="admin",
        allowed_views=frozenset({"admin", "partner", "influencer"}),
        reviewer_grant_active=True,
    )
    attrs.update(overrides)
    return ReviewerIdentity(**attrs)


def test_authorized_admin_sees_three_dashboards():
    identity = reviewer()
    for role in ("admin", "partner", "influencer"):
        assert can_view_dashboard(identity, role)
        assert can_perform_preview_action(identity, role, "dashboard.read")


def test_non_admin_and_unauthenticated_are_denied():
    for identity in (
        reviewer(actual_role="partner"),
        reviewer(actual_role="influencer"),
        reviewer(authenticated=False),
        reviewer(account_active=False),
        reviewer(subject=""),
        reviewer(reviewer_grant_active=False),
    ):
        assert not can_view_dashboard(identity, "admin")
        assert not can_view_dashboard(identity, "partner")


def test_explicit_scope_required():
    identity = reviewer(allowed_views=frozenset({"admin"}))
    assert can_view_dashboard(identity, "admin")
    assert not can_view_dashboard(identity, "partner")
    assert not can_view_dashboard(identity, "influencer")
    assert not can_view_dashboard(identity, "follower")


def test_switching_views_cannot_mutate_or_charge():
    identity = reviewer()
    for role in ("admin", "partner", "influencer"):
        for action in ("payment.create", "payout.transfer", "campaign.delete", "stripe.sync", "partner.write", "user.change_role"):
            assert not can_perform_preview_action(identity, role, action)


def test_unknown_roles_and_actions_are_denied():
    identity = reviewer()
    assert not can_view_dashboard(identity, "superadmin")
    assert not can_perform_preview_action(identity, "admin", "anything.unknown")
