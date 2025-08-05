"""
UI data endpoints for Health Tracker dashboard.
Provides HTML fragments and data for the touch-friendly interface.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path
import logging

from ..database import DatabaseManager
from ..models import MetricType, ManualMetricType
from ..summaries import SummaryComputer
from ..trends import analyze_metric_trends
# from ..auth import require_auth  # Disabled for local development

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/today", response_class=HTMLResponse)
async def get_today_view():
    """
    Get simplified today view component.
    """
    try:
        # Load the simplified today component
        component_path = Path("static/components/today-simple.html")
        if component_path.exists():
            return component_path.read_text()
        else:
            # Fallback to basic layout
            return _generate_simple_today_view()
        
    except Exception as e:
        logger.error(f"Error loading today view component: {e}")
        return _generate_error_card("Failed to load today's view")


@router.get("/today/primary", response_class=HTMLResponse)
async def get_today_primary_metrics():
    """
    Get primary metrics for today (Steps, Sleep).
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        # Load the metric-card.html template
        card_template_path = Path("static/components/metric-card.html")
        if not card_template_path.exists():
            return _generate_error_card("Missing metric card template")
        
        card_template = card_template_path.read_text()
        
        cards_html = []
        primary_metrics = [MetricType.STEPS, MetricType.SLEEP]
        
        for metric in primary_metrics:
            summaries = db.get_daily_summaries_for_metric(metric, today, today)
            data = summaries[0] if summaries else None
            card_html = _generate_enhanced_metric_card(card_template, metric, data, is_manual=False)
            cards_html.append(card_html)
        
        return "\n".join(cards_html)
        
    except Exception as e:
        logger.error(f"Error generating primary metrics: {e}")
        return _generate_error_card("Failed to load primary metrics")


@router.get("/today/secondary", response_class=HTMLResponse)
async def get_today_secondary_metrics():
    """
    Get secondary metrics for today (Weight, Heart Rate).
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        # Load the metric-card.html template
        card_template_path = Path("static/components/metric-card.html")
        if not card_template_path.exists():
            return _generate_error_card("Missing metric card template")
        
        card_template = card_template_path.read_text()
        
        cards_html = []
        secondary_metrics = [MetricType.WEIGHT, MetricType.HEART_RATE]
        
        for metric in secondary_metrics:
            summaries = db.get_daily_summaries_for_metric(metric, today, today)
            data = summaries[0] if summaries else None
            card_html = _generate_enhanced_metric_card(card_template, metric, data, is_manual=False)
            cards_html.append(card_html)
        
        return "\n".join(cards_html)
        
    except Exception as e:
        logger.error(f"Error generating secondary metrics: {e}")
        return _generate_error_card("Failed to load secondary metrics")


@router.get("/today/stats")
async def get_today_stats():
    """
    Get today's quick stats for the dashboard header.
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        # Count metrics with data today
        total_metrics = 0
        for metric in MetricType.all():
            summaries = db.get_daily_summaries_for_metric(metric, today, today)
            if summaries and summaries[0]['value'] is not None:
                total_metrics += 1
        
        # Count manual entries today
        for metric in ManualMetricType.all():
            entry = db.get_manual_entry(today, metric)
            if entry:
                total_metrics += 1
        
        # Calculate health score (placeholder logic)
        health_score = min(100, (total_metrics / 7) * 100) if total_metrics > 0 else 0
        
        # Get streak days (placeholder - would need streak tracking)
        streak_days = 0
        
        # Get completed goals (placeholder - would need goals system)
        completed_goals = 0
        
        return {
            "totalMetrics": total_metrics,
            "completedGoals": completed_goals,
            "streakDays": streak_days,
            "healthScore": f"{health_score:.0f}"
        }
        
    except Exception as e:
        logger.error(f"Error generating today stats: {e}")
        return {
            "totalMetrics": 0,
            "completedGoals": 0,
            "streakDays": 0,
            "healthScore": "--"
        }


