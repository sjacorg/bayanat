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
