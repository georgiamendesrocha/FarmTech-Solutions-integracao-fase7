"""Contrato pequeno, independente de Streamlit e das bibliotecas de cada fase."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Result:
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "Result":
        if (not isinstance(value, dict)
                or value.get("status") not in {"ok", "invalid", "unavailable", "error"}
                or not isinstance(value.get("message"), str)
                or len(value["message"]) > 4000
                or not isinstance(value.get("data", {}), dict)
                or not isinstance(value.get("source", {}), dict)):
            raise ValueError("Resposta de serviço inválida.")
        return cls(value["status"], value["message"], value.get("data", {}), value.get("source", {}))