@router.get("/today/manual-status")
async def get_today_manual_status():
    """
    Get status of manual entries for today.
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        status = {}
        
        # Check HRV entry
        hrv_entry = db.get_manual_entry(today, ManualMetricType.HRV)
        if hrv_entry:
            time_str = datetime.fromisoformat(hrv_entry['updated_at'].replace('Z', '')).strftime('%I:%M %p')
            status['hrv'] = f"Entered at {time_str}"
        else:
            status['hrv'] = "Not entered today"
        
        # Check Mood entry
        mood_entry = db.get_manual_entry(today, ManualMetricType.MOOD)
        if mood_entry:
            score = mood_entry['value']
            status['mood'] = f"Rated {score}/10"
        else:
            status['mood'] = "Not entered today"
        
        # Check Energy entry
        energy_entry = db.get_manual_entry(today, ManualMetricType.ENERGY)
        if energy_entry:
            score = energy_entry['value']
            status['energy'] = f"Rated {score}/10"
        else:
            status['energy'] = "Not entered today"
        
        # Check Notes entry
        notes_entry = db.get_manual_entry(today, ManualMetricType.NOTES)
        if notes_entry and notes_entry['text_value']:
            word_count = len(notes_entry['text_value'].split())
            status['notes'] = f"{word_count} words written"
        else:
            status['notes'] = "No notes today"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting manual entry status: {e}")
        return {
            "hrv": "Error loading",
            "mood": "Error loading", 
            "energy": "Error loading",
            "notes": "Error loading"
        }


@router.get("/today/insights", response_class=HTMLResponse)
async def get_today_insights():
    """
    Get today's insights and recommendations.
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        insights = []
        
        # Steps insight
        steps_data = db.get_daily_summaries_for_metric(MetricType.STEPS, today, today)
        if steps_data and steps_data[0]['value']:
            steps = steps_data[0]['value']
            if steps >= 10000:
                insights.append("🎉 Great job reaching 10,000+ steps today!")
            elif steps >= 7500:
                insights.append(f"👟 You're at {steps:,.0f} steps - almost to 10k!")
            else:
                remaining = 10000 - steps
                insights.append(f"🚶 {remaining:,.0f} more steps to reach your 10k goal.")
        
        # Sleep insight
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sleep_data = db.get_daily_summaries_for_metric(MetricType.SLEEP, yesterday, yesterday)
        if sleep_data and sleep_data[0]['value']:
            sleep_hours = sleep_data[0]['value'] / 60
            if sleep_hours >= 8:
                insights.append(f"😴 Excellent sleep last night: {sleep_hours:.1f} hours!")
            elif sleep_hours >= 7:
                insights.append(f"💤 Good sleep last night: {sleep_hours:.1f} hours.")
            else:
                insights.append(f"⏰ Only {sleep_hours:.1f}h sleep - try for 7-8 hours tonight.")
        
        # Manual entry encouragement
        mood_entry = db.get_manual_entry(today, ManualMetricType.MOOD)
        if not mood_entry:
            insights.append("😊 Take a moment to log your mood - it helps track patterns!")
        
        # If no insights, provide generic encouragement
        if not insights:
            insights.append("📊 Start logging some health data to get personalized insights!")
        
        # Generate HTML
        insights_html = []
        for insight in insights[:3]:  # Limit to 3 insights
            insights_html.append(f'<div class="insight-item">{insight}</div>')
        
        return f"""
        <div class="insights-list">
            {''.join(insights_html)}
        </div>
        <style>
        .insights-list {{
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
        }}
        .insight-item {{
            padding: var(--spacing-md);
            background: rgba(255, 255, 255, 0.05);
            border-radius: var(--border-radius);
            font-size: 0.875rem;
            line-height: 1.4;
            color: var(--text-primary);
        }}
        </style>
        """
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        return '<div class="insight-item">🔄 Unable to generate insights right now.</div>'


