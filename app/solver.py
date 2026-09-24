"""事件时间区间的联立求解。

输入的每一行形如

    事件甲,事件乙,最少分钟,最多分钟

表示  最少分钟 ≤ 事件乙 − 事件甲 ≤ 最多分钟。

这是一组差分约束。把每个事件看成一个节点：

* 由上界  事件乙 − 事件甲 ≤ 最多分钟   得到边  甲 → 乙，权 = 最多分钟
* 由下界  事件乙 − 事件甲 ≥ 最少分钟
       即 事件甲 − 事件乙 ≤ −最少分钟   得到边  乙 → 甲，权 = −最少分钟

加入一个到所有节点距离都为 0 的虚拟源点后做 Bellman-Ford：

* 不存在负环 → 约束系统可行；各节点到虚拟源点的最短距离平移
  （令最早事件为 0）即得到满足全部区间的可行时间线；
* 存在负环 → 环上各边右侧权值之和为负数，即 0 ≤ 负数，构成闭合矛盾链，
  沿前驱指针还原环上的边，即可给出由原始行号与上下界组成的证据。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_INT_RE = re.compile(r"^[+-]?\d+$")


@dataclass
class Edge:
    u: int          # 起点（事件下标）
    v: int          # 终点（事件下标）
    w: int          # 边权 = 该边右侧的上界
    line_no: int    # 原始行号（从 1 开始，空行也占位）
    raw: str        # 原始行文本
    kind: str       # "hi"=取上界 | "lo"=由下界变号
    bound: int      # 该行原始用到的界（最多分钟 / 最少分钟）
    a: str          # 原始行中的事件甲
    b: str          # 原始行中的事件乙


def _fmt(value: int) -> str:
    """把整数格式化成展示字符串，负号用 Unicode 减号。"""
    return str(value).replace("-", "−")


def _parse_int(token: str):
    if _INT_RE.match(token):
        return int(token)
    return None


def _parse_lines(raw_text: str):
    """逐行解析，返回 (行记录, 有效约束)。

    空行跳过但保留原始行号；半角逗号与中文逗号都接受。
    """
    records = []
    constraints = []

    for line_no, raw in enumerate(raw_text.splitlines(), start=1):
        if not raw.strip():
            continue

        normalized = raw.replace("，", ",")
        parts = [p.strip() for p in normalized.split(",")]
        record = {"line_no": line_no, "raw": raw, "valid": False, "errors": []}

        if len(parts) != 4:
            record["errors"].append(
                f"应为 4 个字段“事件甲,事件乙,最少分钟,最多分钟”，实际有 {len(parts)} 个字段"
            )
            records.append(record)
            continue

        a, b, lo_token, hi_token = parts
        if not a:
            record["errors"].append("事件甲名称为空")
        elif _INT_RE.match(a):
            record["errors"].append("事件甲名称不能是纯数字")
        if not b:
            record["errors"].append("事件乙名称为空")
        elif _INT_RE.match(b):
            record["errors"].append("事件乙名称不能是纯数字")
        if a and b and a == b and not record["errors"]:
            # 自区间也允许，交给求解器按 [lo, hi] 判定；此处不报错
            pass

        lo = _parse_int(lo_token)
        if lo is None:
            record["errors"].append(f"“{lo_token}”不是整数分钟（最少分钟）")
        hi = _parse_int(hi_token)
        if hi is None:
            record["errors"].append(f"“{hi_token}”不是整数分钟（最多分钟）")

        if lo is not None and hi is not None and lo > hi:
            record["errors"].append(f"下界 {_fmt(lo)} 大于上界 {_fmt(hi)}，该区间不可能成立")

        records.append(record)
        if not record["errors"]:
            record["valid"] = True
            constraints.append((a, b, lo, hi, line_no, raw))

    return records, constraints


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry


def _bellman_ford(edges, n: int):
    """以到各点距离为 0 的虚拟源点初始化，跑 n 轮松弛。

    返回 (负环边序列或 None, 各点最短距离上界)。
    """
    dist = [0] * n
    pred = [None] * n  # pred[v] = (u, edge)
    last = -1

    for _ in range(n):
        changed = False
        for e in edges:
            candidate = dist[e.u] + e.w
            if candidate < dist[e.v]:
                dist[e.v] = candidate
                pred[e.v] = (e.u, e)
                changed = True
                last = e.v
        if not changed:
            return None, dist

    # 第 n 轮仍可松弛 → 存在负环；沿前驱先走 n 步落到环上
    x = last
    for _ in range(n):
        x = pred[x][0]

    order = []
    seen = set()
    y = x
    while y not in seen:
        seen.add(y)
        order.append(y)
        y = pred[y][0]
    order.reverse()  # 翻转后相邻节点之间正是 pred 记录的边

    cycle_edges = []
    for i in range(len(order)):
        v_node = order[(i + 1) % len(order)]
        u_node, edge = pred[v_node]
        if u_node != order[i]:
            # 理论上不会发生，防御性地退回到简单的边集合
            cycle_edges = [pred[node][1] for node in order]
            break
        cycle_edges.append(edge)
    return cycle_edges, dist


def _build_cycle(cycle_edges):
    steps = []
    sequence = []
    for e in cycle_edges:
        if e.kind == "hi":
            frm, to = e.a, e.b
            kind_label = "上界"
            used_bound = e.w  # = hi
            derived = f"{_fmt(e.bound)}"
        else:
            frm, to = e.b, e.a
            kind_label = "下界"
            used_bound = e.w  # = −lo
            derived = f"−{_fmt(e.bound)}（下界 {_fmt(e.bound)} 变号）"

        expr = f"{frm} − {to}"
        steps.append(
            {
                "line_no": e.line_no,
                "raw": e.raw,
                "kind": kind_label,
                "original_bound": e.bound,
                "derived": derived,
                "from_event": frm,
                "to_event": to,
                "expr": expr,
                "inequality": f"{expr} ≤ {_fmt(used_bound)}",
            }
        )
        if not sequence:
            sequence.append(frm)
        sequence.append(to)

    total = sum(e.w for e in cycle_edges)
    left_terms = " + ".join(f"（{s['expr']}）" for s in steps)

    def _term(w: int) -> str:
        # 负权项加括号，避免出现 “+ −15” 这种排版
        return f"（{_fmt(w)}）" if w < 0 else _fmt(w)

    right_terms = " + ".join(_term(e.w) for e in cycle_edges)
    return {
        "sequence": sequence,  # 首尾相同，天然闭合
        "steps": steps,
        "sum_inequality": f"{left_terms} ≤ {right_terms}",
        "bounds_sum": total,
        "conclusion": (
            f"左边相加后事件两两抵消为 0，于是得到 0 ≤ {_fmt(total)}；"
            f"但 {_fmt(total)} < 0，矛盾。因此这些行不可能同时成立。"
        ),
        "involved_lines": sorted({e.line_no for e in cycle_edges}),
    }


def check_text(raw_text: str) -> dict:
    """对外的主入口：校验并联立，返回前端直接渲染的结果字典。"""
    records, constraints = _parse_lines(raw_text or "")

    if not records:
        return {
            "status": "empty",
            "error": "没有可解析的内容，请先粘贴至少一行“事件甲,事件乙,最少分钟,最多分钟”。",
            "lines": [],
        }

    if any(not r["valid"] for r in records):
        return {
            "status": "invalid",
            "error": "存在无法通过校验的行，已停止联立。请先修正下列标红的行。",
            "lines": records,
        }

    # 收集事件并建图
    names = []
    index = {}
    for a, b, *_ in constraints:
        for name in (a, b):
            if name not in index:
                index[name] = len(names)
                names.append(name)

    uf = _UnionFind(len(names))
    edges = []
    for a, b, lo, hi, line_no, raw in constraints:
        ia, ib = index[a], index[b]
        uf.union(ia, ib)
        # 事件乙 − 事件甲 ≤ hi  →  甲 → 乙，权 hi
        edges.append(Edge(ia, ib, hi, line_no, raw, "hi", hi, a, b))
        # 事件甲 − 事件乙 ≤ −lo  →  乙 → 甲，权 −lo
        edges.append(Edge(ib, ia, -lo, line_no, raw, "lo", lo, a, b))

    cycle_edges, dist = _bellman_ford(edges, len(names))

    if cycle_edges is not None:
        return {
            "status": "conflict",
            "error": "联立后存在冲突：以下各行构成一条闭合矛盾链。",
            "lines": records,
            "event_count": len(names),
            "constraint_count": len(constraints),
            "cycle": _build_cycle(cycle_edges),
        }

    earliest = min(dist)
    timeline = [
        {"event": name, "time": dist[index[name]] - earliest}
        for name in names
    ]
    timeline.sort(key=lambda item: (item["time"], item["event"]))

    component_count = len({uf.find(i) for i in range(len(names))})
    note = None
    if component_count > 1:
        note = (
            f"这些事件之间没有全部连通，共分成 {component_count} 组互不相关的事件；"
            "组与组之间没有给定时间先后，各组都已尽量早地安排（整体最早时刻为第 0 分钟）。"
        )

    return {
        "status": "feasible",
        "error": None,
        "lines": records,
        "event_count": len(names),
        "constraint_count": len(constraints),
        "timeline": timeline,
        "component_count": component_count,
        "note": note,
    }
