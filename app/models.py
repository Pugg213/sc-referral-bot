"""
Модели данных для бота
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    referrer_id: Optional[int] = None
    registration_date: Optional[datetime] = None
    subscription_checked: bool = False
    subscription_date: Optional[datetime] = None
    banned: bool = False
    ban_reason: Optional[str] = None
    wallet_address: Optional[str] = None
    total_earnings: float = 0.0
    pending_balance: float = 0.0
    paid_balance: float = 0.0
    captcha_score: float = 0.0
    risk_score: float = 0.0
    quarantine_until: Optional[datetime] = None
    last_capsule_date: Optional[str] = None
    daily_capsules_opened: int = 0
    total_capsules_opened: int = 0
    total_referrals: int = 0
    validated_referrals: int = 0

@dataclass 
class CaptchaSession:
    id: int
    user_id: int
    captcha_value: str
    start_time: datetime
    solve_time: Optional[float] = None
    solved: bool = False

@dataclass
class ReferralValidation:
    id: int
    referrer_id: int
    referred_id: int
    validation_date: datetime
    validated: bool = False
    risk_flags: Optional[str] = None

@dataclass
class CapsuleOpening:
    id: int
    user_id: int
    reward_name: str
    reward_amount: float
    opening_date: datetime

@dataclass
class Payout:
    id: int
    user_id: int
    amount: float
    admin_id: int
    payout_date: datetime
    notes: Optional[str] = None
