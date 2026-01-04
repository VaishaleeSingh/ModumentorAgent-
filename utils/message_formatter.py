"""
Message formatting utilities for Telegram
"""
import re
from typing import List
from config import config


class MessageFormatter:
    """Utility class for formatting messages for Telegram"""
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape markdown special characters for Telegram"""
        # Characters that need escaping in Telegram MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def format_for_telegram(text: str) -> str:
        """Format text for Telegram with safe markdown handling"""
        try:
            # Clean up problematic markdown characters that cause parsing errors
            # Remove or fix malformed markdown
            text = MessageFormatter._clean_markdown(text)

            # Convert **bold** to *bold* for Telegram (but be careful with existing asterisks)
            text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)

            # Ensure text doesn't exceed Telegram limits
            if len(text) > config.MAX_MESSAGE_LENGTH:
                text = text[:config.MAX_MESSAGE_LENGTH - 3] + "..."

            return text
        except Exception as e:
            # If formatting fails, return plain text
            return MessageFormatter._strip_all_markdown(text)

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Clean problematic markdown that causes parsing errors"""
        # Fix unmatched asterisks
        text = MessageFormatter._fix_unmatched_asterisks(text)

        # Fix unmatched underscores
        text = MessageFormatter._fix_unmatched_underscores(text)

        # Fix problematic brackets
        text = MessageFormatter._fix_unmatched_brackets(text)

        return text

    @staticmethod
    def _fix_unmatched_asterisks(text: str) -> str:
        """Fix unmatched asterisks that cause markdown parsing errors"""
        # Count asterisks and escape odd ones at the end
        asterisk_count = text.count('*')
        if asterisk_count % 2 != 0:
            # Find the last asterisk and escape it
            last_asterisk = text.rfind('*')
            if last_asterisk != -1:
                text = text[:last_asterisk] + '\\*' + text[last_asterisk + 1:]
        return text

    @staticmethod
    def _fix_unmatched_underscores(text: str) -> str:
        """Fix unmatched underscores that cause markdown parsing errors"""
        # Similar logic for underscores
        underscore_count = text.count('_')
        if underscore_count % 2 != 0:
            last_underscore = text.rfind('_')
            if last_underscore != -1:
                text = text[:last_underscore] + '\\_' + text[last_underscore + 1:]
        return text

    @staticmethod
    def _fix_unmatched_brackets(text: str) -> str:
        """Fix unmatched brackets that cause markdown parsing errors"""
        # Escape standalone brackets that aren't part of proper markdown links
        text = re.sub(r'(?<!\[)\](?!\()', r'\\]', text)  # Escape ] not preceded by [
        text = re.sub(r'\[(?![^\]]*\]\([^)]*\))', r'\\[', text)  # Escape [ not part of [text](url)
        return text

    @staticmethod
    def _strip_all_markdown(text: str) -> str:
        """Strip all markdown formatting and return plain text"""
        # Remove all markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove **bold**
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove *italic*
        text = re.sub(r'_(.*?)_', r'\1', text)        # Remove _underline_
        text = re.sub(r'`(.*?)`', r'\1', text)        # Remove `code`
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)  # Remove [text](url)

        # Ensure text doesn't exceed Telegram limits
        if len(text) > config.MAX_MESSAGE_LENGTH:
            text = text[:config.MAX_MESSAGE_LENGTH - 3] + "..."

        return text
    
    @staticmethod
    def split_long_message(text: str, max_length: int = None) -> List[str]:
        """Split long messages into chunks for Telegram"""
        if max_length is None:
            max_length = config.MAX_MESSAGE_LENGTH
        
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk + paragraph) <= max_length:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    # Paragraph is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_chunk + sentence) <= max_length:
                            if current_chunk:
                                current_chunk += '. ' + sentence
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    @staticmethod
    def add_typing_indicator(text: str) -> str:
        """Add typing indicator emoji to make responses feel more natural"""
        if not text.strip():
            return text
        
        # Add thinking emoji for longer responses
        if len(text) > 500:
            return f"🤔 {text}"
        
        return text
