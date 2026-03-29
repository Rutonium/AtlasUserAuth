from fastapi import HTTPException, Request, status


def enforce_csrf(request: Request, expected: str, header_name: str) -> None:
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    supplied = request.headers.get(header_name)
    if (not supplied) or (supplied == expected) is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='CSRF validation failed')
