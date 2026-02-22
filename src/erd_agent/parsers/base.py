from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from erd_agent.model import Schema

class Parser(ABC):
    @abstractmethod
    def can_parse(self, path: Path, text: str) -> bool: ...
    @abstractmethod
    def parse(self, path: Path, text: str, schema: Schema) -> None: ...