async def get_today_view_legacy():
    """
    Legacy today view implementation (fallback).
    """
    try:
        db = DatabaseManager()
        today = date.today().isoformat()
        
        # Get today's summaries for automated metrics
        automated_metrics = {}
        for metric in MetricType.all():
            summaries = db.get_daily_summaries_for_metric(metric, today, today)
            if summaries:
                automated_metrics[metric] = summaries[0]
            else:
                automated_metrics[metric] = None
        
        # Get today's manual entries
        manual_metrics = {}
        for metric in ManualMetricType.all():
            entry = db.get_manual_entry(today, metric)
            manual_metrics[metric] = entry
        
        # Generate HTML cards
        cards_html = []
        
        # Automated metric cards
        for metric in MetricType.all():
            data = automated_metrics[metric]
            card_html = _generate_metric_card(metric, data, is_manual=False)
            cards_html.append(card_html)
        
        # Manual metric cards
        for metric in ManualMetricType.all():
            data = manual_metrics[metric]
            card_html = _generate_metric_card(metric, data, is_manual=True)
            cards_html.append(card_html)
        
        return "\n".join(cards_html)
        
    except Exception as e:
        logger.error(f"Error generating today view: {e}")
        return _generate_error_card("Failed to load today's data")


@router.get("/week", response_class=HTMLResponse)
async def get_week_view():
    """
    Get week view using the new component template.
    """
    try:
        # Load the week-view.html component template
        component_path = Path("static/components/week-view.html")
        if component_path.exists():
            return component_path.read_text()
        else:
            # Fallback to legacy implementation
            return await get_week_view_legacy()
        
    except Exception as e:
        logger.error(f"Error loading week view component: {e}")
        return _generate_error_card("Failed to load week view")


async def get_week_view_legacy():
    """
    Legacy week view implementation (fallback).
    """
    try:
        db = DatabaseManager()
        
        # Get week range
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        start_date = start_of_week.isoformat()
        end_date = end_of_week.isoformat()
        
        # Generate chart containers
        charts_html = []
        
        # Steps bar chart
        steps_data = db.get_daily_summaries_for_metric(MetricType.STEPS, start_date, end_date)
        charts_html.append(_generate_steps_chart(steps_data, "This Week"))
        
        # Weight line chart
        weight_data = db.get_daily_summaries_for_metric(MetricType.WEIGHT, start_date, end_date)
        charts_html.append(_generate_line_chart("Weight", weight_data, "kg", "This Week"))
        
        # Sleep bar chart
        sleep_data = db.get_daily_summaries_for_metric(MetricType.SLEEP, start_date, end_date)
        charts_html.append(_generate_sleep_chart(sleep_data, "This Week"))
        
        # HRV manual entries chart (if any)
        hrv_entries = db.get_manual_entries(ManualMetricType.HRV, start_date, end_date)
        if hrv_entries:
            charts_html.append(_generate_manual_entries_chart("HRV", hrv_entries, "ms", "This Week"))
        
        return "\n".join(charts_html)
        
    except Exception as e:
        logger.error(f"Error generating legacy week view: {e}")
        return _generate_error_card("Failed to load week data")


@router.get("/month", response_class=HTMLResponse)
async def get_month_view():
    """
    Get complete month view using the new component template.
    """
    try:
        # Load the month-view.html component template
        component_path = Path("static/components/month-view.html")
        if component_path.exists():
            return component_path.read_text()
        else:
            # Fallback to legacy month view generation
            return await get_month_view_legacy()
        
    except Exception as e:
        logger.error(f"Error loading month view component: {e}")
        return _generate_error_card("Failed to load month view")


async def get_month_view_legacy():
    """
    Legacy month view generation (fallback).
    """
    try:
        db = DatabaseManager()
        
        # Get month range
        today = date.today()
        start_of_month = today.replace(day=1)
        
        # Calculate end of month
        if today.month == 12:
            end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        start_date = start_of_month.isoformat()
        end_date = end_of_month.isoformat()
        
        # Generate chart containers
        charts_html = []
        
        # Monthly overview - all metrics in smaller charts
        for metric in MetricType.all():
            data = db.get_daily_summaries_for_metric(metric, start_date, end_date)
            if data:
                if metric == MetricType.STEPS:
                    charts_html.append(_generate_steps_chart(data, "This Month", compact=True))
                elif metric == MetricType.SLEEP:
                    charts_html.append(_generate_sleep_chart(data, "This Month", compact=True))
                else:
                    unit = "kg" if metric == MetricType.WEIGHT else "bpm"
                    charts_html.append(_generate_line_chart(metric.title(), data, unit, "This Month", compact=True))
        
        return "\n".join(charts_html)
        
    except Exception as e:
        logger.error(f"Error generating legacy month view: {e}")
        return _generate_error_card("Failed to load month data")


