"""
Authentication and IP filtering middleware for Health Tracker API.
"""
import sys
from pathlib import Path
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

# Add parent directory to path for config import
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class SecurityError(HTTPException):
    """Custom security error for better error handling."""
    
    def __init__(self, detail: str, status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=detail)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request headers."""
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    
    # Default fallback
    return "unknown"


def verify_ip_access(request: Request) -> bool:
    """Verify if client IP is allowed to access the API."""
    config = get_config()
    client_ip = get_client_ip(request)
    
    # Log the access attempt
    logger.info(f"Access attempt from IP: {client_ip}")
    
    # Allow all IPs in development mode
    if config.is_development:
        logger.info(f"Development mode: allowing IP {client_ip}")
        return True
    
    # Check against allowed IPs
    is_allowed = config.is_ip_allowed(client_ip)
    
    if not is_allowed:
        logger.warning(f"IP {client_ip} not in allowed list: {config.allowed_ips}")
    
    return is_allowed


def verify_auth_header(request: Request) -> bool:
    """Verify authentication header contains correct secret."""
    config = get_config()
    
    # Get auth header
    auth_header = request.headers.get(config.auth_header_name)
    
    if not auth_header:
        logger.warning(f"Missing authentication header: {config.auth_header_name}")
        return False
    
    # Validate secret
    is_valid = config.validate_secret(auth_header)
    
    if not is_valid:
        logger.warning("Invalid authentication secret provided")
    
    return is_valid


async def verify_request_security(request: Request) -> None:
    """
    Comprehensive security verification for incoming requests.
    Raises HTTPException if security checks fail.
    """
    # Verify IP access
    if not verify_ip_access(request):
        client_ip = get_client_ip(request)
        raise SecurityError(
            detail=f"Access denied for IP address: {client_ip}",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # Verify authentication header
    if not verify_auth_header(request):
        raise SecurityError(
            detail="Invalid or missing authentication credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


def create_auth_dependency():
    """Create a FastAPI dependency for authentication."""
    async def auth_dependency(request: Request) -> dict:
        """FastAPI dependency that enforces authentication and IP filtering."""
        await verify_request_security(request)
        
        # Return security context
        return {
            "client_ip": get_client_ip(request),
            "authenticated": True,
            "timestamp": request.headers.get("Date", "unknown")
        }
    
    return auth_dependency


# Create the auth dependency instance
require_auth = create_auth_dependency()


class SecurityMiddleware:
    """Optional middleware class for global security checks."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add security headers to response
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Add security headers
                    security_headers = {
                        b"X-Content-Type-Options": b"nosniff",
                        b"X-Frame-Options": b"DENY",
                        b"X-XSS-Protection": b"1; mode=block",
                        b"Referrer-Policy": b"strict-origin-when-cross-origin"
                    }
                    
                    for key, value in security_headers.items():
                        headers[key] = value
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def get_security_info() -> dict:
    """Get current security configuration information."""
    config = get_config()
    
    return {
        "auth_header_name": config.auth_header_name,
        "allowed_ip_count": len(config.allowed_ips),
        "development_mode": config.is_development,
        "rate_limit": {
            "requests": config.rate_limit_requests,
            "window_seconds": config.rate_limit_window
        }
    }