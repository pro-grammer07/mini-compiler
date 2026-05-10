def _is_leaf(value):
    return isinstance(value, (str, int, float, bool)) or value is None


def _label_for(node):
    if not hasattr(node, "__dict__"):
        return repr(node)
    cls = node.__class__.__name__
    leaf_parts = []
    for k, v in node.__dict__.items():
        if _is_leaf(v):
            leaf_parts.append(f"{k}={v!r}")
    if leaf_parts:
        return f"{cls} [{', '.join(leaf_parts)}]"
    return cls


def dump(node, prefix="", is_last=True):
    if prefix == "":
        connector = ""
    else:
        connector = "`-- " if is_last else "|-- "

    if node is None:
        return f"{prefix}{connector}None"

    if isinstance(node, list):
        lines = [f"{prefix}{connector}List[{len(node)}]"]
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, item in enumerate(node):
            lines.append(dump(item, child_prefix, i == len(node) - 1))
        return "\n".join(lines)

    if not hasattr(node, "__dict__"):
        return f"{prefix}{connector}{repr(node)}"

    lines = [f"{prefix}{connector}{_label_for(node)}"]
    complex_items = [(k, v) for k, v in node.__dict__.items() if not _is_leaf(v)]
    child_prefix = prefix + ("    " if is_last else "|   ")

    for idx, (field, value) in enumerate(complex_items):
        field_is_last = idx == len(complex_items) - 1
        field_connector = "`-- " if field_is_last else "|-- "
        lines.append(f"{child_prefix}{field_connector}{field}")
        nested_prefix = child_prefix + ("    " if field_is_last else "|   ")

        if isinstance(value, list):
            lines.append(f"{nested_prefix}`-- List[{len(value)}]")
            list_prefix = nested_prefix + "    "
            for i, item in enumerate(value):
                lines.append(dump(item, list_prefix, i == len(value) - 1))
        else:
            lines.append(dump(value, nested_prefix, True))

    return "\n".join(lines)
