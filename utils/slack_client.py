"""
Moduł do komunikacji ze Slackiem z retry i idempotencją.
"""
import hashlib
import os
import time
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _idempotency_key(text: str) -> str:
    """Oblicza klucz idempotencji dla wiadomości."""
    return hashlib.sha1(text.encode()).hexdigest()


# Globalna instancja - singleton
_notifier_instance: Optional["SlackNotifier"] = None


def _get_notifier() -> "SlackNotifier":
    """Zwraca globalną instancję SlackNotifier (singleton)."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = SlackNotifier()
    return _notifier_instance


def post_message(text: str, channel: Optional[str] = None, retries: int = 3) -> None:
    """
    Helper function: wysyła wiadomość tekstową na Slack.

    Args:
        text: Treść wiadomości
        channel: Kanał docelowy
        retries: Liczba prób
    """
    notifier = _get_notifier()
    notifier.post_message(text, channel, retries)


def upload_file(
    file_path: str,
    channel: Optional[str] = None,
    initial_comment: str = "",
    retries: int = 3
) -> None:
    """
    Helper function: wysyła plik na Slack.

    Args:
        file_path: Ścieżka do pliku
        channel: Kanał docelowy
        initial_comment: Komentarz przy pliku
        retries: Liczba prób
    """
    notifier = _get_notifier()
    with open(file_path, "rb") as f:
        content = f.read()
    notifier.upload_file(content, os.path.basename(file_path), channel, initial_comment, retries)


class SlackNotifier:
    """Klasa do wysyłania wiadomości i plików na Slack."""

    def __init__(self):
        """Inicjalizacja klienta Slack z tokena ENV."""
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise ValueError("Brak SLACK_BOT_TOKEN w zmiennych środowiskowych")
        self.client = WebClient(token=token)
        self.channel = os.environ.get("SLACK_CHANNEL", "#alpha-lab")
    
    def post_message(self, text: str, channel: Optional[str] = None, retries: int = 3) -> None:
        """
        Wysyła wiadomość tekstową na Slack z retry i idempotencją.

        Jeśli wiadomość > 3000 znaków, dzieli lub wysyła jako plik .md.

        Parameters:
        -----------
        text : str
            Treść wiadomości
        channel : Optional[str]
            Kanał docelowy (domyślnie self.channel)
        retries : int
            Liczba prób (domyślnie 3)
        """
        target_channel = channel or self.channel
        key = _idempotency_key(text)

        for i in range(retries):
            try:
                if len(text) > 3000:
                    # Zbyt długa wiadomość - wyślij jako plik
                    print("Wiadomość za długa, wysyłam jako plik...")
                    self.upload_file(
                        file_content=text.encode('utf-8'),
                        filename="raport.md",
                        channel=target_channel,
                        initial_comment="Raport (pełna treść)"
                    )
                else:
                    self.client.chat_postMessage(
                        channel=target_channel,
                        text=text,
                        username="alpha-lab bot",
                        metadata={
                            "event_type": "alpha_report",
                            "event_payload": {"key": key}
                        }
                    )
                    print(f"Wiadomość wysłana na {target_channel}")
                return

            except SlackApiError as e:
                if i == retries - 1:
                    print(f"BŁĄD przy wysyłaniu wiadomości: {e.response['error']}")
                    raise
                time.sleep(2 ** i)
    
    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        channel: Optional[str] = None,
        initial_comment: str = "",
        retries: int = 3
    ) -> None:
        """
        Wysyła plik na Slack z retry.

        Parameters:
        -----------
        file_content : bytes
            Zawartość pliku w bajtach
        filename : str
            Nazwa pliku
        channel : Optional[str]
            Kanał docelowy
        initial_comment : str
            Komentarz przy pliku
        retries : int
            Liczba prób (domyślnie 3)
        """
        target_channel = channel or self.channel

        for i in range(retries):
            try:
                self.client.files_upload_v2(
                    channel=target_channel,
                    file=file_content,
                    filename=filename,
                    initial_comment=initial_comment
                )
                print(f"Plik {filename} wysłany na {target_channel}")
                return

            except SlackApiError as e:
                if i == retries - 1:
                    print(f"BŁĄD przy wysyłaniu pliku: {e.response['error']}")
                    raise
                time.sleep(2 ** i)
