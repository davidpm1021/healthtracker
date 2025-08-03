"""
Data models for Health Tracker database tables.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json


@dataclass
class RawPoint:
    """Model for raw time-series health data points."""
    metric: str
    start_time: str
    value: float
    unit: str
    source: str
    end_time: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'metric': self.metric,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'value': self.value,
            'unit': self.unit,
            'source': self.source
        }


@dataclass
class DailySummary:
    """Model for daily aggregated health metrics."""
    date: str
    metric: str
    value: float
    unit: str
    avg_7day: Optional[float] = None
    avg_30day: Optional[float] = None
    trend_slope: Optional[float] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'date': self.date,
            'metric': self.metric,
            'value': self.value,
            'unit': self.unit,
            'avg_7day': self.avg_7day,
            'avg_30day': self.avg_30day,
            'trend_slope': self.trend_slope,
            'updated_at': datetime.now().isoformat()
        }


@dataclass
class Goal:
    """Model for health metric goals."""
    metric: str
    period: str
    target_value: float
    unit: str
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'metric': self.metric,
            'period': self.period,
            'target_value': self.target_value,
            'unit': self.unit,
            'active': self.active,
            'updated_at': datetime.now().isoformat()
        }


@dataclass
class Badge:
    """Model for earned milestone badges."""
    name: str
    metric: str
    description: str
    criteria: dict
    earned_at: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'name': self.name,
            'metric': self.metric,
            'description': self.description,
            'criteria': json.dumps(self.criteria),
            'earned_at': self.earned_at
        }

    @classmethod
    def from_db_row(cls, row: dict) -> 'Badge':
        """Create Badge from database row."""
        return cls(
            id=row.get('id'),
            name=row['name'],
            metric=row['metric'],
            description=row['description'],
            criteria=json.loads(row['criteria']),
            earned_at=row.get('earned_at'),
            created_at=row.get('created_at')
        )


@dataclass
class ManualEntry:
    """Model for user-input data like HRV and other manual entries."""
    date: str
    metric: str
    value: Optional[float] = None
    unit: Optional[str] = None
    text_value: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'date': self.date,
            'metric': self.metric,
            'value': self.value,
            'unit': self.unit,
            'text_value': self.text_value,
            'notes': self.notes,
            'updated_at': datetime.now().isoformat()
        }


@dataclass
class SyncLog:
    """Model for data synchronization logging."""
    source: str
    sync_type: str
    start_time: str
    end_time: str
    status: str
    records_processed: int = 0
    records_added: int = 0
    records_updated: int = 0
    error_message: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            'source': self.source,
            'sync_type': self.sync_type,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'records_processed': self.records_processed,
            'records_added': self.records_added,
            'records_updated': self.records_updated,
            'status': self.status,
            'error_message': self.error_message
        }


class MetricType:
    """Constants for supported health metrics."""
    STEPS = "steps"
    SLEEP = "sleep"
    WEIGHT = "weight"
    HEART_RATE = "heart_rate"

    @classmethod
    def all(cls) -> list[str]:
        """Get all supported metric types."""
        return [cls.STEPS, cls.SLEEP, cls.WEIGHT, cls.HEART_RATE]


class ManualMetricType:
    """Constants for manual entry metrics."""
    HRV = "hrv"
    MOOD = "mood"
    ENERGY = "energy"
    NOTES = "notes"

    @classmethod
    def all(cls) -> list[str]:
        """Get all supported manual metric types."""
        return [cls.HRV, cls.MOOD, cls.ENERGY, cls.NOTES]


class SyncStatus:
    """Constants for sync log status values."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"