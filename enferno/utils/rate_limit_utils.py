from flask import request
from flask_limiter.util import get_remote_address
import ipaddress


def is_private_ip(ip_str):
    """Check if an IP address is private."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or (
                isinstance(ip, ipaddress.IPv6Address)
                and (ip.ipv4_mapped or ip.sixtofour or ip.teredo)
            )
        )
    except ValueError:
        return True  # If we can't parse the IP, consider it private for safety


def get_first_public_ip(ip_list):
    """Get the first public IP from a comma-separated list."""
    if not ip_list:
        return None

    # Split and clean IPs
    ips = [ip.strip() for ip in ip_list.split(",")]

    # Return first public IP
    for ip in ips:
        if ip and not is_private_ip(ip):
            return ip
    return None


def get_real_ip():
    """Get the real IP address from various proxy headers, prioritizing public IPs."""
    # List of proxy headers to check in order of preference
    proxy_headers = [
        "X-Real-IP",
        "X-Forwarded-For",
        "CF-Connecting-IP",
        "True-Client-IP",
    ]

    # Check each header
    for header in proxy_headers:
        ip_list = request.headers.get(header)
        if ip_list:
            public_ip = get_first_public_ip(ip_list)
            if public_ip:
                return public_ip

    # Fall back to remote address if no valid public IP found in headers
    return get_remote_address()


def ratelimit_handler(e):
    return {
        "error": "Too Many Requests",
        "message": str(e.description),
    }, 429


# Login throttle
# Counters are kept in Redis with a 15-minute sliding TTL. We key by IP and
# by username independently so a single attacker cannot pivot across either.
LOGIN_FAIL_WINDOW_SEC = 900
LOGIN_FAIL_MAX_PER_USERNAME = 10
LOGIN_FAIL_MAX_PER_IP = 30


def _ip_key(ip: str) -> str:
    return f"loginfail:ip:{ip}"


def _user_key(username: str) -> str:
    return f"loginfail:user:{username.lower().strip()}"


def is_login_throttled(rds, username: str, ip: str) -> bool:
    """Return True if either the IP or username has exceeded its window quota."""
    if ip:
        ip_count = rds.get(_ip_key(ip))
        if ip_count and int(ip_count) >= LOGIN_FAIL_MAX_PER_IP:
            return True
    if username:
        user_count = rds.get(_user_key(username))
        if user_count and int(user_count) >= LOGIN_FAIL_MAX_PER_USERNAME:
            return True
    return False


def record_login_failure(rds, username: str, ip: str) -> None:
    """Increment failure counters for the given username and IP, refreshing TTL."""
    if ip:
        k = _ip_key(ip)
        rds.incr(k)
        rds.expire(k, LOGIN_FAIL_WINDOW_SEC)
    if username:
        k = _user_key(username)
        rds.incr(k)
        rds.expire(k, LOGIN_FAIL_WINDOW_SEC)


def clear_login_failures(rds, username: str) -> None:
    """Drop the per-username counter on a successful login."""
    if username:
        rds.delete(_user_key(username))
