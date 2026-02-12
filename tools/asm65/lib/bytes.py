

class ByteConverter:

  @staticmethod
  def convert_int(value: int, size: int) -> bytes:
    if size == 1:
      return bytes([value & 0xFF])
    elif size == 2:
      # big endian
      return bytes([(value >> 8) & 0xFF, value & 0xFF])
    else:
      raise ValueError(f"Invalid size: {size}")

  @staticmethod
  def convert_str(value: str) -> bytes:
    return bytes(value, 'utf-8')
  