from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Model


_T = TypeVar("_T", bound=models.Model)
User = get_user_model()


@dataclass
class ModifiedObject(Generic[_T]):
    obj: _T
    changed_values: dict[str, Any]


@dataclass
class TrackingInfo:
    user: Optional[User] = None
    comment: Optional[str] = None
    reason: Optional[Model] = None
    system: Optional[str] = None
