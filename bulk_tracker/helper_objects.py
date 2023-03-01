from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from django.db import models
from django.db.models import Model


_T = TypeVar("_T", bound=models.Model)
User = TypeVar("User", bound=models.Model)


@dataclass
class ModifiedObject(Generic[_T]):
    instance: _T
    changed_values: dict[str, Any]


@dataclass
class TrackingInfo:
    user: User | None = None
    comment: str | None = None
    reason: Model | None = None
    system: str | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)