@router.get("/badges", response_class=HTMLResponse)
async def get_badges_view():
    """
    Get badges display component for dashboard.
    """
    try:
        # Load the badges-display.html component
        component_path = Path("static/components/badges-display.html")
        if component_path.exists():
            return component_path.read_text()
        else:
            return _generate_error_card("Badges display component not found")
    
    except Exception as e:
        logger.error(f"Error loading badges view: {e}")
        return _generate_error_card("Failed to load badges view")


@router.get("/goals", response_class=HTMLResponse)
async def get_goals_view():
    """
    Get goals and progress for the dashboard.
    """
    try:
        db = DatabaseManager()
        
        # Get active goals
        goals = db.get_active_goals()
        
        if not goals:
            return """
            <div class="goal-card">
                <div class="goal-header">
                    <h3>No Goals Set</h3>
                </div>
                <p>Set your first health goal to start tracking progress!</p>
                <button class="entry-button" style="margin-top: 1rem;">
                    <span class="entry-icon">🎯</span>
                    <span class="entry-label">Add Goal</span>
                </button>
            </div>
            """
        
        # Generate goal cards
        goal_cards = []
        for goal in goals:
            card_html = _generate_goal_card(goal, db)
            goal_cards.append(card_html)
        
        return "\n".join(goal_cards)
        
    except Exception as e:
        logger.error(f"Error generating goals view: {e}")
        return _generate_error_card("Failed to load goals")


@router.get("/manual-entry-form/{metric_type}", response_class=HTMLResponse)
async def get_manual_entry_form(
    metric_type: str):
    """
    Get manual entry form for a specific metric type.
    """
    try:
        today = date.today().isoformat()
        
        if metric_type == ManualMetricType.HRV:
            return f"""
            <form hx-post="/api/manual" hx-swap="none" hx-on::after-request="if(event.detail.successful) {{ $dispatch('show-success', {{message: 'HRV recorded successfully'}}); Alpine.raw($el.closest('[x-data]')).closeModal(); }}">
                <input type="hidden" name="date" value="{today}">
                <input type="hidden" name="metric" value="hrv">
                <input type="hidden" name="unit" value="ms">
                
                <div style="margin-bottom: 1rem;">
                    <label for="hrv-value" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">HRV Reading (ms)</label>
                    <input 
                        type="number" 
                        id="hrv-value"
                        name="value" 
                        min="0" 
                        max="1000" 
                        step="0.1"
                        required
                        style="width: 100%; padding: 0.75rem; border: 1px solid #dee2e6; border-radius: 8px; font-size: 1rem;"
                        placeholder="Enter HRV value"
                    >
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <label for="hrv-notes" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Notes (optional)</label>
                    <textarea 
                        id="hrv-notes"
                        name="notes" 
                        rows="3"
                        style="width: 100%; padding: 0.75rem; border: 1px solid #dee2e6; border-radius: 8px; font-size: 1rem; resize: vertical;"
                        placeholder="Any notes about your measurement..."
                    ></textarea>
                </div>
                
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button 
                        type="button" 
                        @click="closeModal()"
                        style="padding: 0.75rem 1.5rem; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Cancel
                    </button>
                    <button 
                        type="submit"
                        style="padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Save HRV
                    </button>
                </div>
            </form>
            """
        
        elif metric_type in [ManualMetricType.MOOD, ManualMetricType.ENERGY]:
            metric_title = metric_type.title()
            return f"""
            <form hx-post="/api/manual" hx-swap="none" hx-on::after-request="if(event.detail.successful) {{ $dispatch('show-success', {{message: '{metric_title} recorded successfully'}}); Alpine.raw($el.closest('[x-data]')).closeModal(); }}">
                <input type="hidden" name="date" value="{today}">
                <input type="hidden" name="metric" value="{metric_type}">
                <input type="hidden" name="unit" value="score">
                
                <div style="margin-bottom: 1rem;">
                    <label style="display: block; margin-bottom: 1rem; font-weight: 600;">Rate your {metric_title} (1-10)</label>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; margin-bottom: 1rem;">
                        {' '.join([f'''
                        <input type="radio" id="{metric_type}-{i}" name="value" value="{i}" required style="display: none;">
                        <label for="{metric_type}-{i}" style="display: flex; align-items: center; justify-content: center; padding: 0.75rem; border: 2px solid #dee2e6; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s;" onchange="this.parentElement.querySelectorAll('label').forEach(l => l.style.background = '#fff'); this.style.background = '#667eea'; this.style.color = 'white'; this.style.borderColor = '#667eea';">{i}</label>
                        ''' for i in range(1, 11)])}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.875rem; color: #6c757d;">
                        <span>{"Very Low" if metric_type == "mood" else "No Energy"}</span>
                        <span>{"Excellent" if metric_type == "mood" else "High Energy"}</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <label for="{metric_type}-notes" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Notes (optional)</label>
                    <textarea 
                        id="{metric_type}-notes"
                        name="notes" 
                        rows="3"
                        style="width: 100%; padding: 0.75rem; border: 1px solid #dee2e6; border-radius: 8px; font-size: 1rem; resize: vertical;"
                        placeholder="How are you feeling today..."
                    ></textarea>
                </div>
                
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button 
                        type="button" 
                        @click="closeModal()"
                        style="padding: 0.75rem 1.5rem; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Cancel
                    </button>
                    <button 
                        type="submit"
                        style="padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Save {metric_title}
                    </button>
                </div>
            </form>
            """
        
        elif metric_type == ManualMetricType.NOTES:
            return f"""
            <form hx-post="/api/manual" hx-swap="none" hx-on::after-request="if(event.detail.successful) {{ $dispatch('show-success', {{message: 'Notes saved successfully'}}); Alpine.raw($el.closest('[x-data]')).closeModal(); }}">
                <input type="hidden" name="date" value="{today}">
                <input type="hidden" name="metric" value="notes">
                
                <div style="margin-bottom: 1rem;">
                    <label for="notes-text" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Your Notes</label>
                    <textarea 
                        id="notes-text"
                        name="text_value" 
                        rows="6"
                        required
                        style="width: 100%; padding: 0.75rem; border: 1px solid #dee2e6; border-radius: 8px; font-size: 1rem; resize: vertical;"
                        placeholder="What's on your mind? How was your day? Any observations about your health..."
                    ></textarea>
                </div>
                
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button 
                        type="button" 
                        @click="closeModal()"
                        style="padding: 0.75rem 1.5rem; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Cancel
                    </button>
                    <button 
                        type="submit"
                        style="padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;"
                    >
                        Save Notes
                    </button>
                </div>
            </form>
            """
        
        else:
            raise HTTPException(status_code=400, detail="Invalid metric type")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating manual entry form for {metric_type}: {e}")
        return "<p>Error loading form. Please try again.</p>"


