"""
Badges Service - Health Tracker
Core logic for badge evaluation, earning, and management
"""
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from ..database import DatabaseManager
from ..models import Badge

logger = logging.getLogger(__name__)


class BadgeEvaluator:
    """Evaluates whether badges should be earned based on criteria"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.badge_definitions = self._load_badge_definitions()
    
    def _load_badge_definitions(self) -> Dict[str, Any]:
        """Load badge definitions from JSON file"""
        try:
            badge_file = Path(__file__).parent.parent.parent / 'data' / 'badge_definitions.json'
            with open(badge_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load badge definitions: {e}")
            return {"badges": [], "tiers": {}}
    
    def evaluate_all_badges(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Evaluate all badges for potential earning.
        
        Returns:
            List of badge evaluation results with earning status
        """
        results = []
        
        for badge_def in self.badge_definitions.get('badges', []):
            try:
                result = self._evaluate_badge(badge_def, user_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating badge {badge_def.get('id')}: {e}")
                
        return results
    
    def _evaluate_badge(self, badge_def: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        """Evaluate a single badge based on its criteria"""
        badge_id = badge_def.get('id')
        criteria = badge_def.get('criteria', {})
        
        # Check if already earned
        existing_badge = self._get_earned_badge(badge_id)
        if existing_badge:
            return {
                'badge': badge_def,
                'earned': True,
                'earned_date': existing_badge.get('earned_at'),
                'already_earned': True
            }
        
        # Evaluate based on condition type
        condition = criteria.get('condition')
        earned = False
        earned_date = None
        
        if condition == 'single_day_threshold':
            earned, earned_date = self._check_single_day_threshold(criteria)
        elif condition == 'consecutive_days_threshold':
            earned, earned_date = self._check_consecutive_days_threshold(criteria)
        elif condition == 'weekly_total':
            earned, earned_date = self._check_weekly_total(criteria)
        elif condition == 'consistency_check':
            earned, earned_date = self._check_consistency(criteria)
        elif condition == 'progress_milestone':
            earned, earned_date = self._check_progress_milestone(criteria)
        elif condition == 'percentage_of_goal':
            earned, earned_date = self._check_percentage_of_goal(criteria)
        elif condition == 'goal_achieved':
            earned, earned_date = self._check_goal_achieved(criteria)
        elif condition == 'improvement':
            earned, earned_date = self._check_improvement(criteria)
        elif condition == 'zone_consistency':
            earned, earned_date = self._check_zone_consistency(criteria)
        elif condition == 'personal_best':
            earned, earned_date = self._check_personal_best(criteria)
        elif condition == 'entry_streak':
            earned, earned_date = self._check_entry_streak(criteria)
        elif condition == 'monthly_entries':
            earned, earned_date = self._check_monthly_entries(criteria)
        elif condition == 'all_goals_met':
            earned, earned_date = self._check_all_goals_met(criteria)
        elif condition == 'streak_length':
            earned, earned_date = self._check_streak_length(criteria)
        elif condition == 'time_based_entry':
            earned, earned_date = self._check_time_based_entry(criteria)
        elif condition == 'daily_entries':
            earned, earned_date = self._check_daily_entries(criteria)
        
        return {
            'badge': badge_def,
            'earned': earned,
            'earned_date': earned_date,
            'already_earned': False
        }
    
    def _get_earned_badge(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """Check if a badge has already been earned"""
        try:
            result = self.db.connection.execute(
                "SELECT * FROM badges WHERE name = ? AND earned_at IS NOT NULL",
                (badge_id,)
            ).fetchone()
            
            if result:
                return dict(result)
            return None
        except Exception as e:
            logger.error(f"Error checking earned badge: {e}")
            return None
    
    def _check_single_day_threshold(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if a single day threshold has been met"""
        metric = criteria.get('metric')
        threshold = criteria.get('threshold')
        
        try:
            # Check daily summaries for the metric
            result = self.db.connection.execute(
                f"""
                SELECT date FROM daily_summaries
                WHERE {metric}_total >= ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (threshold,)
            ).fetchone()
            
            if result:
                return True, datetime.fromisoformat(result['date']).date()
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking single day threshold: {e}")
            return False, None
    
    def _check_consecutive_days_threshold(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if consecutive days threshold has been met"""
        metric = criteria.get('metric')
        threshold = criteria.get('threshold')
        days = criteria.get('days', 7)
        
        try:
            # Get recent daily summaries
            results = self.db.connection.execute(
                f"""
                SELECT date, {metric}_total 
                FROM daily_summaries
                WHERE date >= date('now', '-{days * 2} days')
                ORDER BY date DESC
                """
            ).fetchall()
            
            if len(results) < days:
                return False, None
            
            # Check for consecutive days meeting threshold
            consecutive_count = 0
            last_date = None
            
            for row in results:
                current_date = datetime.fromisoformat(row['date']).date()
                value = row[f'{metric}_total']
                
                if value >= threshold:
                    if last_date is None or (last_date - current_date).days == 1:
                        consecutive_count += 1
                        if consecutive_count >= days:
                            return True, current_date
                    else:
                        consecutive_count = 1
                    last_date = current_date
                else:
                    consecutive_count = 0
                    last_date = None
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking consecutive days threshold: {e}")
            return False, None
    
    def _check_weekly_total(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if weekly total threshold has been met"""
        metric = criteria.get('metric')
        threshold = criteria.get('threshold')
        
        try:
            # Check weekly totals
            result = self.db.connection.execute(
                f"""
                SELECT 
                    date(date, 'weekday 0', '-6 days') as week_start,
                    SUM({metric}_total) as weekly_total
                FROM daily_summaries
                GROUP BY week_start
                HAVING weekly_total >= ?
                ORDER BY week_start DESC
                LIMIT 1
                """,
                (threshold,)
            ).fetchone()
            
            if result:
                return True, datetime.fromisoformat(result['week_start']).date()
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking weekly total: {e}")
            return False, None
    
    def _check_consistency(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if consistency criteria has been met"""
        metric = criteria.get('metric')
        variance_threshold = criteria.get('variance_threshold', 30)
        days = criteria.get('days', 14)
        
        try:
            # Get recent data
            results = self.db.connection.execute(
                f"""
                SELECT date, {metric}_total
                FROM daily_summaries
                WHERE date >= date('now', '-{days} days')
                ORDER BY date DESC
                LIMIT {days}
                """
            ).fetchall()
            
            if len(results) < days:
                return False, None
            
            # Calculate variance
            values = [row[f'{metric}_total'] for row in results]
            avg_value = sum(values) / len(values)
            max_variance = max(abs(v - avg_value) for v in values)
            
            if max_variance <= variance_threshold:
                return True, date.today()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking consistency: {e}")
            return False, None
    
    def _check_progress_milestone(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if progress milestone has been met"""
        metric = criteria.get('metric')
        threshold = criteria.get('threshold')
        
        try:
            # Get baseline and current weight
            baseline = self.db.connection.execute(
                f"""
                SELECT {metric}_value
                FROM daily_summaries
                WHERE {metric}_value IS NOT NULL
                ORDER BY date ASC
                LIMIT 1
                """
            ).fetchone()
            
            if not baseline:
                return False, None
            
            current = self.db.connection.execute(
                f"""
                SELECT date, {metric}_value
                FROM daily_summaries
                WHERE {metric}_value IS NOT NULL
                ORDER BY date DESC
                LIMIT 1
                """
            ).fetchone()
            
            if current:
                progress = current[f'{metric}_value'] - baseline[f'{metric}_value']
                if progress <= threshold:  # Negative threshold for weight loss
                    return True, datetime.fromisoformat(current['date']).date()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking progress milestone: {e}")
            return False, None
    
    def _check_percentage_of_goal(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if percentage of goal has been reached"""
        metric = criteria.get('metric')
        percentage = criteria.get('threshold')
        
        try:
            # Get active goal for metric
            goal = self.db.connection.execute(
                """
                SELECT * FROM goals
                WHERE goal_type = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (metric,)
            ).fetchone()
            
            if not goal:
                return False, None
            
            # Calculate progress percentage
            # This would need to integrate with progress tracker
            # Placeholder implementation
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking percentage of goal: {e}")
            return False, None
    
    def _check_personal_best(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if personal best has been achieved"""
        metric = criteria.get('metric')
        lookback_days = criteria.get('lookback_days', 90)
        
        try:
            # For HRV, check manual entries
            if metric == 'hrv':
                result = self.db.connection.execute(
                    """
                    SELECT date, hrv_value
                    FROM manual_entries
                    WHERE hrv_value IS NOT NULL
                    AND date >= date('now', '-' || ? || ' days')
                    ORDER BY hrv_value DESC
                    LIMIT 1
                    """,
                    (lookback_days,)
                ).fetchone()
                
                if result:
                    # Check if this is the highest ever
                    max_ever = self.db.connection.execute(
                        """
                        SELECT MAX(hrv_value) as max_hrv
                        FROM manual_entries
                        WHERE date < ?
                        """,
                        (result['date'],)
                    ).fetchone()
                    
                    if not max_ever['max_hrv'] or result['hrv_value'] > max_ever['max_hrv']:
                        return True, datetime.fromisoformat(result['date']).date()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking personal best: {e}")
            return False, None
    
    def _check_entry_streak(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if entry streak has been achieved"""
        metric = criteria.get('metric')
        days = criteria.get('days', 7)
        
        try:
            # For HRV, check manual entries
            if metric == 'hrv':
                results = self.db.connection.execute(
                    """
                    SELECT COUNT(DISTINCT date) as entry_count
                    FROM manual_entries
                    WHERE hrv_value IS NOT NULL
                    AND date >= date('now', '-' || ? || ' days')
                    """,
                    (days,)
                ).fetchone()
                
                if results and results['entry_count'] >= days:
                    return True, date.today()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking entry streak: {e}")
            return False, None
    
    # Additional check methods would follow similar patterns...
    
    def _check_streak_length(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if any streak has reached specified length"""
        days = criteria.get('days', 30)
        
        try:
            # Check all active streaks
            result = self.db.connection.execute(
                """
                SELECT MAX(current_count) as max_streak
                FROM streaks
                WHERE current_count >= ?
                """,
                (days,)
            ).fetchone()
            
            if result and result['max_streak']:
                return True, date.today()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking streak length: {e}")
            return False, None
    
    def _check_daily_entries(self, criteria: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """Check if daily entries have been made consistently"""
        days = criteria.get('days', 30)
        
        try:
            # Check for any data entry in the last N days
            result = self.db.connection.execute(
                """
                SELECT COUNT(DISTINCT date) as entry_days
                FROM (
                    SELECT date FROM daily_summaries
                    WHERE date >= date('now', '-' || ? || ' days')
                    UNION
                    SELECT date FROM manual_entries
                    WHERE date >= date('now', '-' || ? || ' days')
                )
                """,
                (days, days)
            ).fetchone()
            
            if result and result['entry_days'] >= days:
                return True, date.today()
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking daily entries: {e}")
            return False, None


class BadgesService:
    """Service for managing badges and achievements"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.evaluator = BadgeEvaluator()
    
    async def get_all_badges(self, earned_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all badges with their earned status.
        
        Args:
            earned_only: If True, only return earned badges
            
        Returns:
            List of badge information including earned status
        """
        try:
            # Get all badge definitions
            badge_defs = self.evaluator.badge_definitions.get('badges', [])
            
            # Get earned badges from database
            earned_badges = self.db.connection.execute(
                "SELECT * FROM badges WHERE earned_at IS NOT NULL"
            ).fetchall()
            
            earned_dict = {badge['name']: dict(badge) for badge in earned_badges}
            
            # Combine definitions with earned status
            all_badges = []
            for badge_def in badge_defs:
                badge_id = badge_def.get('id')
                earned_info = earned_dict.get(badge_id)
                
                badge_data = {
                    **badge_def,
                    'earned': earned_info is not None,
                    'earned_at': earned_info['earned_at'] if earned_info else None,
                    'tier_info': self.evaluator.badge_definitions['tiers'].get(badge_def.get('tier', 'bronze'))
                }
                
                if not earned_only or badge_data['earned']:
                    all_badges.append(badge_data)
            
            return all_badges
            
        except Exception as e:
            logger.error(f"Error getting all badges: {e}")
            return []
    
    async def evaluate_and_earn_badges(self) -> List[Dict[str, Any]]:
        """
        Evaluate all badges and automatically earn those that meet criteria.
        
        Returns:
            List of newly earned badges
        """
        try:
            newly_earned = []
            evaluation_results = self.evaluator.evaluate_all_badges()
            
            for result in evaluation_results:
                if result['earned'] and not result['already_earned']:
                    # Earn the badge
                    badge_def = result['badge']
                    success = self._create_badge_record(
                        badge_def['id'],
                        badge_def['name'],
                        badge_def['category'],
                        badge_def['description'],
                        result['earned_date']
                    )
                    
                    if success:
                        newly_earned.append({
                            **badge_def,
                            'earned_at': result['earned_date'].isoformat() if result['earned_date'] else None
                        })
            
            return newly_earned
            
        except Exception as e:
            logger.error(f"Error evaluating and earning badges: {e}")
            return []
    
    def _create_badge_record(self, badge_id: str, name: str, category: str, 
                           description: str, earned_date: Optional[date] = None) -> bool:
        """Create a badge record in the database"""
        try:
            if not earned_date:
                earned_date = date.today()
            
            self.db.connection.execute(
                """
                INSERT OR IGNORE INTO badges (name, metric, description, criteria, earned_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (badge_id, category, description, json.dumps({"id": badge_id}), 
                 earned_date.isoformat())
            )
            self.db.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating badge record: {e}")
            return False
    
    async def get_badge_progress(self) -> Dict[str, Any]:
        """
        Get progress information for all badges.
        
        Returns:
            Dictionary with badge progress statistics
        """
        try:
            all_badges = await self.get_all_badges()
            earned_badges = [b for b in all_badges if b['earned']]
            
            # Calculate points
            total_points = sum(
                b.get('tier_info', {}).get('points', 0) 
                for b in earned_badges
            )
            
            # Group by category
            by_category = {}
            for badge in all_badges:
                category = badge.get('category', 'other')
                if category not in by_category:
                    by_category[category] = {'total': 0, 'earned': 0}
                by_category[category]['total'] += 1
                if badge['earned']:
                    by_category[category]['earned'] += 1
            
            # Recent badges
            recent_badges = sorted(
                earned_badges,
                key=lambda x: x.get('earned_at', ''),
                reverse=True
            )[:5]
            
            return {
                'total_badges': len(all_badges),
                'earned_badges': len(earned_badges),
                'total_points': total_points,
                'completion_percentage': round(
                    (len(earned_badges) / len(all_badges) * 100) if all_badges else 0, 
                    1
                ),
                'by_category': by_category,
                'recent_badges': recent_badges
            }
            
        except Exception as e:
            logger.error(f"Error getting badge progress: {e}")
            return {
                'total_badges': 0,
                'earned_badges': 0,
                'total_points': 0,
                'completion_percentage': 0,
                'by_category': {},
                'recent_badges': []
            }
    
    async def get_next_badges(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get the next badges that are closest to being earned.
        
        Args:
            limit: Maximum number of badges to return
            
        Returns:
            List of badges with progress information
        """
        try:
            # This would require more sophisticated progress tracking
            # For now, return unearned badges
            all_badges = await self.get_all_badges()
            unearned = [b for b in all_badges if not b['earned']]
            
            # Prioritize by tier (bronze first)
            tier_order = ['bronze', 'silver', 'gold', 'platinum']
            unearned.sort(key=lambda x: tier_order.index(x.get('tier', 'bronze')))
            
            return unearned[:limit]
            
        except Exception as e:
            logger.error(f"Error getting next badges: {e}")
            return []