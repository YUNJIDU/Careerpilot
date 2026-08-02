import argparse
import getpass
import os
import re
from pathlib import Path
from typing import ClassVar, Protocol

import keyring


class SecretStore(Protocol):
    writable: bool

    def get(self, account_id: str, email: str) -> str | None: ...

    def set(self, account_id: str, email: str, value: str) -> None: ...

    def get_named(self, name: str) -> str | None: ...

    def set_named(self, name: str, value: str) -> None: ...

    def delete_named(self, name: str) -> None: ...


class WindowsSecretStore:
    prefix = "CareerPilot/mail/163"
    writable = True

    def get(self, account_id: str, email: str) -> str | None:
        return keyring.get_password(f"{self.prefix}/{account_id}", email)

    def set(self, account_id: str, email: str, value: str) -> None:
        keyring.set_password(f"{self.prefix}/{account_id}", email, value)

    def get_named(self, name: str) -> str | None:
        return keyring.get_password(f"CareerPilot/{name}", "credential")

    def set_named(self, name: str, value: str) -> None:
        keyring.set_password(f"CareerPilot/{name}", "credential", value)

    def delete_named(self, name: str) -> None:
        try:
            keyring.delete_password(f"CareerPilot/{name}", "credential")
        except keyring.errors.PasswordDeleteError:
            pass


class EnvironmentSecretStore:
    writable = False
    names: ClassVar[dict[str, str]] = {
        "mail": "CAREERPILOT_MAIL_SECRET",
        "model": "CAREERPILOT_MODEL_SECRET",
        "tavily": "CAREERPILOT_TAVILY_SECRET",
    }

    @staticmethod
    def _read(name: str) -> str | None:
        file_name = os.getenv(f"{name}_FILE")
        if file_name:
            value = Path(file_name).read_text(encoding="utf-8")
        else:
            value = os.getenv(name, "")
        return value.strip() or None

    def get(self, account_id: str, email: str) -> str | None:
        account_key = re.sub(r"[^A-Za-z0-9]", "_", account_id).upper()
        scoped = self._read(f"CAREERPILOT_MAIL_SECRET_{account_key}")
        legacy_account = os.getenv("CAREERPILOT_MAIL_ACCOUNT_ID", "personal")
        if scoped or account_id != legacy_account:
            return scoped
        return self._read(self.names["mail"])

    def set(self, account_id: str, email: str, value: str) -> None:
        raise RuntimeError("runtime-injected secrets are read-only")

    def get_named(self, name: str) -> str | None:
        variable = self.names.get(name)
        if not variable:
            suffix = re.sub(r"[^A-Za-z0-9]", "_", name).upper()
            variable = f"CAREERPILOT_SECRET_{suffix}"
        return self._read(variable)

    def set_named(self, name: str, value: str) -> None:
        raise RuntimeError("runtime-injected secrets are read-only")

    def delete_named(self, name: str) -> None:
        raise RuntimeError("runtime-injected secrets are read-only")


def default_secret_store() -> SecretStore:
    return WindowsSecretStore() if os.name == "nt" else EnvironmentSecretStore()


def main() -> None:
    parser = argparse.ArgumentParser(description="Store a 163 client authorization code")
    parser.add_argument("account_id")
    parser.add_argument("email")
    args = parser.parse_args()
    secret = getpass.getpass("163 client authorization code: ")
    if not secret:
        raise SystemExit("authorization code cannot be empty")
    WindowsSecretStore().set(args.account_id, args.email, secret)
    print(f"Stored credential for account {args.account_id}.")


if __name__ == "__main__":
    main()
