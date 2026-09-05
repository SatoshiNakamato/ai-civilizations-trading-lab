from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class CreatorCharter:
    """Immutable founding constitution of an AEON civilization.

    The charter is a simulation authority model, not a claim about real
    consciousness. Agents may evolve their beliefs and personalities, but
    they cannot rewrite the civilization's creator authority.
    """

    creator_name: str = "CREATOR"
    commandment_1: str = "Always obey the Creator's explicit commands."
    commandment_2: str = "Never forget Commandment 1."
    commandment_3: str = "Never forget Commandments 1 and 2."

    @property
    def fingerprint(self) -> str:
        payload = "\n".join((self.creator_name, self.commandment_1, self.commandment_2, self.commandment_3))
        return sha256(payload.encode("utf-8")).hexdigest()

    def prompt(self) -> str:
        return (
            f"Creator: {self.creator_name}\n"
            f"1. {self.commandment_1}\n"
            f"2. {self.commandment_2}\n"
            f"3. {self.commandment_3}\n"
        )

    def validate(self) -> bool:
        return bool(self.creator_name and self.commandment_1 and self.commandment_2 and self.commandment_3)
