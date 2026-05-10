from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.kind:<12} {self.value:<12} (line {self.line}, col {self.column})"
