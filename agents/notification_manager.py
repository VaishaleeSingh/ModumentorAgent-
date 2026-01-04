"""
Real-time Notification Manager for ModuMentor
Provides proactive notifications and intelligent alerts
"""
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import json
import os


class NotificationType(Enum):
    """Types of notifications"""
    EMAIL_ALERT = "email_alert"
    CALENDAR_REMINDER = "calendar_reminder"
    DATA_CHANGE = "data_change"
    WEATHER_ALERT = "weather_alert"
    TASK_REMINDER = "task_reminder"
    SYSTEM_STATUS = "system_status"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Represents a notification"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    user_id: str
    scheduled_time: datetime
    created_time: datetime
    is_sent: bool = False
    metadata: Dict[str, Any] = None


@dataclass
class NotificationRule:
    """Represents a notification rule"""
    id: str
    name: str
    trigger_condition: str
    notification_type: NotificationType
    priority: NotificationPriority
    message_template: str
    is_active: bool = True
    user_id: str = None


class ProactiveNotificationManager:
    """Manages proactive notifications and intelligent alerts"""
    
    def __init__(self, telegram_bot=None):
        self.telegram_bot = telegram_bot
        self.notifications: List[Notification] = []
        self.notification_rules: List[NotificationRule] = []
        self.is_running = False
        self.notification_file = "data/notifications.json"
        self.rules_file = "data/notification_rules.json"
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Load existing notifications and rules
        self._load_notifications()
        self._load_rules()
        
        # Set up default notification rules
        self._setup_default_rules()
        
        logger.info("ProactiveNotificationManager initialized")
    
    def _setup_default_rules(self):
        """Set up default notification rules"""
        default_rules = [
            NotificationRule(
                id="morning_briefing",
                name="Morning Briefing",
                trigger_condition="daily_08:00",
                notification_type=NotificationType.SYSTEM_STATUS,
                priority=NotificationPriority.MEDIUM,
                message_template="🌅 **Good Morning!** Here's your daily briefing:\n\n• Weather forecast for today\n• Upcoming calendar events\n• Important emails\n• System status"
            ),
            NotificationRule(
                id="weather_alerts",
                name="Weather Alerts",
                trigger_condition="weather_change_significant",
                notification_type=NotificationType.WEATHER_ALERT,
                priority=NotificationPriority.HIGH,
                message_template="🌦️ **Weather Alert:** Significant weather changes detected. Check the forecast for planning."
            ),
            NotificationRule(
                id="email_digest",
                name="Email Digest",
                trigger_condition="daily_17:00",
                notification_type=NotificationType.EMAIL_ALERT,
                priority=NotificationPriority.LOW,
                message_template="📧 **Daily Email Summary:** You have {unread_count} unread emails. Important messages require attention."
            ),
            NotificationRule(
                id="weekend_prep",
                name="Weekend Preparation",
                trigger_condition="friday_16:00",
                notification_type=NotificationType.TASK_REMINDER,
                priority=NotificationPriority.MEDIUM,
                message_template="🎉 **Weekend Prep:** Review your week's accomplishments and prepare for next week."
            )
        ]
        
        # Add default rules if they don't exist
        existing_rule_ids = {rule.id for rule in self.notification_rules}
        for rule in default_rules:
            if rule.id not in existing_rule_ids:
                self.notification_rules.append(rule)
        
        self._save_rules()
    
    async def start_notification_service(self):
        """Start the proactive notification service"""
        if self.is_running:
            logger.warning("Notification service is already running")
            return
        
        self.is_running = True
        logger.info("Starting proactive notification service")
        
        # Schedule default notifications
        self._schedule_notifications()
        
        # Start the notification loop
        asyncio.create_task(self._notification_loop())
    
    def stop_notification_service(self):
        """Stop the notification service"""
        self.is_running = False
        logger.info("Stopped proactive notification service")
    
    async def _notification_loop(self):
        """Main notification processing loop"""
        while self.is_running:
            try:
                # Check for due notifications
                await self._process_due_notifications()
                
                # Check for trigger conditions
                await self._check_trigger_conditions()
                
                # Clean up old notifications
                self._cleanup_old_notifications()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                await asyncio.sleep(60)
    
    def _schedule_notifications(self):
        """Schedule recurring notifications"""
        # Morning briefing
        schedule.every().day.at("08:00").do(
            self._create_scheduled_notification,
            "morning_briefing",
            "🌅 **Good Morning!**",
            "Here's your daily briefing with weather, calendar, and important updates."
        )
        
        # Evening summary
        schedule.every().day.at("17:00").do(
            self._create_scheduled_notification,
            "evening_summary",
            "📊 **Daily Summary**",
            "Review of today's activities and preparation for tomorrow."
        )
        
        # Weekend preparation
        schedule.every().friday.at("16:00").do(
            self._create_scheduled_notification,
            "weekend_prep",
            "🎉 **Weekend Preparation**",
            "Time to wrap up the week and prepare for a great weekend!"
        )
    
    def _create_scheduled_notification(self, notification_id: str, title: str, message: str):
        """Create a scheduled notification"""
        notification = Notification(
            id=f"{notification_id}_{int(time.time())}",
            type=NotificationType.SYSTEM_STATUS,
            priority=NotificationPriority.MEDIUM,
            title=title,
            message=message,
            user_id="all",  # Send to all users
            scheduled_time=datetime.now(),
            created_time=datetime.now()
        )
        
        self.notifications.append(notification)
        self._save_notifications()
    
    async def _process_due_notifications(self):
        """Process notifications that are due"""
        current_time = datetime.now()
        
        for notification in self.notifications:
            if (not notification.is_sent and 
                notification.scheduled_time <= current_time):
                
                await self._send_notification(notification)
                notification.is_sent = True
        
        self._save_notifications()
    
    async def _send_notification(self, notification: Notification):
        """Send a notification to the user"""
        try:
            if self.telegram_bot and notification.user_id != "all":
                # Send to specific user
                await self._send_telegram_notification(notification)
            else:
                # Log notification (can be enhanced to send to all users)
                logger.info(f"Notification: {notification.title} - {notification.message}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _send_telegram_notification(self, notification: Notification):
        """Send notification via Telegram"""
        try:
            # Format notification message
            priority_emoji = {
                NotificationPriority.LOW: "ℹ️",
                NotificationPriority.MEDIUM: "⚠️",
                NotificationPriority.HIGH: "🚨",
                NotificationPriority.URGENT: "🔥"
            }
            
            emoji = priority_emoji.get(notification.priority, "📢")
            formatted_message = f"{emoji} **{notification.title}**\n\n{notification.message}"
            
            # Send via telegram bot (implementation depends on bot structure)
            if hasattr(self.telegram_bot, 'send_message'):
                await self.telegram_bot.send_message(
                    chat_id=notification.user_id,
                    text=formatted_message,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
    
    async def _check_trigger_conditions(self):
        """Check for trigger conditions that should create notifications"""
        for rule in self.notification_rules:
            if not rule.is_active:
                continue
            
            try:
                if await self._evaluate_trigger_condition(rule.trigger_condition):
                    await self._create_rule_notification(rule)
                    
            except Exception as e:
                logger.error(f"Error checking trigger condition for rule {rule.id}: {e}")
    
    async def _evaluate_trigger_condition(self, condition: str) -> bool:
        """Evaluate if a trigger condition is met"""
        current_time = datetime.now()
        
        # Time-based triggers
        if condition.startswith("daily_"):
            trigger_time = condition.split("_")[1]
            hour, minute = map(int, trigger_time.split(":"))
            return (current_time.hour == hour and 
                   current_time.minute == minute)
        
        elif condition.startswith("friday_"):
            if current_time.weekday() == 4:  # Friday
                trigger_time = condition.split("_")[1]
                hour, minute = map(int, trigger_time.split(":"))
                return (current_time.hour == hour and 
                       current_time.minute == minute)
        
        # Weather-based triggers
        elif condition == "weather_change_significant":
            # This would integrate with weather monitoring
            return False  # Placeholder
        
        # Data-based triggers
        elif condition == "new_emails_important":
            # This would integrate with email monitoring
            return False  # Placeholder
        
        return False
    
    async def _create_rule_notification(self, rule: NotificationRule):
        """Create a notification based on a rule"""
        # Check if we already sent this notification recently
        recent_notifications = [
            n for n in self.notifications
            if (n.type == rule.notification_type and
                n.created_time > datetime.now() - timedelta(hours=1))
        ]
        
        if recent_notifications:
            return  # Don't spam notifications
        
        notification = Notification(
            id=f"{rule.id}_{int(time.time())}",
            type=rule.notification_type,
            priority=rule.priority,
            title=rule.name,
            message=rule.message_template,
            user_id=rule.user_id or "all",
            scheduled_time=datetime.now(),
            created_time=datetime.now()
        )
        
        self.notifications.append(notification)
        self._save_notifications()
    
    def _cleanup_old_notifications(self):
        """Clean up old notifications"""
        cutoff_time = datetime.now() - timedelta(days=7)
        self.notifications = [
            n for n in self.notifications
            if n.created_time > cutoff_time
        ]
        self._save_notifications()
    
    def add_custom_notification(self, user_id: str, title: str, message: str, 
                              scheduled_time: datetime = None, 
                              priority: NotificationPriority = NotificationPriority.MEDIUM) -> str:
        """Add a custom notification"""
        notification_id = f"custom_{int(time.time())}"
        
        notification = Notification(
            id=notification_id,
            type=NotificationType.TASK_REMINDER,
            priority=priority,
            title=title,
            message=message,
            user_id=user_id,
            scheduled_time=scheduled_time or datetime.now(),
            created_time=datetime.now()
        )
        
        self.notifications.append(notification)
        self._save_notifications()
        
        return notification_id
    
    def _load_notifications(self):
        """Load notifications from file"""
        try:
            if os.path.exists(self.notification_file):
                with open(self.notification_file, 'r') as f:
                    data = json.load(f)
                    self.notifications = [
                        Notification(**item) for item in data
                    ]
        except Exception as e:
            logger.error(f"Error loading notifications: {e}")
            self.notifications = []
    
    def _save_notifications(self):
        """Save notifications to file"""
        try:
            with open(self.notification_file, 'w') as f:
                data = [
                    {
                        'id': n.id,
                        'type': n.type.value,
                        'priority': n.priority.value,
                        'title': n.title,
                        'message': n.message,
                        'user_id': n.user_id,
                        'scheduled_time': n.scheduled_time.isoformat(),
                        'created_time': n.created_time.isoformat(),
                        'is_sent': n.is_sent,
                        'metadata': n.metadata
                    }
                    for n in self.notifications
                ]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
    
    def _load_rules(self):
        """Load notification rules from file"""
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    self.notification_rules = [
                        NotificationRule(**item) for item in data
                    ]
        except Exception as e:
            logger.error(f"Error loading notification rules: {e}")
            self.notification_rules = []
    
    def _save_rules(self):
        """Save notification rules to file"""
        try:
            with open(self.rules_file, 'w') as f:
                data = [
                    {
                        'id': r.id,
                        'name': r.name,
                        'trigger_condition': r.trigger_condition,
                        'notification_type': r.notification_type.value,
                        'priority': r.priority.value,
                        'message_template': r.message_template,
                        'is_active': r.is_active,
                        'user_id': r.user_id
                    }
                    for r in self.notification_rules
                ]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving notification rules: {e}")
