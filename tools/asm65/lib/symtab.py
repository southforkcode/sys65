

class SymbolTable:
  def __init__(self):
    self.symbols : dict[str, int] = {}

  def items(self):
    return self.symbols.items()

  def resolved_items(self):
    return [(name, value) for name, value in self.symbols.items() if value is not None]

  def unresolved_items(self):
    return [(name, value) for name, value in self.symbols.items() if value is None]

  def resolve(self, name: str, value: int):
    if name not in self.symbols:
      raise ValueError(f"Symbol '{name}' not defined")
    self.symbols[name] = value

  def set(self, name: str, value: int | None):
    self.symbols[name] = value

  def get(self, name: str) -> int | None:
    return self.symbols.get(name)

  def __getitem__(self, name: str) -> int | None:
    return self.get(name)

  def __contains__(self, name: str) -> bool:
    return name in self.symbols