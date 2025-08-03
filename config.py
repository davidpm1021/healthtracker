"""
Configuration management for Health Tracker API.
Handles environment variables, secrets, and allowed IPs.
"""
import os
from typing import List, Optional
from pathlib import Path


class Config:
    """Configuration class for Health Tracker API."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables with defaults."""
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # Security Configuration
        self.shared_secret = os.getenv("SHARED_SECRET", "health-tracker-dev-secret-change-me")
        self.auth_header_name = os.getenv("AUTH_HEADER_NAME", "X-Health-Secret")
        
        # IP Filtering Configuration
        allowed_ips_str = os.getenv("ALLOWED_IPS", "127.0.0.1,::1,192.168.1.0/24,10.0.0.0/8,172.16.0.0/12")
        self.allowed_ips = [ip.strip() for ip in allowed_ips_str.split(",") if ip.strip()]
        
        # Database Configuration
        self.database_path = os.getenv("DATABASE_PATH", "healthtracker.db")
        
        # Data Ingestion Configuration
        self.max_payload_size = int(os.getenv("MAX_PAYLOAD_SIZE", "10485760"))  # 10MB default
        self.max_records_per_request = int(os.getenv("MAX_RECORDS_PER_REQUEST", "1000"))
        
        # Rate Limiting
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour
        
        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "health_tracker.log")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug_mode or self.shared_secret == "health-tracker-dev-secret-change-me"
    
    def is_ip_allowed(self, client_ip: str) -> bool:
        """Check if client IP is in allowed list."""
        import ipaddress
        
        try:
            client = ipaddress.ip_address(client_ip)
            
            for allowed in self.allowed_ips:
                try:
                    # Handle CIDR notation
                    if '/' in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client in network:
                            return True
                    else:
                        # Handle single IP
                        allowed_ip = ipaddress.ip_address(allowed)
                        if client == allowed_ip:
                            return True
                except (ipaddress.AddressValueError, ValueError):
                    # Skip invalid IP configurations
                    continue
            
            return False
            
        except (ipaddress.AddressValueError, ValueError):
            # Invalid client IP
            return False
    
    def validate_secret(self, provided_secret: str) -> bool:
        """Validate provided secret against configured secret."""
        return provided_secret == self.shared_secret
    
    def get_database_url(self) -> str:
        """Get database connection URL."""
        return f"sqlite:///{self.database_path}"
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary (excluding secrets)."""
        return {
            "api_host": self.api_host,
            "api_port": self.api_port,
            "debug_mode": self.debug_mode,
            "auth_header_name": self.auth_header_name,
            "allowed_ips": self.allowed_ips,
            "database_path": self.database_path,
            "max_payload_size": self.max_payload_size,
            "max_records_per_request": self.max_records_per_request,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window": self.rate_limit_window,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "is_development": self.is_development
        }


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = Config()