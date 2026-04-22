"""
Jarvis AI Assistant — Web Check Tool
HTTP diagnostics, DNS resolution, and connectivity checks.
"""

import urllib.request
import urllib.error
import socket
import ssl
import time
from agents import function_tool


@function_tool(strict_mode=False)
def check_website(url: str) -> str:
    """
    Check if a website is up and responding. Returns status code, response time,
    and basic information about the site.

    Args:
        url: The URL to check (e.g., "https://example.com").

    Returns:
        A diagnostic report about the website's status.
    """
    # Ensure URL has a scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    report = [f"🌐 Website Check: {url}\n"]

    try:
        start_time = time.time()

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Jarvis-HealthCheck/1.0"}
        )

        ctx = ssl.create_default_context()
        response = urllib.request.urlopen(req, timeout=10, context=ctx)

        elapsed = time.time() - start_time

        report.append(f"  ✅ Status: {response.status} {response.reason}")
        report.append(f"  ⏱️  Response time: {elapsed:.2f}s")
        report.append(f"  📦 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        report.append(f"  📏 Content-Length: {response.headers.get('Content-Length', 'unknown')}")
        report.append(f"  🖥️  Server: {response.headers.get('Server', 'unknown')}")

        # Check for redirects
        if response.url != url:
            report.append(f"  ↪️  Redirected to: {response.url}")

    except urllib.error.HTTPError as e:
        report.append(f"  ❌ HTTP Error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        report.append(f"  ❌ Connection Error: {str(e.reason)}")
    except socket.timeout:
        report.append(f"  ⏰ Timeout: Site did not respond within 10 seconds")
    except Exception as e:
        report.append(f"  ❌ Error: {type(e).__name__}: {str(e)}")

    return "\n".join(report)


@function_tool(strict_mode=False)
def dns_lookup(hostname: str) -> str:
    """
    Perform a DNS lookup on a hostname to see its IP addresses.

    Args:
        hostname: The domain name to look up (e.g., "google.com").

    Returns:
        The IP addresses associated with the hostname.
    """
    # Strip protocol if present
    hostname = hostname.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        results = socket.getaddrinfo(hostname, None)
        ips = set()
        for result in results:
            ips.add(result[4][0])

        lines = [f"🔍 DNS Lookup: {hostname}\n"]
        for ip in sorted(ips):
            # Determine if IPv4 or IPv6
            ip_type = "IPv4" if "." in ip else "IPv6"
            lines.append(f"  → {ip} ({ip_type})")

        return "\n".join(lines)

    except socket.gaierror as e:
        return f"❌ DNS resolution failed for '{hostname}': {str(e)}"
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {str(e)}"


@function_tool(strict_mode=False)
def check_port(host: str, port: int) -> str:
    """
    Check if a specific port is open on a host.

    Args:
        host: The hostname or IP address to check.
        port: The port number to check (e.g., 80, 443, 3306).

    Returns:
        Whether the port is open or closed.
    """
    host = host.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return f"✅ Port {port} is OPEN on {host}"
        else:
            return f"❌ Port {port} is CLOSED on {host}"

    except socket.gaierror:
        return f"❌ Could not resolve hostname: {host}"
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {str(e)}"