# Helper functions for generating HTML

def _generate_enhanced_metric_card(template: str, metric: str, data: Optional[Dict], is_manual: bool = False) -> str:
    """
    Generate HTML for a metric card using the enhanced template.
    """
    # Metric configuration
    config = {
        MetricType.STEPS: {"icon": "👟", "name": "Steps", "unit": "steps", "class": "steps"},
        MetricType.SLEEP: {"icon": "😴", "name": "Sleep", "unit": "hours", "class": "sleep"},
        MetricType.WEIGHT: {"icon": "⚖️", "name": "Weight", "unit": "kg", "class": "weight"},
        MetricType.HEART_RATE: {"icon": "❤️", "name": "Heart Rate", "unit": "bpm", "class": "heart_rate"},
        ManualMetricType.HRV: {"icon": "💓", "name": "HRV", "unit": "ms", "class": "hrv"},
        ManualMetricType.MOOD: {"icon": "😊", "name": "Mood", "unit": "/10", "class": "mood"},
        ManualMetricType.ENERGY: {"icon": "⚡", "name": "Energy", "unit": "/10", "class": "energy"},
        ManualMetricType.NOTES: {"icon": "📝", "name": "Notes", "unit": "", "class": "notes"}
    }
    
    metric_config = config.get(metric, {"icon": "📊", "name": metric.title(), "unit": "", "class": "default"})
    
    # Determine status
    if not data:
        status_class = "missing"
        last_updated = "No data"
        value = "--"
        unit = ""
        trend_indicator = ""
        comparison_text = ""
        progress_display = "none"
        progress_percent = "0"
        progress_text = ""
        action_buttons = ""
    else:
        # Data freshness status
        if data.get('updated_at'):
            updated_time = datetime.fromisoformat(data['updated_at'].replace('Z', ''))
            hours_ago = (datetime.now() - updated_time).total_seconds() / 3600
            if hours_ago <= 2:
                status_class = "fresh"
            elif hours_ago <= 24:
                status_class = "stale"
            else:
                status_class = "missing"
            last_updated = updated_time.strftime('%I:%M %p')
        else:
            status_class = "missing"
            last_updated = "Unknown"
        
        # Format value
        if metric == MetricType.SLEEP:
            value_raw = data.get('value', 0)
            hours = value_raw / 60 if value_raw else 0
            value = f"{hours:.1f}"
            unit = "hours"
        elif metric in [ManualMetricType.MOOD, ManualMetricType.ENERGY]:
            value = f"{data.get('value', 0):.0f}"
            unit = "/10"
        elif metric == ManualMetricType.NOTES:
            text_value = data.get('text_value', '')
            if text_value:
                word_count = len(text_value.split())
                value = f"{word_count}"
                unit = "words"
            else:
                value = "--"
                unit = ""
        else:
            value_raw = data.get('value', 0)
            if value_raw and value_raw >= 1000:
                value = f"{value_raw:,.0f}"
            elif value_raw:
                value = f"{value_raw:.1f}"
            else:
                value = "--"
            unit = metric_config["unit"]
        
        # Trend indicator
        if not is_manual and data.get('trend_slope') is not None:
            slope = data['trend_slope']
            if abs(slope) < 0.01:
                trend_indicator = '<div class="metric-trend trend-flat"><span class="trend-arrow">→</span> Stable</div>'
            elif slope > 0:
                trend_indicator = '<div class="metric-trend trend-up"><span class="trend-arrow">↗</span> Improving</div>'
            else:
                trend_indicator = '<div class="metric-trend trend-down"><span class="trend-arrow">↘</span> Declining</div>'
        else:
            trend_indicator = f'<div class="metric-trend">Updated {last_updated}</div>'
        
        # Comparison text
        if data.get('avg_7_day') and not is_manual:
            avg_7 = data['avg_7_day']
            current_val = data.get('value', 0)
            if current_val > avg_7 * 1.1:
                comparison_text = f'<div class="metric-comparison">+{((current_val / avg_7 - 1) * 100):.0f}% vs 7-day avg</div>'
            elif current_val < avg_7 * 0.9:
                comparison_text = f'<div class="metric-comparison">{((current_val / avg_7 - 1) * 100):.0f}% vs 7-day avg</div>'
            else:
                comparison_text = '<div class="metric-comparison">Near 7-day average</div>'
        else:
            comparison_text = ""
        
        # Progress bar (for goals)
        progress_display = "none"  # Would implement with goals system
        progress_percent = "0"
        progress_text = ""
        
        # Action buttons
        if is_manual:
            action_buttons = f'<div class="metric-actions"><button class="metric-action-btn primary" onclick="showManualEntry(\'{metric}\')">Update</button></div>'
        else:
            action_buttons = ""
    
    # Replace template variables
    result = template.replace("{metric_type}", metric)
    result = result.replace("{metric_class}", metric_config["class"])
    result = result.replace("{metric_icon}", metric_config["icon"])
    result = result.replace("{status_class}", status_class)
    result = result.replace("{metric_name}", metric_config["name"])
    result = result.replace("{last_updated}", last_updated)
    result = result.replace("{value}", value)
    result = result.replace("{unit}", unit)
    result = result.replace("{trend_indicator}", trend_indicator)
    result = result.replace("{comparison_text}", comparison_text) 
    result = result.replace("{action_buttons}", action_buttons)
    result = result.replace("{progress_display}", progress_display)
    result = result.replace("{progress_percent}", progress_percent)
    result = result.replace("{progress_text}", progress_text)
    
    return result


