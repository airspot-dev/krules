"""
# Django KRules dashboard

A Django instance providing useful applications dealing with KRules

Currently it provides
- A processing events collector
- Aa events scheduler implementation
"""


def on_create(ctx, click, dest, env: dict, tag: str = None) -> bool:

    return True