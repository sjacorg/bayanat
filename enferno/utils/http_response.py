import json
from flask import Response


class HTTPResponse:
    """Utility class for HTTP responses."""

    @staticmethod
    def _json_response(data: dict = None, message: str = None, status: int = 200):
        """Standard JSON response for success."""
        response_data = {}
        if data is not None:
            response_data["data"] = data
        if message is not None:
            response_data["message"] = message
        return Response(json.dumps(response_data), status=status, content_type="application/json")

    @staticmethod
    def _json_error(message: str, status: int = 400, errors: any = None):
        """Standard JSON response for error."""
        response_data = {"message": message}
        if errors:
            response_data["errors"] = errors
        return Response(json.dumps(response_data), status=status, content_type="application/json")

    @staticmethod
    def success(data=None, message=None, status=200):
        """200 OK response"""
        return HTTPResponse._json_response(data, message, status)

    @staticmethod
    def created(data=None, message=None):
        """201 Created response"""
        return HTTPResponse._json_response(data, message, 201)

    @staticmethod
    def error(message, status=400, errors=None):
        """Error response with custom status"""
        return HTTPResponse._json_error(message, status, errors)

    @staticmethod
    def not_found(message="Not found"):
        """404 Not Found"""
        return HTTPResponse.error(message, 404)

    @staticmethod
    def forbidden(message="Forbidden"):
        """403 Forbidden"""
        return HTTPResponse.error(message, 403)
