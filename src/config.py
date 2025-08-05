"""
Configuration management for Health Tracker.
"""
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    """Application configuration."""
    # Security
    shared_secret: str = os.getenv('HEALTH_SECRET', 'health-tracker-dev-secret-change-me')
    allowed_ips: List[str] = None  # Will be initialized in __post_init__
    
    # Database
    database_path: str = os.getenv('DATABASE_PATH', 'healthtracker.db')
    
    # API Settings
    max_payload_size: int = 10 * 1024 * 1024  # 10MB
    max_records_per_request: int = 1000
    
    # Development
    is_development: bool = os.getenv('ENV', 'development') == 'development'
    
    def __post_init__(self):
        """Process configuration after initialization."""
        # Initialize allowed_ips if not set
        if self.allowed_ips is None:
            self.allowed_ips = []
            
        # Parse allowed IPs from environment
        allowed_ips_env = os.getenv('ALLOWED_IPS', '')
        if allowed_ips_env:
            self.allowed_ips = [ip.strip() for ip in allowed_ips_env.split(',')]

# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config