"""
Moduł secrets: uniwersalny menedżer tajemnic (env/aws/gcp/vault).
"""
import json
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SecretSpec:
    """Specyfikacja sekretu."""
    name: str
    required: bool = True


class Secrets:
    """Menedżer tajemnic z różnymi backendami."""

    def __init__(self, backend: Optional[str] = None):
        """
        Inicjalizacja.

        Args:
            backend: Backend ('env', 'aws', 'gcp', 'vault') lub None (auto z ENV)
        """
        self.backend = (backend or os.environ.get("SECRETS_BACKEND", "env")).lower()

    def get(self, key: str) -> Optional[str]:
        """
        Pobiera sekret.

        Args:
            key: Klucz sekretu

        Returns:
            Wartość lub None
        """
        if self.backend == "env":
            return os.environ.get(key)

        if self.backend == "aws":
            try:
                import boto3
                arn = os.environ.get("AWS_SECRET_ARN")
                if not arn:
                    return None
                val = boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]
                return json.loads(val).get(key)
            except Exception as e:
                print(f"⚠️  AWS secrets error: {e}")
                return None

        if self.backend == "gcp":
            try:
                from google.cloud import secretmanager
                name = os.environ.get("GCP_SECRET_NAME")
                if not name:
                    return None
                client = secretmanager.SecretManagerServiceClient()
                resp = client.access_secret_version(request={"name": name})
                val = resp.payload.data.decode("UTF-8")
                return json.loads(val).get(key)
            except Exception as e:
                print(f"⚠️  GCP secrets error: {e}")
                return None

        if self.backend == "vault":
            try:
                import hvac
                url = os.environ.get("VAULT_ADDR")
                token = os.environ.get("VAULT_TOKEN")
                path = os.environ.get("VAULT_PATH", "secret/data/alpha")
                if not url or not token:
                    return None
                cli = hvac.Client(url=url, token=token)
                val = cli.secrets.kv.v2.read_secret_version(path=path)["data"]["data"]
                return val.get(key)
            except Exception as e:
                print(f"⚠️  Vault error: {e}")
                return None

        return None

    def validate(self, specs: List[SecretSpec]) -> List[str]:
        """
        Waliduje wymagane sekrety.

        Args:
            specs: Lista specyfikacji sekretów

        Returns:
            Lista brakujących sekretów
        """
        missing = []
        for spec in specs:
            if spec.required and not self.get(spec.name):
                missing.append(spec.name)
        return missing
