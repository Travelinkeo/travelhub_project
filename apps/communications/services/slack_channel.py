"""
Slack / Teams Webhook Notification Channel.

Envía notificaciones a canales de Slack mediante Incoming Webhooks.
"""

import json  # noqa: I001
import logging
import urllib.request  # noqa: S310 (webhook URLs from settings, safe)

from django.conf import settings

logger = logging.getLogger(__name__)


class SlackChannel:
    """Canal de notificaciones vía Slack (Incoming Webhook)."""

    CHANNEL_TYPE = "slack"

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Envía una notificación a un webhook de Slack."""
        webhook_url = self._get_webhook_url(recipient)
        if not webhook_url:
            logger.warning("No Slack webhook URL configured for %s", recipient)
            return False

        payload = {
            "text": f"*{subject}*\n{message}",
            "mrkdwn": True,
            "username": "TravelHub",
            "icon_emoji": ":airplane:",
        }

        blocks = kwargs.get("blocks")
        if blocks:
            payload["blocks"] = blocks

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(  # noqa: S310
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                if resp.status == 200:
                    logger.info("Slack notification sent to %s", recipient[:50])
                    return True
                logger.warning("Slack returned %s: %s", resp.status, resp.read()[:200])
                return False
        except Exception as e:
            logger.error("Slack notification failed: %s", e)
            return False

    def _get_webhook_url(self, identifier: str) -> str:
        """
        Resuelve la URL del webhook.
        `identifier` puede ser:
          - Una URL directa de webhook
          - Una clave del settings.SLACK_WEBHOOKS dict
          - El nombre de agencia (se busca en settings)
        """
        if identifier.startswith("https://hooks.slack.com/"):
            return identifier
        webhooks = getattr(settings, "SLACK_WEBHOOKS", {})
        if identifier in webhooks:
            return webhooks[identifier]
        return webhooks.get("default", "")


class TeamsChannel:
    """Canal de notificaciones vía Microsoft Teams (webhook)."""

    CHANNEL_TYPE = "teams"

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """send."""
        webhook_url = self._get_webhook_url(recipient)
        if not webhook_url:
            return False

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": subject,
            "title": subject,
            "text": message,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(  # noqa: S310
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                return resp.status == 200
        except Exception as e:
            logger.error("Teams notification failed: %s", e)
            return False

    def _get_webhook_url(self, identifier: str) -> str:
        """_get_webhook_url."""
        if identifier.startswith("https://"):
            return identifier
        webhooks = getattr(settings, "TEAMS_WEBHOOKS", {})
        return webhooks.get(identifier, webhooks.get("default", ""))
