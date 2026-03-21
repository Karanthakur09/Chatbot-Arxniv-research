import re
from collections import Counter


def tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def keyword_score(query: str, content: str):

    query_tokens = tokenize(query)
    content_tokens = tokenize(content)

    if not content_tokens:
        return 0.0

    content_freq = Counter(content_tokens)

    score = 0.0

    for token in query_tokens:
        score += content_freq.get(token, 0)

    return score / len(content_tokens)