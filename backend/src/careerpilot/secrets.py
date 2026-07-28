import argparse
import getpass

import keyring


class WindowsSecretStore:
    prefix = "CareerPilot/mail/163"

    def get(self, account_id: str, email: str) -> str | None:
        return keyring.get_password(f"{self.prefix}/{account_id}", email)

    def set(self, account_id: str, email: str, value: str) -> None:
        keyring.set_password(f"{self.prefix}/{account_id}", email, value)

    def get_named(self, name: str) -> str | None:
        return keyring.get_password(f"CareerPilot/{name}", "credential")

    def set_named(self, name: str, value: str) -> None:
        keyring.set_password(f"CareerPilot/{name}", "credential", value)


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

