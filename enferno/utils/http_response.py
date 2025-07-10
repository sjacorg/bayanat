import json
from flask import Response


class HTTPResponse:
    """Utility class for HTTP responses."""

    OK = Response("OK", status=200)
    UNAUTHORIZED = Response("Unauthorized", status=401)
    FORBIDDEN = Response("Forbidden", status=403)
    NOT_FOUND = Response("Not Found", status=404)
    REQUEST_EXPIRED = Response("Request Expired", 410)
    BAD_REQUEST = Response("Bad Request", status=400)
    INTERNAL_SERVER_ERROR = Response("Internal Server Error", status=500)

    @staticmethod
    def json_ok(data: dict = None, message: str = None, status: int = 200):
        """Standard JSON response for success."""
        response_data = {}
        if data is not None:
            response_data["data"] = data
        if message is not None:
            response_data["message"] = message
        return Response(json.dumps(response_data), status=status, content_type="application/json")

    @staticmethod
    def json_error(message: str, status: int = 400, errors: any = None):
        """Standard JSON response for error."""
        response_data = {"message": message}
        if errors:
            response_data["errors"] = errors
        return Response(json.dumps(response_data), status=status, content_type="application/json")
