"""
Celery tasks for the rule engine.

Scheduled by Celery Beat (configured via django-celery-beat admin UI or fixtures).
"""

import logging
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="rules.evaluate_all_rules",
    max_retries=3,
    default_retry_delay=30,           # Retry after 30s on failure
    acks_late=True,                   # Only ack after completion (prevents lost tasks on crash)
    reject_on_worker_lost=True,
)
def evaluate_all_rules(self):
    """
    Main rule evaluation task.
    Runs every 60 seconds by default (configured in Celery Beat schedule).

    Using `bind=True` gives access to self for retry handling.
    """
    try:
        from apps.rules.engine import RuleEngine
        engine  = RuleEngine()
        results = engine.evaluate_all_rules()

        logger.info(
            f"Rule evaluation complete: "
            f"{results['evaluated']} evaluated, "
            f"{results['triggered']} triggered, "
            f"{results['errors']} errors"
        )
        return results

    except Exception as exc:
        logger.error(f"Rule evaluation task failed: {exc}", exc_info=True)
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@shared_task(
    bind=True,
    name="rules.evaluate_single_rule",
    max_retries=2,
)
def evaluate_single_rule(self, rule_id: str):
    """
    Evaluate a single rule on-demand (e.g., when a rule is created/updated).
    Useful for immediate validation feedback.
    """
    try:
        from apps.rules.models import Rule
        from apps.rules.engine import RuleEngine

        rule   = Rule.objects.get(id=rule_id, is_active=True)
        engine = RuleEngine()
        engine._evaluate_rule(rule)

    except Exception as exc:
        logger.error(f"Single rule evaluation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)