from __future__ import annotations

from app.core.errors import AppError
from app.diagnostics.policy import ObjectiveNode


def find_cycle(nodes: list[ObjectiveNode]) -> list[str] | None:
    known = {node.code for node in nodes}
    adjacency = {
        node.code: [code for code in node.prerequisite_codes if code in known]
        for node in nodes
    }
    color = {node.code: 0 for node in nodes}
    stack: list[str] = []

    def visit(code: str) -> list[str] | None:
        color[code] = 1
        stack.append(code)
        for prerequisite in adjacency[code]:
            if color[prerequisite] == 1:
                cycle = stack[stack.index(prerequisite) :]
                return cycle + [prerequisite]
            if color[prerequisite] == 0:
                found = visit(prerequisite)
                if found is not None:
                    return found
        stack.pop()
        color[code] = 2
        return None

    for code in sorted(color):
        if color[code] == 0:
            found = visit(code)
            if found is not None:
                return found
    return None


def learning_order(nodes: list[ObjectiveNode]) -> list[ObjectiveNode]:
    cycle = find_cycle(nodes)
    if cycle is not None:
        raise AppError(
            "dependency_cycle",
            "The prerequisite graph has a cycle: " + " -> ".join(cycle) + ".",
            422,
        )
    by_code = {node.code: node for node in nodes}
    dependents: dict[str, list[str]] = {node.code: [] for node in nodes}
    indegree = {node.code: 0 for node in nodes}
    for node in nodes:
        seen: set[str] = set()
        for prerequisite in node.prerequisite_codes:
            if prerequisite not in by_code or prerequisite in seen or prerequisite == node.code:
                continue
            seen.add(prerequisite)
            dependents[prerequisite].append(node.code)
            indegree[node.code] += 1
    ready = sorted((code for code, degree in indegree.items() if degree == 0), key=lambda code: (by_code[code].position, code))
    ordered: list[ObjectiveNode] = []
    while ready:
        code = ready.pop(0)
        ordered.append(by_code[code])
        unlocked: list[str] = []
        for dependent in dependents[code]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                unlocked.append(dependent)
        ready.extend(unlocked)
        ready.sort(key=lambda item: (by_code[item].position, item))
    if len(ordered) != len(nodes):
        raise AppError("dependency_cycle", "The prerequisite graph has a cycle.", 422)
    return ordered
