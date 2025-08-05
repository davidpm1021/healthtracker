"""
Freeze Token Management - Health Tracker
Service for managing monthly freeze tokens that preserve streaks
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from calendar import monthrange

from ..database import DatabaseManager
from ..models.goals import Streak, FreezeToken

logger = logging.getLogger(__name__)


class FreezeTokenManager:
    """Manager for freeze token lifecycle and usage"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def issue_monthly_tokens(self, target_date: Optional[date] = None) -> Dict[str, int]:
        """
        Issue monthly freeze tokens for all active streaks.
        
        Args:
            target_date: Date to issue tokens for (defaults to today)
        
        Returns:
            Summary of tokens issued
        """
        if not target_date:
            target_date = date.today()
        
        summary = {
            "tokens_issued": 0,
            "streaks_processed": 0,
            "errors": 0,
            "already_issued": 0
        }
        
        try:
            # Get all active streaks
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.* FROM streaks s
                    JOIN goals g ON s.goal_id = g.id
                    WHERE g.status = 'active' AND s.is_active = 1
                """)
                
                streaks = []
                for row in cursor.fetchall():
                    streak = Streak(
                        id=row[0],
                        goal_id=row[1],
                        current_count=row[2],
                        best_count=row[3],
                        last_achieved_date=datetime.fromisoformat(row[4]).date() if row[4] else None,
                        last_updated=datetime.fromisoformat(row[5]) if row[5] else None,
                        is_active=bool(row[6]),
                        freeze_tokens_used=row[7]
                    )
                    streaks.append(streak)
            
            # Issue tokens for each streak
            for streak in streaks:
                try:
                    if self._should_issue_token_for_month(streak.id, target_date):
                        token = self._create_freeze_token(streak.id, target_date)
                        if token:
                            summary["tokens_issued"] += 1
                            logger.info(f"Issued freeze token {token.id} for streak {streak.id}")
                        else:
                            summary["errors"] += 1
                    else:
                        summary["already_issued"] += 1
                    
                    summary["streaks_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error issuing token for streak {streak.id}: {e}")
                    summary["errors"] += 1
            
            logger.info(f"Monthly token issuance complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in issue_monthly_tokens: {e}")
            summary["errors"] += 1
            return summary
    
    def use_token(self, token_id: int, used_date: Optional[date] = None, 
                  streak_id: Optional[int] = None) -> bool:
        """
        Use a freeze token to preserve a streak.
        
        Args:
            token_id: ID of the token to use
            used_date: Date the token is used (defaults to today)
            streak_id: Optional streak ID for validation
        
        Returns:
            True if token was successfully used
        """
        if not used_date:
            used_date = date.today()
        
        try:
            # Get the token
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM freeze_tokens WHERE id = ?", (token_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Freeze token {token_id} not found")
                    return False
                
                token = FreezeToken(
                    id=row[0],
                    streak_id=row[1],
                    issued_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
                    used_date=datetime.fromisoformat(row[3]).date() if row[3] else None,
                    expires_date=datetime.fromisoformat(row[4]).date() if row[4] else None,
                    is_used=bool(row[5])
                )
            
            # Validate token can be used
            if not self._validate_token_usage(token, used_date, streak_id):
                return False
            
            # Use the token
            success = self.db.use_freeze_token(token_id, used_date)
            
            if success:
                # Update streak freeze token usage count
                self._increment_streak_token_usage(token.streak_id)
                logger.info(f"Used freeze token {token_id} for streak {token.streak_id} on {used_date}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error using freeze token {token_id}: {e}")
            return False
    
    def get_available_tokens(self, streak_id: int) -> List[FreezeToken]:
        """Get all available (unused, unexpired) tokens for a streak"""
        try:
            return self.db.get_available_freeze_tokens(streak_id)
            
        except Exception as e:
            logger.error(f"Error getting available tokens for streak {streak_id}: {e}")
            return []
    
    def get_token_history(self, streak_id: int) -> List[FreezeToken]:
        """Get complete token history for a streak"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM freeze_tokens 
                    WHERE streak_id = ?
                    ORDER BY issued_date DESC
                """, (streak_id,))
                
                tokens = []
                for row in cursor.fetchall():
                    token = FreezeToken(
                        id=row[0],
                        streak_id=row[1],
                        issued_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
                        used_date=datetime.fromisoformat(row[3]).date() if row[3] else None,
                        expires_date=datetime.fromisoformat(row[4]).date() if row[4] else None,
                        is_used=bool(row[5])
                    )
                    tokens.append(token)
                
                return tokens
                
        except Exception as e:
            logger.error(f"Error getting token history for streak {streak_id}: {e}")
            return []
    
    def expire_old_tokens(self, as_of_date: Optional[date] = None) -> int:
        """
        Clean up expired tokens.
        
        Args:
            as_of_date: Date to check expiration against (defaults to today)
        
        Returns:
            Number of tokens expired
        """
        if not as_of_date:
            as_of_date = date.today()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get count of expired tokens
                cursor.execute("""
                    SELECT COUNT(*) FROM freeze_tokens 
                    WHERE expires_date < ? AND is_used = 0
                """, (as_of_date.isoformat(),))
                
                expired_count = cursor.fetchone()[0]
                
                if expired_count > 0:
                    # Mark them as expired (we don't delete, just mark)
                    # Note: The database schema doesn't have an explicit expired flag,
                    # but tokens are considered expired if expires_date < current_date
                    logger.info(f"Found {expired_count} expired freeze tokens as of {as_of_date}")
                
                return expired_count
                
        except Exception as e:
            logger.error(f"Error expiring old tokens: {e}")
            return 0
    
    def get_token_statistics(self) -> Dict[str, Any]:
        """Get system-wide freeze token statistics"""
        try:
            stats = {
                "total_tokens_issued": 0,
                "total_tokens_used": 0,
                "total_tokens_expired": 0,
                "total_tokens_available": 0,
                "usage_rate": 0.0,
                "tokens_by_month": {},
                "most_saved_streaks": []
            }
            
            today = date.today()
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total counts
                cursor.execute("SELECT COUNT(*) FROM freeze_tokens")
                stats["total_tokens_issued"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM freeze_tokens WHERE is_used = 1")
                stats["total_tokens_used"] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM freeze_tokens 
                    WHERE expires_date < ? AND is_used = 0
                """, (today.isoformat(),))
                stats["total_tokens_expired"] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM freeze_tokens 
                    WHERE expires_date >= ? AND is_used = 0
                """, (today.isoformat(),))
                stats["total_tokens_available"] = cursor.fetchone()[0]
                
                # Usage rate
                if stats["total_tokens_issued"] > 0:
                    stats["usage_rate"] = (stats["total_tokens_used"] / stats["total_tokens_issued"]) * 100
                
                # Tokens by month (last 6 months)
                cursor.execute("""
                    SELECT strftime('%Y-%m', issued_date) as month, COUNT(*) as count
                    FROM freeze_tokens 
                    WHERE issued_date >= date('now', '-6 months')
                    GROUP BY strftime('%Y-%m', issued_date)
                    ORDER BY month DESC
                """)
                
                for row in cursor.fetchall():
                    stats["tokens_by_month"][row[0]] = row[1]
                
                # Streaks with most token usage
                cursor.execute("""
                    SELECT s.id, s.goal_id, COUNT(ft.id) as token_count
                    FROM streaks s
                    LEFT JOIN freeze_tokens ft ON s.id = ft.streak_id AND ft.is_used = 1
                    GROUP BY s.id, s.goal_id
                    HAVING token_count > 0
                    ORDER BY token_count DESC
                    LIMIT 5
                """)
                
                for row in cursor.fetchall():
                    stats["most_saved_streaks"].append({
                        "streak_id": row[0],
                        "goal_id": row[1],
                        "tokens_used": row[2]
                    })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting token statistics: {e}")
            return {"error": "Unable to generate statistics"}
    
    def _should_issue_token_for_month(self, streak_id: int, target_date: date) -> bool:
        """Check if a token should be issued for the given month"""
        try:
            month_start = target_date.replace(day=1)
            month_end = self._get_month_end(target_date)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM freeze_tokens 
                    WHERE streak_id = ? AND issued_date >= ? AND issued_date <= ?
                """, (streak_id, month_start.isoformat(), month_end.isoformat()))
                
                existing_count = cursor.fetchone()[0]
                return existing_count == 0
                
        except Exception as e:
            logger.error(f"Error checking if token should be issued: {e}")
            return False
    
    def _create_freeze_token(self, streak_id: int, issue_date: date) -> Optional[FreezeToken]:
        """Create a new freeze token"""
        try:
            expires_date = self._get_month_end(issue_date)
            
            token = FreezeToken(
                streak_id=streak_id,
                issued_date=issue_date,
                expires_date=expires_date,
                is_used=False
            )
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO freeze_tokens (streak_id, issued_date, expires_date, is_used)
                    VALUES (?, ?, ?, ?)
                """, (
                    token.streak_id,
                    token.issued_date.isoformat(),
                    token.expires_date.isoformat(),
                    token.is_used
                ))
                
                token.id = cursor.lastrowid
            
            return token
            
        except Exception as e:
            logger.error(f"Error creating freeze token: {e}")
            return None
    
    def _validate_token_usage(self, token: FreezeToken, used_date: date, 
                             expected_streak_id: Optional[int] = None) -> bool:
        """Validate that a token can be used"""
        
        # Check if already used
        if token.is_used:
            logger.warning(f"Token {token.id} is already used")
            return False
        
        # Check if expired
        if token.is_expired:
            logger.warning(f"Token {token.id} is expired")
            return False
        
        # Check streak ID if provided
        if expected_streak_id and token.streak_id != expected_streak_id:
            logger.warning(f"Token {token.id} belongs to different streak")
            return False
        
        # Check if use date is reasonable (not in future, not too old)
        today = date.today()
        if used_date > today:
            logger.warning(f"Token {token.id} cannot be used for future date")
            return False
        
        # Allow using token up to 7 days after issue date
        if used_date < token.issued_date - timedelta(days=7):
            logger.warning(f"Token {token.id} cannot be used for date too far in past")
            return False
        
        return True
    
    def _increment_streak_token_usage(self, streak_id: int) -> None:
        """Increment the freeze token usage count for a streak"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE streaks 
                    SET freeze_tokens_used = freeze_tokens_used + 1,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (streak_id,))
                
        except Exception as e:
            logger.error(f"Error incrementing token usage for streak {streak_id}: {e}")
    
    def _get_month_end(self, date_obj: date) -> date:
        """Get last day of the month containing the given date"""
        last_day = monthrange(date_obj.year, date_obj.month)[1]
        return date_obj.replace(day=last_day)