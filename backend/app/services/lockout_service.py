from collections import defaultdict, deque
from app.core.security import now_epoch
from app.core.settings import get_settings

settings = get_settings()

_ip_attempts: dict[str, deque[int]] = defaultdict(deque)
_account_attempts: dict[str, deque[int]] = defaultdict(deque)
_ip_lockout_until: dict[str, int] = {}
_account_lockout_until: dict[str, int] = {}


def _trim(deq: deque[int], cutoff: int) -> None:
    while deq and deq[0] < cutoff:
        deq.popleft()


def is_locked(ip: str, account: str) -> bool:
    now = now_epoch()
    return _ip_lockout_until.get(ip, 0) > now or _account_lockout_until.get(account, 0) > now


def register_failure(ip: str, account: str) -> None:
    now = now_epoch()
    cutoff = now - settings.auth_attempt_window_seconds

    _ip_attempts[ip].append(now)
    _account_attempts[account].append(now)

    _trim(_ip_attempts[ip], cutoff)
    _trim(_account_attempts[account], cutoff)

    if len(_ip_attempts[ip]) >= settings.auth_max_attempts_per_ip:
        _ip_lockout_until[ip] = now + settings.auth_lockout_seconds
    if len(_account_attempts[account]) >= settings.auth_max_attempts_per_account:
        _account_lockout_until[account] = now + settings.auth_lockout_seconds


def register_success(ip: str, account: str) -> None:
    _ip_attempts.pop(ip, None)
    _account_attempts.pop(account, None)
    _ip_lockout_until.pop(ip, None)
    _account_lockout_until.pop(account, None)
