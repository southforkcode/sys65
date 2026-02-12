

def str_compare(a: str, b: str, casei: bool) -> bool:
  if casei:
    return a.lower() == b.lower()
  return a == b
