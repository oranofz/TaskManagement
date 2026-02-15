"""Password hashing and validation utilities."""
import re
import hashlib
from typing import Optional
import httpx
from passlib.context import CryptContext
from loguru import logger


pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4
)


class PasswordHandler:
    """Password hashing and validation handler."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using Argon2id.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password meets strength requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"

        return True, None

    @staticmethod
    async def check_compromised_password(password: str) -> bool:
        """
        Check if password has been compromised using HaveIBeenPwned API.
        Uses k-Anonymity model - only sends first 5 chars of SHA1 hash.

        Args:
            password: Password to check

        Returns:
            True if password is compromised
        """
        # Generate SHA1 hash of password
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.pwnedpasswords.com/range/{prefix}",
                    headers={"Add-Padding": "true"}
                )

                if response.status_code != 200:
                    logger.warning(f"HaveIBeenPwned API returned status {response.status_code}")
                    return False

                # Check if our suffix appears in the response
                hashes = response.text.splitlines()
                for hash_line in hashes:
                    hash_suffix = hash_line.split(":")[0]
                    if hash_suffix == suffix:
                        return True

                return False
        except Exception as e:
            logger.error(f"Error checking compromised password: {e}")
            # Don't block registration if API is down
            return False


password_handler = PasswordHandler()

