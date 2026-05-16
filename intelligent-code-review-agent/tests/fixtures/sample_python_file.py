"""Sample Python file for testing AST extraction."""

import os
import sys
from pathlib import Path
from typing import Optional


class UserService:
    """Manages user operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._cache: dict[str, dict] = {}

    def find_user(self, username: str) -> Optional[dict]:
        """Find a user by username."""
        if username in self._cache:
            return self._cache[username]

        # Query database
        result = self._query_db(username)
        if result:
            self._cache[username] = result
        return result

    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create a new user."""
        if not username or not email:
            return False

        if self.find_user(username):
            return False  # User already exists

        # Store user (password should be hashed!)
        user_data = {
            "username": username,
            "email": email,
            "password": password,  # BUG: storing plain text password
        }
        return self._save_user(user_data)

    def _query_db(self, username: str) -> Optional[dict]:
        """Query the database for a user."""
        # Placeholder implementation
        return None

    def _save_user(self, user_data: dict) -> bool:
        """Save user to database."""
        return True


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[1]


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
