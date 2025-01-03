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
