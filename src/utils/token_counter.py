def count_tokens(text: str) -> int:
    """Very rough token estimator (word count)."""
    return len(text.split()) 