def _generate_metric_card(metric: str, data: Optional[Dict], is_manual: bool = False) -> str:
    """Generate HTML for a metric card."""
    
    # Metric configuration
    config = {
        MetricType.STEPS: {"icon": "👟", "name": "Steps", "unit": "steps"},
        MetricType.SLEEP: {"icon": "😴", "name": "Sleep", "unit": "hours"},
        MetricType.WEIGHT: {"icon": "⚖️", "name": "Weight", "unit": "kg"},
        MetricType.HEART_RATE: {"icon": "❤️", "name": "Heart Rate", "unit": "bpm"},
        ManualMetricType.HRV: {"icon": "💓", "name": "HRV", "unit": "ms"},
        ManualMetricType.MOOD: {"icon": "😊", "name": "Mood", "unit": "/10"},
        ManualMetricType.ENERGY: {"icon": "⚡", "name": "Energy", "unit": "/10"},
        ManualMetricType.NOTES: {"icon": "📝", "name": "Notes", "unit": ""}
    }
    
    metric_config = config.get(metric, {"icon": "📊", "name": metric.title(), "unit": ""})
    
    if not data:
        # No data card
        return f"""
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-icon">{metric_config["icon"]}</div>
                <div class="metric-name">{metric_config["name"]}</div>
            </div>
            <div class="metric-value">--</div>
            <div class="metric-trend">No data today</div>
        </div>
        """
    
    # Format value based on metric type
    if metric == MetricType.SLEEP:
        # Convert minutes to hours
        value = data.get('value', 0)
        hours = value / 60 if value else 0
        formatted_value = f"{hours:.1f}"
        unit = "hours"
    elif metric in [ManualMetricType.MOOD, ManualMetricType.ENERGY]:
        formatted_value = f"{data.get('value', 0):.0f}"
        unit = "/10"
    elif metric == ManualMetricType.NOTES:
        text_value = data.get('text_value', '')
        formatted_value = f"{len(text_value.split())} words" if text_value else "Empty"
        unit = ""
    else:
        value = data.get('value', 0)
        formatted_value = f"{value:,.0f}" if value and value >= 1000 else f"{value:.1f}" if value else "--"
        unit = metric_config["unit"]
    
    # Get trend information for automated metrics
    trend_html = ""
    if not is_manual and data.get('trend_slope') is not None:
        slope = data['trend_slope']
        if abs(slope) < 0.01:
            trend_html = '<div class="metric-trend trend-flat">→ Stable</div>'
        elif slope > 0:
            trend_html = '<div class="metric-trend trend-up">↗ Improving</div>'
        else:
            trend_html = '<div class="metric-trend trend-down">↘ Declining</div>'
    elif is_manual:
        updated_at = data.get('updated_at', '')
        if updated_at:
            time_str = datetime.fromisoformat(updated_at.replace('Z', '')).strftime('%I:%M %p')
            trend_html = f'<div class="metric-trend">Updated {time_str}</div>'
        else:
            trend_html = '<div class="metric-trend">No data</div>'
    
    return f"""
    <div class="metric-card">
        <div class="metric-header">
            <div class="metric-icon">{metric_config["icon"]}</div>
            <div class="metric-name">{metric_config["name"]}</div>
        </div>
        <div class="metric-value">
            {formatted_value}
            <span class="metric-unit">{unit}</span>
        </div>
        {trend_html}
    </div>
    """


