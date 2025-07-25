import json
from typing import Any
from flask import Response


class HTTPResponse:
    """Utility class for HTTP responses."""

    @staticmethod
    def _json_response(
        data: dict | None = None, message: str | None = None, status: int = 200
    ) -> Response:
        """Standard JSON response for success."""
        response_data = {}
        if data is not None:
            response_data["data"] = data
        if message is not None:
            response_data["message"] = message
        return Response(json.dumps(response_data), status=status, content_type="application/json")

    @staticmethod
    def _json_error(message: str, status: int = 400, errors: Any = None) -> Response:
        """Standard JSON response for error."""
        response_data = {"message": message}
        if errors:
            response_data["errors"] = errors
        return Response(json.dumps(response_data), status=status, content_type="application/json")

    @staticmethod
    def success(
        data: dict | None = None, message: str | None = None, status: int = 200
    ) -> Response:
        """200 OK response"""
        return HTTPResponse._json_response(data, message, status)

    @staticmethod
    def created(data: dict | None = None, message: str | None = None) -> Response:
        """201 Created response"""
        return HTTPResponse._json_response(data, message, 201)

    @staticmethod
    def error(message: str, status: int = 400, errors: Any = None) -> Response:
        """Error response with custom status"""
        return HTTPResponse._json_error(message, status, errors)

    @staticmethod
    def not_found(message: str = "Not found") -> Response:
        """404 Not Found"""
        return HTTPResponse.error(message, 404)

    @staticmethod
    def forbidden(message: str = "Forbidden") -> Response:
        """403 Forbidden"""
        return HTTPResponse.error(message, 403)
