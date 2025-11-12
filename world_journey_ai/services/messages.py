"""Message storage and management for World Journey AI.

This module provides a thread-safe message store for chat conversations
with support for timestamp filtering and HTML content.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

# Type aliases
MessageDict = Dict[str, Any]
MessageList = List[MessageDict]


class MessageStore:
    """Thread-safe message storage with automatic cleanup.
    
    Stores chat messages with timestamps and optional HTML content.
    Automatically limits the number of stored messages using a deque.
    """
    
    def __init__(self, limit: int = 200) -> None:
        """Initialize message store.
        
        Args:
            limit: Maximum number of messages to store (default: 200)
            
        Raises:
            ValueError: If limit is not positive
        """
        if limit <= 0:
            raise ValueError("Message limit must be positive")
            
        self._messages: Deque[MessageDict] = deque(maxlen=limit)
        self._limit = limit

    def add(self, role: str, text: str, *, html: Optional[str] = None) -> MessageDict:
        """Add a new message to the store.
        
        Args:
            role: Message role (e.g., "user", "assistant")
            text: Plain text content of the message
            html: Optional HTML content for rich formatting
            
        Returns:
            The created message dictionary
            
        Raises:
            ValueError: If role or text is empty
        """
        if not role.strip():
            raise ValueError("Message role cannot be empty")
        if not text.strip():
            raise ValueError("Message text cannot be empty")
            
        timestamp = self._now_iso()
        entry: MessageDict = {
            "id": timestamp,  # Use timestamp as unique ID
            "role": role.strip(),
            "text": text.strip(),
            "createdAt": timestamp,
        }
        
        if html and html.strip():
            entry["html"] = html.strip()
            
        self._messages.append(entry)
        return entry

    def list(self) -> MessageList:
        """Get all stored messages.
        
        Returns:
            List of all message dictionaries in chronological order
        """
        return list(self._messages)

    def since(self, since_iso: str) -> MessageList:
        """Get messages created after a specific timestamp.
        
        Args:
            since_iso: ISO format timestamp string
            
        Returns:
            List of messages created after the given timestamp
        """
        try:
            since_dt = self._parse_iso_timestamp(since_iso)
        except ValueError:
            # If timestamp parsing fails, return all messages
            return self.list()

        filtered: MessageList = []
        for message in self._messages:
            if self._message_is_after(message, since_dt):
                filtered.append(message)
                
        return filtered

    def clear(self) -> None:
        """Clear all stored messages."""
        self._messages.clear()

    def count(self) -> int:
        """Get the current number of stored messages.
        
        Returns:
            Number of messages in the store
        """
        return len(self._messages)

    def get_limit(self) -> int:
        """Get the maximum number of messages that can be stored.
        
        Returns:
            Message storage limit
        """
        return self._limit

    @staticmethod
    def _now_iso() -> str:
        """Get current timestamp in ISO format.
        
        Returns:
            Current UTC timestamp as ISO string
        """
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_iso_timestamp(iso_string: str) -> datetime:
        """Parse ISO timestamp string to datetime object.
        
        Args:
            iso_string: ISO format timestamp string
            
        Returns:
            Parsed datetime object with UTC timezone
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        try:
            dt = datetime.fromisoformat(iso_string)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {iso_string}") from e

    def _message_is_after(self, message: MessageDict, since_dt: datetime) -> bool:
        """Check if message was created after a specific datetime.
        
        Args:
            message: Message dictionary to check
            since_dt: Comparison datetime
            
        Returns:
            True if message is after the given datetime
        """
        created_raw = message.get("createdAt")
        if not created_raw:
            return True  # Include messages without timestamps
            
        try:
            created = self._parse_iso_timestamp(str(created_raw))
            return created > since_dt
        except ValueError:
            return True  # Include messages with invalid timestamps
