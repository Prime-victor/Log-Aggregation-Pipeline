"""
Rule Engine — evaluates all active rules against live log data.

Design:
  - Stateless: engine reads from ES and writes to PostgreSQL only
  - Idempotent: safe to run multiple times (cooldown prevents duplicate alerts)
  - Extensible: add new Condition types by adding a method + entry to EVALUATORS dict

Called by: Celery Beat (every 60 seconds by default)
"""

import logging
from datetime import datetime, timezone, timedelta

import structlog
from django.db import transaction
from django.utils import timezone as django_tz

from apps.rules.models import Rule
from apps.alerts.models import Alert
from integrations.elasticsearch.log_repository import LogRepository

logger = structlog.get_logger(__name__)


class RuleEngine:

    def __init__(self):
        self.repo = LogRepository()

    def evaluate_all_rules(self) -> dict:
        """
        Entry point: evaluate every active rule.
        Returns a summary dict for logging/monitoring.
        """
        rules = Rule.objects.filter(is_active=True).select_related("created_by")
        results = {"evaluated": 0, "triggered": 0, "errors": 0}

        logger.info("rule_engine.start", rule_count=rules.count())

        for rule in rules:
            try:
                triggered = self._evaluate_rule(rule)
                results["evaluated"] += 1
                if triggered:
                    results["triggered"] += 1
            except Exception as e:
                results["errors"] += 1
                logger.error(
                    "rule_engine.evaluation_error",
                    rule_id=str(rule.id),
                    rule_name=rule.name,
                    error=str(e),
                    exc_info=True,
                )

        logger.info("rule_engine.complete", **results)
        return results

    def _evaluate_rule(self, rule: Rule) -> bool:
        """
        Evaluate a single rule. Returns True if an alert was triggered.
        """
        now = datetime.now(timezone.utc)

        # ── Cooldown check ────────────────────────────────────────────────────
        # Don't spam alerts. If the last trigger was within cooldown_sec, skip.
        if rule.last_triggered_at:
            elapsed = (now - rule.last_triggered_at).total_seconds()
            if elapsed < rule.cooldown_sec:
                logger.debug(
                    "rule_engine.cooldown_active",
                    rule_id=str(rule.id),
                    seconds_remaining=int(rule.cooldown_sec - elapsed),
                )
                return False

        # ── Compute the metric ────────────────────────────────────────────────
        value = self._compute_metric(rule)

        # Update evaluation timestamp
        rule.last_evaluated_at = now
        rule.save(update_fields=["last_evaluated_at"])

        logger.debug(
            "rule_engine.evaluated",
            rule_id=str(rule.id),
            rule_name=rule.name,
            condition=rule.condition,
            value=value,
            threshold=rule.threshold,
        )

        # ── Check threshold ───────────────────────────────────────────────────
        if not rule.matches_condition(value):
            return False

        # ── Trigger alert ─────────────────────────────────────────────────────
        self._trigger_alert(rule, value, now)
        return True

    def _compute_metric(self, rule: Rule) -> float:
        """
        Route to the correct metric computation based on rule condition.
        """
        service = rule.service or ""
        window  = rule.window_sec

        if rule.condition == Rule.Condition.ERROR_RATE:
            return self.repo.get_error_rate(service, window)

        elif rule.condition == Rule.Condition.LOG_COUNT:
            return float(self.repo.get_log_count(service, window))

        elif rule.condition == Rule.Condition.ERROR_COUNT:
            return float(self.repo.get_log_count(service, window, level="ERROR"))

        elif rule.condition == Rule.Condition.CRITICAL_COUNT:
            return float(self.repo.get_log_count(service, window, level="CRITICAL"))

        elif rule.condition == Rule.Condition.LATENCY_P99:
            return self._get_p99_latency(service, window)

        else:
            raise ValueError(f"Unknown condition: {rule.condition}")

    def _get_p99_latency(self, service: str, window_sec: int) -> float:
        """Compute P99 latency from ES percentile aggregation."""
        from integrations.elasticsearch.client import get_es_client
        from integrations.elasticsearch.indexes import get_log_index_pattern
        import time

        es    = get_es_client()
        start = int((time.time() - window_sec) * 1000)

        filters = [{"range": {"@timestamp": {"gte": start, "format": "epoch_millis"}}}]
        if service:
            filters.append({"term": {"service": service}})

        resp = es.search(
            index=get_log_index_pattern(service),
            body={
                "query": {"bool": {"filter": filters}},
                "size":  0,
                "aggs":  {
                    "p99": {"percentiles": {"field": "duration_ms", "percents": [99]}}
                }
            }
        )
        return resp["aggregations"]["p99"]["values"].get("99.0") or 0.0

    @transaction.atomic
    def _trigger_alert(self, rule: Rule, value: float, now: datetime) -> Alert:
        """
        Create an Alert record and schedule notification delivery.
        Wrapped in a transaction: alert creation + rule update are atomic.
        """
        window_start = now - timedelta(seconds=rule.window_sec)

        alert = Alert.objects.create(
            rule=rule,
            severity=rule.severity,
            service=rule.service or "ALL",
            triggered_value=value,
            threshold_value=rule.threshold,
            window_start=window_start,
            window_end=now,
            message=self._build_alert_message(rule, value),
        )

        # Update rule tracking
        rule.last_triggered_at = now
        rule.trigger_count     = rule.trigger_count + 1
        rule.save(update_fields=["last_triggered_at", "trigger_count"])

        logger.warning(
            "rule_engine.alert_triggered",
            alert_id=str(alert.id),
            rule_name=rule.name,
            service=rule.service or "ALL",
            value=value,
            threshold=rule.threshold,
            severity=rule.severity,
        )

        # Enqueue notification delivery 
        # Import here to avoid circular dependency
        from apps.notifications.tasks import deliver_alert_notification
        deliver_alert_notification.delay(str(alert.id))

        return alert

    def _build_alert_message(self, rule: Rule, value: float) -> str:
        service_str = rule.service or "all services"
        window_min  = rule.window_sec // 60

        templates = {
            Rule.Condition.ERROR_RATE:    f"Error rate for {service_str} is {value:.1f}% (threshold: {rule.threshold}%) in the last {window_min} minutes",
            Rule.Condition.LOG_COUNT:     f"Log volume for {service_str} reached {int(value)} entries (threshold: {int(rule.threshold)}) in the last {window_min} minutes",
            Rule.Condition.ERROR_COUNT:   f"Error count for {service_str} reached {int(value)} (threshold: {int(rule.threshold)}) in the last {window_min} minutes",
            Rule.Condition.CRITICAL_COUNT:f"Critical errors for {service_str}: {int(value)} (threshold: {int(rule.threshold)}) in the last {window_min} minutes",
            Rule.Condition.LATENCY_P99:   f"P99 latency for {service_str} is {value:.0f}ms (threshold: {rule.threshold:.0f}ms) in the last {window_min} minutes",
        }
        return templates.get(rule.condition, f"Rule '{rule.name}' triggered: value={value}, threshold={rule.threshold}")