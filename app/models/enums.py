from enum import Enum


class PlanEnum(str, Enum):
    free = "free"
    pro = "pro"


class AccountTypeEnum(str, Enum):
    free = "free"
    uk_exporter = "uk_exporter"
    forwarder = "forwarder"
    eu_member = "eu_member"
    admin = "admin"


class StatusEnum(str, Enum):
    active = "active"
    pending = "pending"
    blocked = "blocked"


class AuthProviderEnum(str, Enum):
    google = "google"
    microsoft = "microsoft"


class InviteStatusEnum(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    cancelled = "cancelled"