def _generate_steps_chart(data: List[Dict], period: str, compact: bool = False) -> str:
    """Generate HTML for steps bar chart."""
    if not data:
        return _generate_empty_chart("Steps", period)
    
    # Prepare chart data
    labels = [datetime.fromisoformat(d['date']).strftime('%a') for d in data]
    values = [d['value'] for d in data]
    
    chart_id = f"steps-chart-{period.lower().replace(' ', '-')}"
    height = "200px" if compact else "300px"
    
    return f"""
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">Steps</div>
            <div class="chart-period">{period}</div>
        </div>
        <div style="height: {height};">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: 'Steps',
                            data: {values},
                            backgroundColor: '#667eea',
                            borderColor: '#5758bb',
                            borderWidth: 1,
                            borderRadius: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: function(value) {{
                                        return value.toLocaleString();
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }});
        </script>
    </div>
    """


def _generate_line_chart(title: str, data: List[Dict], unit: str, period: str, compact: bool = False) -> str:
    """Generate HTML for line chart."""
    if not data:
        return _generate_empty_chart(title, period)
    
    labels = [datetime.fromisoformat(d['date']).strftime('%m/%d') for d in data]
    values = [d['value'] for d in data]
    
    chart_id = f"{title.lower()}-chart-{period.lower().replace(' ', '-')}"
    height = "200px" if compact else "300px"
    
    return f"""
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">{title}</div>
            <div class="chart-period">{period}</div>
        </div>
        <div style="height: {height};">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: '{title}',
                            data: {values},
                            borderColor: '#42b883',
                            backgroundColor: 'rgba(66, 184, 131, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: false
                            }}
                        }}
                    }}
                }});
            }});
        </script>
    </div>
    """


