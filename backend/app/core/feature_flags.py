"""
Feature flag system for safe database views rollout.
Following trunk-based development best practices.
"""

import hashlib
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class RolloutStrategy(Enum):
    """Feature rollout strategies."""

    OFF = "off"
    ON = "on"
    PERCENTAGE = "percentage"
    USER_WHITELIST = "user_whitelist"
    GRADUAL = "gradual"


class FeatureFlags:
    """
    Centralized feature flag management for database views migration.

    Uses environment variables for configuration in production.
    Implements gradual rollout strategy for safe deployment.
    """

    # Feature flag definitions
    FLAGS: dict[str, dict[str, Any]] = {
        "use_database_views": {
            "enabled": False,
            "strategy": RolloutStrategy.GRADUAL,
            "percentage": 0.0,
            "whitelist_users": ["admin@kidney-genetics.org"],
            "rollout_steps": {1: 0, 2: 10, 3: 25, 4: 50, 5: 75, 6: 100},
            "current_step": 1,
        },
        "use_materialized_views": {
            "enabled": False,
            "strategy": RolloutStrategy.PERCENTAGE,
            "percentage": 0.0,
        },
        "enable_shadow_testing": {"enabled": True, "strategy": RolloutStrategy.ON},
    }

    @classmethod
    def is_enabled(
        cls, flag_name: str, user_id: str | None = None, context: dict[str, Any] | None = None
    ) -> bool:
        """
        Check if feature flag is enabled for given context.

        Args:
            flag_name: Name of the feature flag
            user_id: Optional user identifier for user-based rollout
            context: Additional context for decision

        Returns:
            True if feature is enabled
        """
        flag = cls.FLAGS.get(flag_name)
        if not flag:
            logger.sync_warning(f"Unknown feature flag: {flag_name}")
            return False

        # Check if globally disabled
        if not flag.get("enabled", False):
            return False

        strategy = flag.get("strategy", RolloutStrategy.OFF)

        # Apply rollout strategy
        if strategy == RolloutStrategy.ON:
            return True

        elif strategy == RolloutStrategy.OFF:
            return False

        elif strategy == RolloutStrategy.USER_WHITELIST:
            whitelist = flag.get("whitelist_users", [])
            return bool(user_id and user_id in whitelist)

        elif strategy == RolloutStrategy.PERCENTAGE:
            if not user_id:
                return False
            # Consistent hash for user (MD5 for distribution, not security)
            user_hash = int(
                hashlib.md5(user_id.encode(), usedforsecurity=False).hexdigest(), 16
            )
            percentage = int(flag.get("percentage", 0))
            return bool((user_hash % 100) < percentage)

        elif strategy == RolloutStrategy.GRADUAL:
            # Use current step to determine percentage
            current_step = int(flag.get("current_step", 1))
            rollout_steps: dict[int, int] = flag.get("rollout_steps", {})

            if current_step in rollout_steps:
                target_percentage = rollout_steps[current_step]
            else:
                target_percentage = 0

            if user_id:
                user_hash = int(
                    hashlib.md5(user_id.encode(), usedforsecurity=False).hexdigest(), 16
                )
                return bool((user_hash % 100) < target_percentage)

            return False

        return False

    @classmethod
    def advance_rollout(cls, flag_name: str) -> bool:
        """
        Advance to the next rollout step.

        Args:
            flag_name: Name of the feature flag

        Returns:
            True if advanced, False if at final step or error
        """
        flag = cls.FLAGS.get(flag_name)
        if not flag:
            return False

        if flag.get("strategy") != RolloutStrategy.GRADUAL:
            return False

        current_step = flag.get("current_step", 1)
        rollout_steps = flag.get("rollout_steps", {})

        # Find next step
        next_step = current_step + 1
        if next_step in rollout_steps:
            flag["current_step"] = next_step
            logger.sync_info(
                f"Advanced {flag_name} to step {next_step} ({rollout_steps[next_step]}%)"
            )
            return True

        return False

    @classmethod
    def set_percentage(cls, flag_name: str, percentage: float) -> None:
        """
        Update rollout percentage (for testing/emergency rollback).

        Args:
            flag_name: Name of the feature flag
            percentage: New percentage (0-100)
        """
        if flag_name in cls.FLAGS:
            cls.FLAGS[flag_name]["percentage"] = max(0, min(100, percentage))
            logger.sync_info(f"Updated {flag_name} to {percentage}%")

    @classmethod
    def emergency_disable(cls, flag_name: str) -> None:
        """
        Emergency disable a feature flag.

        Args:
            flag_name: Name of the feature flag to disable
        """
        if flag_name in cls.FLAGS:
            cls.FLAGS[flag_name]["enabled"] = False
            logger.sync_critical(f"EMERGENCY: Disabled feature flag {flag_name}")

    @classmethod
    def get_status(cls) -> dict[str, dict[str, Any]]:
        """
        Get current status of all feature flags.

        Returns:
            Dictionary with flag statuses
        """
        status = {}
        for flag_name, flag_config in cls.FLAGS.items():
            status[flag_name] = {
                "enabled": flag_config.get("enabled", False),
                "strategy": str(flag_config.get("strategy", RolloutStrategy.OFF)),
            }

            if flag_config.get("strategy") == RolloutStrategy.PERCENTAGE:
                status[flag_name]["percentage"] = flag_config.get("percentage", 0)
            elif flag_config.get("strategy") == RolloutStrategy.GRADUAL:
                current_step = flag_config.get("current_step", 1)
                rollout_steps = flag_config.get("rollout_steps", {})
                status[flag_name]["current_step"] = current_step
                status[flag_name]["current_percentage"] = rollout_steps.get(current_step, 0)

        return status
