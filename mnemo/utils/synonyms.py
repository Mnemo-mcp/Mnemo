"""Developer-focused synonym expansion for search enhancement."""

from __future__ import annotations

SYNONYM_GROUPS: list[set[str]] = [
    {"auth", "authentication", "authn", "login"},
    {"authorization", "authz", "rbac", "permissions"},
    {"db", "database", "datastore"},
    {"k8s", "kubernetes", "kube"},
    {"ci", "pipeline", "continuous-integration"},
    {"api", "endpoint", "rest"},
    {"test", "testing", "tests", "spec"},
    {"deploy", "deployment", "deploying"},
    {"cache", "caching", "cached"},
    {"config", "configuration", "setup"},
    {"deps", "dependencies", "dependency"},
    {"perf", "performance", "latency"},
    {"monitor", "monitoring", "observability"},
    {"validate", "validation"},
    {"migrate", "migration"},
    {"container", "docker", "containerization"},
    {"repo", "repository"},
    {"env", "environment"},
    {"log", "logging", "logs"},
    {"err", "error", "exception"},
    {"msg", "message", "messaging"},
    {"encrypt", "encryption", "crypto"},
    {"queue", "pubsub", "event-bus"},
    {"infra", "infrastructure"},
    {"svc", "service", "microservice"},
    {"pkg", "package", "module"},
    {"fn", "function", "lambda"},
    {"var", "variable", "param"},
    {"async", "asynchronous", "concurrent"},
    {"sync", "synchronous", "blocking"},
    {"lint", "linter", "static-analysis"},
    {"debug", "debugging", "troubleshoot"},
]

_INDEX: dict[str, set[str]] = {}
for _group in SYNONYM_GROUPS:
    for _term in _group:
        _INDEX[_term] = _group


def get_synonym_group(term: str) -> set[str] | None:
    """Look up the synonym group for a term."""

    return _INDEX.get(term.lower())


def expand_synonyms(terms: list[str]) -> list[tuple[str, float]]:
    """Expand terms with synonyms. Returns (term, weight) pairs: 1.0 original, 0.7 synonyms."""
    result: list[tuple[str, float]] = []
    seen: set[str] = set()
    for t in terms:
        low = t.lower()
        if low not in seen:
            seen.add(low)
            result.append((low, 1.0))
        group = _INDEX.get(low)
        if group:
            for syn in group:
                if syn not in seen:
                    seen.add(syn)
                    result.append((syn, 0.7))
    return result
