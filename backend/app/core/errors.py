"""API 오류 응답 형식.

모든 업무 오류는 {"detail": {"code": "...", "message": "..."}} 형태로 반환한다.
프론트엔드는 code로 분기하고 message를 그대로 보여 준다.
"""
from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def bad_request(code: str, message: str) -> ApiError:
    return ApiError(400, code, message)


def unauthorized(code: str = "unauthorized", message: str = "로그인이 필요합니다.") -> ApiError:
    return ApiError(401, code, message)


def forbidden(code: str = "forbidden", message: str = "권한이 없습니다.") -> ApiError:
    return ApiError(403, code, message)


def not_found(code: str = "not_found", message: str = "찾을 수 없습니다.") -> ApiError:
    return ApiError(404, code, message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)
