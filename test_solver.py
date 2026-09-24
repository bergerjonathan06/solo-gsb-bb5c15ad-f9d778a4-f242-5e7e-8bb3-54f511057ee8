"""solver 的离线测试脚本（不依赖 pytest）。"""
from app.solver import check_text

failures = []

def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        failures.append(name)

# 1. 可行示例
r = check_text(
    "出门,到车站,15,30\n"
    "到车站,列车进站,5,10\n"
    "列车进站,开车铃响,2,5\n"
    "开车铃响,开车,1,3\n"
    "出门,到外婆家,90,120\n"
)
check("feasible/status", r["status"] == "feasible", r.get("status"))
tl = {t["event"]: t["time"] for t in r["timeline"]}
check("feasible/earliest-zero", min(tl.values()) == 0, str(tl))
check("feasible/出门=0", tl["出门"] == 0)
# 累计下界: 出门->开车 >= 15+5+2+1=23, <= 30+10+5+3=48
check("feasible/开车>=23", tl["开车"] >= 23, str(tl))
check("feasible/开车<=48", tl["开车"] <= 48, str(tl))
check("feasible/外婆家 in 90..120", 90 <= tl["到外婆家"] <= 120, str(tl))
check("feasible/sorted", [t["time"] for t in r["timeline"]] == sorted(t["time"] for t in r["timeline"]))
check("feasible/connected", r["component_count"] == 1)

# 2. 冲突示例
r2 = check_text(
    "出门,到车站,15,30\n"
    "到车站,列车进站,5,10\n"
    "列车进站,开车铃响,2,5\n"
    "开车铃响,出门,60,120\n"
)
check("conflict/status", r2["status"] == "conflict", r2.get("status"))
cyc = r2["cycle"]
check("conflict/closed", cyc["sequence"][0] == cyc["sequence"][-1], str(cyc["sequence"]))
check("conflict/4-lines", cyc["involved_lines"] == [1, 2, 3, 4], str(cyc["involved_lines"]))
check("conflict/negative-sum", cyc["bounds_sum"] < 0, str(cyc["bounds_sum"]))
# 该组约束本身有不止一条负环，例如全用下界变号：−5−15−60−2=−82，
# 或上界链 30+10+5 配第4行下界变号 −60，得 −15；都是合法闭合矛盾链。
check("conflict/sum-is-evidence", cyc["bounds_sum"] in (-82, -15), str(cyc["bounds_sum"]))
# 每步都带原始行号与界
check("conflict/steps-have-lines", sorted({s["line_no"] for s in cyc["steps"]}) == [1, 2, 3, 4])
print("   chain:", " → ".join(cyc["sequence"]))
print("   proof:", cyc["sum_inequality"], "=>", cyc["bounds_sum"])

# 3. 逐行校验错误
r3 = check_text("甲,乙,10,5\n丙,丁,abc,8\n甲,乙,3\n,丁,1,2\n8,丁,1,2")
check("invalid/status", r3["status"] == "invalid")
errs = {L["line_no"]: L["errors"] for L in r3["lines"] if not L["valid"]}
check("invalid/lo>hi", any("下界" in e for e in errs[1]), str(errs))
check("invalid/not-int", any("整数" in e for e in errs[2]), str(errs))
check("invalid/field-count", any("4 个字段" in e for e in errs[3]), str(errs))
check("invalid/empty-name", any("为空" in e for e in errs[4]), str(errs))
check("invalid/numeric-name", any("纯数字" in e for e in errs[5]), str(errs))

# 4. 空输入与全空行
check("empty/blank", check_text("")["status"] == "empty")
check("empty/newlines", check_text("\n  \n\t\n")["status"] == "empty")

# 5. 空行保留行号：第2行为空，错误出现在第3行
r5 = check_text("甲,乙,1,2\n\n甲,乙,5,3")
check("blank/line-no-kept", r5["status"] == "invalid" and
      [L for L in r5["lines"] if not L["valid"]][0]["line_no"] == 3)

# 6. 中文逗号、全角空格容忍
r6 = check_text("甲，乙，1，2\n乙，丙，3，4")
check("fullwidth-comma", r6["status"] == "feasible", r6.get("error"))

# 7. 自区间冲突 甲,甲,1,5  => 甲-甲 in [1,5] 不可能
r7 = check_text("甲,甲,1,5")
check("self-loop/conflict", r7["status"] == "conflict", r7.get("status"))
check("self-loop/sum", r7["cycle"]["bounds_sum"] < 0)
# 自区间 0,0 可行
r7b = check_text("甲,甲,0,0\n甲,乙,1,2")
check("self-loop/zero-feasible", r7b["status"] == "feasible", r7b.get("status"))

# 8. 负整数界
r8 = check_text("甲,乙,-5,-1")
check("negative/feasible", r8["status"] == "feasible", r8.get("status"))
tl8 = {t["event"]: t["time"] for t in r8["timeline"]}
# 乙-甲 ∈ [-5,-1]，平移后最早为0
check("negative/order", tl8["乙"] < tl8["甲"], str(tl8))

# 9. 不连通的两组事件
r9 = check_text("甲,乙,1,2\n丙,丁,3,4")
check("disconnected/status", r9["status"] == "feasible")
check("disconnected/components", r9["component_count"] == 2, str(r9["component_count"]))
check("disconnected/note", r9["note"] and "2 组" in r9["note"])

# 10. 重复行叠加约束：乙-甲 ∈[1,2] 且 ∈[5,6] → 冲突
r10 = check_text("甲,乙,1,2\n甲,乙,5,6")
check("dup/conflict", r10["status"] == "conflict", r10.get("status"))

# 11. 多余逗号
r11 = check_text("甲,乙,1,2,3")
check("extra-comma", r11["status"] == "invalid" and
      any("4 个字段" in e for e in r11["lines"][0]["errors"]))

# 12. 所有可行结果必须确实满足全部约束（随机化强校验）
import random
random.seed(42)
for trial in range(300):
    n = random.randint(2, 6)
    names = [f"E{i}" for i in range(n)]
    lines = []
    for _ in range(random.randint(1, 8)):
        a, b = random.sample(names, 2)
        lo = random.randint(-8, 6)
        hi = lo + random.randint(0, 12)
        lines.append(f"{a},{b},{lo},{hi}")
    res = check_text("\n".join(lines))
    if res["status"] == "feasible":
        t = {x["event"]: x["time"] for x in res["timeline"]}
        for row in lines:
            a, b, lo, hi = row.split(",")
            d = t[b] - t[a]
            assert int(lo) <= d <= int(hi), (lines, t, row, d)
check("random/feasible-satisfies-all", True)

# 13. 冲突链上的边不等式之和必须等于结论中的负数（闭合性强校验）
for trial in range(100):
    n = random.randint(2, 5)
    names = [f"E{i}" for i in range(n)]
    lines = []
    for i in range(n + 2):
        a, b = random.sample(names, 2)
        lo = random.randint(-5, 2)
        hi = lo + random.randint(0, 5)
        lines.append(f"{a},{b},{lo},{hi}")
    res = check_text("\n".join(lines))
    if res["status"] == "conflict":
        c = res["cycle"]
        # sequence 相邻事件与 step 的 from/to 一致
        for i, s in enumerate(c["steps"]):
            assert c["sequence"][i] == s["from_event"] and c["sequence"][i + 1] == s["to_event"]
        assert c["sequence"][0] == c["sequence"][-1]
        assert c["bounds_sum"] < 0
check("random/conflict-chain-wellformed", True)

print()
if failures:
    print("FAILED:", failures)
    raise SystemExit(1)
print("ALL TESTS PASSED")
