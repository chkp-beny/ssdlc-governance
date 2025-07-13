import collections.abc
from typing import Any, Set


def serialize_recursive(obj: Any, _visited: Set[int] = None) -> Any:
    """
    Recursively serialize an object to a JSON-serializable structure (dict, list, primitives).
    Handles nested custom objects, lists, dicts, and cycle detection.
    Args:
        obj: The object to serialize.
        _visited: Set of object ids already visited (for cycle detection).
    Returns:
        A JSON-serializable representation of the object.
    """

    # Primitives (do NOT add to _visited, avoids false cycle detection for bool/int/str/float/None)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if _visited is None:
        _visited = set()

    # Cycle detection (for non-primitives only)
    obj_id = id(obj)
    if obj_id in _visited:
        return f"<cycle: {type(obj).__name__}>"
    _visited.add(obj_id)

    # List, tuple, set
    if isinstance(obj, (list, tuple, set)):
        return [serialize_recursive(item, _visited) for item in obj]

    # Dict
    if isinstance(obj, dict):
        return {str(k): serialize_recursive(v, _visited) for k, v in obj.items()}

    # Namedtuple
    if isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return {field: serialize_recursive(getattr(obj, field), _visited) for field in obj._fields}

    # Custom class (has __dict__ or __slots__)
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue  # skip private/protected/internal
            result[key] = serialize_recursive(value, _visited)
        return result
    if hasattr(obj, '__slots__'):
        result = {}
        for key in obj.__slots__:
            value = getattr(obj, key, None)
            result[key] = serialize_recursive(value, _visited)
        return result

    # Fallback: string representation
    return str(obj)