def _generate_sleep_chart(data: List[Dict], period: str, compact: bool = False) -> str:
    """Generate HTML for sleep bar chart (converted to hours)."""
    if not data:
        return _generate_empty_chart("Sleep", period)
    
    labels = [datetime.fromisoformat(d['date']).strftime('%a') for d in data]
    values = [d['value'] / 60 for d in data]  # Convert minutes to hours
    
    chart_id = f"sleep-chart-{period.lower().replace(' ', '-')}"
    height = "200px" if compact else "300px"
    
    return f"""
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">Sleep</div>
            <div class="chart-period">{period}</div>
        </div>
        <div style="height: {height};">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: 'Sleep Hours',
                            data: {values},
                            backgroundColor: '#764ba2',
                            borderColor: '#5d3a7b',
                            borderWidth: 1,
                            borderRadius: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 12,
                                ticks: {{
                                    callback: function(value) {{
                                        return value + 'h';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }});
        </script>
    </div>
    """


def _generate_manual_entries_chart(title: str, data: List[Dict], unit: str, period: str) -> str:
    """Generate HTML for manual entries scatter plot."""
    if not data:
        return _generate_empty_chart(title, period)
    
    labels = [datetime.fromisoformat(d['date']).strftime('%m/%d') for d in data]
    values = [d['value'] for d in data]
    
    chart_id = f"{title.lower()}-manual-chart-{period.lower().replace(' ', '-')}"
    
    return f"""
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">{title} (Manual)</div>
            <div class="chart-period">{period}</div>
        </div>
        <div style="height: 300px;">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    type: 'scatter',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: '{title}',
                            data: {[{'x': i, 'y': v} for i, v in enumerate(values)]},
                            backgroundColor: '#e74c3c',
                            borderColor: '#c0392b',
                            borderWidth: 2,
                            pointRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            x: {{
                                type: 'linear',
                                position: 'bottom',
                                ticks: {{
                                    callback: function(value) {{
                                        return {labels}[Math.floor(value)] || '';
                                    }}
                                }}
                            }},
                            y: {{
                                beginAtZero: false
                            }}
                        }}
                    }}
                }});
            }});
        </script>
    </div>
    """


def _generate_goal_card(goal: Dict, db: DatabaseManager) -> str:
    """Generate HTML for a goal card."""
    # This is a placeholder - goals functionality would be implemented later
    return f"""
    <div class="goal-card">
        <div class="goal-header">
            <div class="goal-name">{goal.get('metric', 'Unknown').title()} Goal</div>
            <div class="goal-status in-progress">In Progress</div>
        </div>
        <div class="goal-progress">
            <div class="goal-progress-bar" style="width: 65%;"></div>
        </div>
        <p>Target: {goal.get('target_value', 0)} {goal.get('unit', '')} per {goal.get('period', 'day')}</p>
    </div>
    """


def _generate_empty_chart(title: str, period: str) -> str:
    """Generate HTML for empty chart placeholder."""
    return f"""
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">{title}</div>
            <div class="chart-period">{period}</div>
        </div>
        <div style="height: 300px; display: flex; align-items: center; justify-content: center; color: #6c757d;">
            <p>No data available for this period</p>
        </div>
    </div>
    """


def _generate_error_card(message: str) -> str:
    """Generate HTML for error card."""
    return f"""
    <div class="loading-card" style="border-left: 4px solid #e74c3c;">
        <p style="color: #e74c3c; margin: 0;">⚠️ {message}</p>
    </div>
    """