"""Normalize Stripe SDK resources for existing dict-style payment logic.

The StripeClient v1 and Webhook SDK can return StripeObject instances, which
do not implement dict.get(). Keep .id/.url available for legacy checkout usage.
"""
from collections.abc import Mapping


class StripeRecord(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def stripe_payload(value):
    # Use a class-defined conversion method; MagicMock dynamically invents
    # .to_dict and must never be recursively converted.
    converter = getattr(type(value), "to_dict", None)
    if callable(converter) and not isinstance(value, Mapping):
        value = value.to_dict()
    if isinstance(value, Mapping):
        return StripeRecord({key: stripe_payload(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return [stripe_payload(item) for item in value]
    return value
