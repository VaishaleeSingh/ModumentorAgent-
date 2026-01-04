"""
Conversation memory management for maintaining chat history
"""
import json
import time
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from loguru import logger
from config import config


@dataclass
class Message:
    """Represents a single message in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float
    user_id: str


@dataclass
class Conversation:
    """Represents a full conversation with a user"""
    user_id: str
    messages: List[Message]
    created_at: float
    last_updated: float
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation"""
        message = Message(
            role=role,
            content=content,
            timestamp=time.time(),
            user_id=self.user_id
        )
        self.messages.append(message)
        self.last_updated = time.time()
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent messages from the conversation"""
        return self.messages[-limit:] if self.messages else []
    
    def get_context_string(self, limit: int = 10) -> str:
        """Get conversation context as a formatted string"""
        recent_messages = self.get_recent_messages(limit)
        if not recent_messages:
            return ""
        
        context_parts = []
        for msg in recent_messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def clear_old_messages(self, max_age_hours: int = 24) -> None:
        """Clear messages older than specified hours"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        self.messages = [msg for msg in self.messages if msg.timestamp > cutoff_time]


class ConversationMemory:
    """Manages conversation memory for all users with persistent storage"""
    
    def __init__(self, max_conversations: int = 1000, max_messages_per_conversation: int = 100):
        self.conversations: Dict[str, Conversation] = {}
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation
        self.storage_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'conversation_memory.json')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        
        # Load existing conversations from file
        self._load_conversations()
        logger.info("ConversationMemory initialized")
    
    def _load_conversations(self) -> None:
        """Load conversations from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for user_id, conv_data in data.items():
                    # Convert message data back to Message objects
                    messages = []
                    for msg_data in conv_data.get('messages', []):
                        message = Message(
                            role=msg_data['role'],
                            content=msg_data['content'],
                            timestamp=msg_data['timestamp'],
                            user_id=msg_data['user_id']
                        )
                        messages.append(message)
                    
                    # Create Conversation object
                    conversation = Conversation(
                        user_id=user_id,
                        messages=messages,
                        created_at=conv_data.get('created_at', time.time()),
                        last_updated=conv_data.get('last_updated', time.time())
                    )
                    self.conversations[user_id] = conversation
                    
                logger.info(f"Loaded {len(self.conversations)} conversations from storage")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
    
    def _save_conversations(self) -> None:
        """Save conversations to persistent storage"""
        try:
            # Convert conversations to serializable format
            data = {}
            for user_id, conversation in self.conversations.items():
                messages_data = []
                for msg in conversation.messages:
                    messages_data.append({
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp,
                        'user_id': msg.user_id
                    })
                
                data[user_id] = {
                    'user_id': conversation.user_id,
                    'messages': messages_data,
                    'created_at': conversation.created_at,
                    'last_updated': conversation.last_updated
                }
            
            # Save to file
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving conversations: {e}")
    
    def get_or_create_conversation(self, user_id: str) -> Conversation:
        """Get existing conversation or create new one"""
        if user_id not in self.conversations:
            self.conversations[user_id] = Conversation(
                user_id=user_id,
                messages=[],
                created_at=time.time(),
                last_updated=time.time()
            )
            logger.info(f"Created new conversation for user {user_id}")
            self._save_conversations()  # Save after creating new conversation
        
        return self.conversations[user_id]
    
    def add_user_message(self, user_id: str, message: str) -> None:
        """Add a user message to conversation"""
        conversation = self.get_or_create_conversation(user_id)
        conversation.add_message("user", message)
        self._cleanup_conversation(conversation)
        self._save_conversations()  # Save after adding message
        logger.debug(f"Added user message for {user_id}: {message[:50]}...")
    
    def add_assistant_message(self, user_id: str, message: str) -> None:
        """Add an assistant message to conversation"""
        conversation = self.get_or_create_conversation(user_id)
        conversation.add_message("assistant", message)
        self._cleanup_conversation(conversation)
        self._save_conversations()  # Save after adding message
        logger.debug(f"Added assistant message for {user_id}: {message[:50]}...")
    
    def get_conversation_context(self, user_id: str, limit: int = 10) -> str:
        """Get conversation context for a user"""
        conversation = self.get_or_create_conversation(user_id)
        return conversation.get_context_string(limit)
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear conversation for a specific user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            self._save_conversations()  # Save after clearing
            logger.info(f"Cleared conversation for user {user_id}")
            return True
        return False
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's conversation"""
        if user_id not in self.conversations:
            return {"message_count": 0, "conversation_age": 0}
        
        conversation = self.conversations[user_id]
        return {
            "message_count": len(conversation.messages),
            "conversation_age": time.time() - conversation.created_at,
            "last_message_time": conversation.last_updated
        }
    
    def _cleanup_conversation(self, conversation: Conversation) -> None:
        """Clean up conversation to maintain limits"""
        # Limit messages per conversation
        if len(conversation.messages) > self.max_messages_per_conversation:
            # Keep the most recent messages
            conversation.messages = conversation.messages[-self.max_messages_per_conversation:]
            logger.debug(f"Trimmed conversation for user {conversation.user_id}")
        
        # Clean up old messages (older than 24 hours)
        conversation.clear_old_messages(24)
    
    def cleanup_old_conversations(self, max_age_hours: int = 48) -> None:
        """Clean up conversations that haven't been active recently"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        old_conversations = [
            user_id for user_id, conv in self.conversations.items()
            if conv.last_updated < cutoff_time
        ]
        
        for user_id in old_conversations:
            del self.conversations[user_id]
            logger.info(f"Cleaned up old conversation for user {user_id}")
        
        # Also limit total number of conversations
        if len(self.conversations) > self.max_conversations:
            # Remove oldest conversations
            sorted_conversations = sorted(
                self.conversations.items(),
                key=lambda x: x[1].last_updated
            )
            
            excess_count = len(self.conversations) - self.max_conversations
            for user_id, _ in sorted_conversations[:excess_count]:
                del self.conversations[user_id]
                logger.info(f"Removed excess conversation for user {user_id}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        total_messages = sum(len(conv.messages) for conv in self.conversations.values())
        return {
            "total_conversations": len(self.conversations),
            "total_messages": total_messages,
            "average_messages_per_conversation": total_messages / len(self.conversations) if self.conversations else 0
        }

    def analyze_conversation(self, user_id: str) -> Dict[str, Any]:
        """Provide comprehensive conversation analysis"""
        if user_id not in self.conversations:
            return {
                "has_conversation": False,
                "message": "No conversation history found for this user."
            }
        
        conversation = self.conversations[user_id]
        messages = conversation.messages
        
        if not messages:
            return {
                "has_conversation": False,
                "message": "No messages in conversation history."
            }
        
        # Basic statistics
        total_messages = len(messages)
        user_messages = [msg for msg in messages if msg.role == "user"]
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        
        # Time analysis
        conversation_duration = conversation.last_updated - conversation.created_at
        hours_duration = conversation_duration / 3600
        
        # Topic analysis
        topics = self._extract_topics_from_messages(messages)
        
        # Sentiment analysis (simple keyword-based)
        sentiment = self._analyze_sentiment(messages)
        
        # Key insights
        insights = self._generate_insights(messages, topics, sentiment)
        
        # Recent activity
        recent_messages = conversation.get_recent_messages(5)
        recent_context = conversation.get_context_string(5)
        
        return {
            "has_conversation": True,
            "summary": {
                "total_messages": total_messages,
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "conversation_duration_hours": round(hours_duration, 2),
                "conversation_start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(conversation.created_at)),
                "last_activity": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(conversation.last_updated))
            },
            "topics": topics,
            "sentiment": sentiment,
            "insights": insights,
            "recent_context": recent_context,
            "recent_messages": [
                {
                    "role": msg.role,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "timestamp": time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
                }
                for msg in recent_messages
            ]
        }
    
    def _extract_topics_from_messages(self, messages: List[Message]) -> List[str]:
        """Extract main topics from conversation messages"""
        all_content = " ".join([msg.content.lower() for msg in messages])
        topics = []
        
        # Topic keywords
        topic_keywords = {
            "Weather": ["weather", "temperature", "forecast", "climate", "rain", "sunny", "cloudy"],
            "Email": ["email", "mail", "send", "compose", "inbox", "outbox"],
            "Spreadsheets": ["sheet", "spreadsheet", "excel", "google sheets", "data", "update"],
            "Web Search": ["search", "find", "lookup", "research", "information"],
            "Dictionary": ["define", "meaning", "word", "dictionary", "definition"],
            "Lyrics": ["lyrics", "song", "music", "artist", "album"],
            "Technical": ["code", "programming", "bug", "error", "fix", "debug"],
            "Business": ["meeting", "client", "project", "business", "work"],
            "General": ["hello", "hi", "how are you", "thanks", "thank you"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in all_content for keyword in keywords):
                topics.append(topic)
        
        # If no specific topics found, add general conversation
        if not topics:
            topics.append("General conversation")
        
        return topics
    
    def _analyze_sentiment(self, messages: List[Message]) -> Dict[str, Any]:
        """Simple sentiment analysis based on keywords"""
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "perfect", "love", "like", "thanks", "thank you", "helpful", "awesome"]
        negative_words = ["bad", "terrible", "awful", "hate", "dislike", "problem", "error", "wrong", "fail", "broken", "sad", "angry"]
        question_words = ["what", "how", "why", "when", "where", "who", "which", "?"]
        
        all_content = " ".join([msg.content.lower() for msg in messages])
        
        positive_count = sum(1 for word in positive_words if word in all_content)
        negative_count = sum(1 for word in negative_words if word in all_content)
        question_count = sum(1 for word in question_words if word in all_content)
        
        total_words = len(all_content.split())
        
        return {
            "positive_score": positive_count,
            "negative_score": negative_count,
            "question_count": question_count,
            "overall_sentiment": "positive" if positive_count > negative_count else "negative" if negative_count > positive_count else "neutral",
            "engagement_level": "high" if question_count > 3 else "medium" if question_count > 1 else "low"
        }
    
    def _generate_insights(self, messages: List[Message], topics: List[str], sentiment: Dict[str, Any]) -> List[str]:
        """Generate insights about the conversation"""
        insights = []
        
        # Message frequency insights
        if len(messages) > 10:
            insights.append("Active conversation with substantial message exchange")
        elif len(messages) > 5:
            insights.append("Moderate conversation activity")
        else:
            insights.append("Brief conversation session")
        
        # Topic insights
        if len(topics) > 3:
            insights.append("Diverse range of topics discussed")
        elif len(topics) > 1:
            insights.append("Multiple topics covered")
        else:
            insights.append("Focused on single topic")
        
        # Sentiment insights
        if sentiment["overall_sentiment"] == "positive":
            insights.append("Generally positive interaction")
        elif sentiment["overall_sentiment"] == "negative":
            insights.append("Some negative sentiment detected")
        else:
            insights.append("Neutral conversation tone")
        
        # Engagement insights
        if sentiment["engagement_level"] == "high":
            insights.append("High user engagement with many questions")
        elif sentiment["engagement_level"] == "medium":
            insights.append("Moderate user engagement")
        else:
            insights.append("Low question engagement")
        
        # Time-based insights
        if len(messages) > 0:
            time_span = messages[-1].timestamp - messages[0].timestamp
            if time_span > 3600:  # More than 1 hour
                insights.append("Extended conversation session")
            elif time_span > 300:  # More than 5 minutes
                insights.append("Sustained conversation")
            else:
                insights.append("Quick interaction")
        
        return insights
