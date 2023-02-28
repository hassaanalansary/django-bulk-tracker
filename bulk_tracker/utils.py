from __future__ import annotations


def get_old_values(obj, kwargs):
    return {key: getattr(obj, key) for key, value in kwargs.items()}
