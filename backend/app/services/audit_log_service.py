import logging

logger = logging.getLogger('atlas_auth.audit')


def log_event(message: str, *, event_type: str, employee_id: int | None = None, ip: str | None = None, app_key: str | None = None, result: str | None = None) -> None:
    logger.info(
        message,
        extra={
            'event_type': event_type,
            'employee_id': employee_id,
            'ip': ip,
            'app_key': app_key,
            'result': result,
        },
    )
