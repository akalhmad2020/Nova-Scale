from collections.abc import Mapping

from app.modules.notifications.application.exceptions import (
    NotificationProviderNotConfiguredError,
)
from app.modules.notifications.application.ports.providers import (
    NotificationProvider,
)
from app.modules.notifications.domain.enums import NotificationChannel


class NotificationProviderRegistry:
    def __init__(
        self,
        providers: Mapping[
            NotificationChannel,
            NotificationProvider,
        ],
    ) -> None:
        self._providers = dict(providers)

    def resolve(
        self,
        channel: NotificationChannel,
    ) -> NotificationProvider:
        provider = self._providers.get(channel)

        if provider is None:
            raise NotificationProviderNotConfiguredError(
                f"No notification provider configured for channel '{channel.value}'."
            )

        return provider
