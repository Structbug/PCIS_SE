import traceback

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class LegacyAPIError(APIException):
    status_code = 400
    default_code = "invalid_request"

    def __init__(self, status_code, message, errors=None):
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(detail=message)


def api_response(http_status, data, message="Success", payload_status_code=None):
    return Response(
        {
            "statusCode": payload_status_code or http_status,
            "data": data,
            "message": message,
            "success": http_status < 400,
        },
        status=http_status,
    )


def make_error_response(status_code, message, errors=None):
    return Response(
        {
            "statusCode": status_code,
            "data": None,
            "message": message,
            "success": False,
            "errors": errors or [],
        },
        status=status_code,
    )


def legacy_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        if isinstance(exc, Http404):
            return make_error_response(404, "Not found")
        if isinstance(exc, PermissionDenied):
            return make_error_response(403, "Permission denied")
        if isinstance(exc, ValidationError):
            return make_error_response(400, str(exc))
        traceback.print_exc()
        return make_error_response(500, "Internal server error")

    detail = response.data
    if isinstance(detail, dict) and isinstance(detail.get("detail"), str):
        message = detail["detail"]
    elif isinstance(detail, list) and detail:
        message = str(detail[0])
    else:
        message = "Validation failed"
    errors = getattr(exc, "errors", detail)
    response.data = {
        "statusCode": response.status_code,
        "data": None,
        "message": message,
        "success": False,
        "errors": errors,
    }
    return response
