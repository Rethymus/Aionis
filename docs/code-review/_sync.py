"""Sync progress.json + SUMMARY.md from written reports (+ result JSONs for skipped).

Usage: python docs/code-review/_sync.py
Primary source: docs/code-review/commits/<hash>.md (parsed).
Secondary: docs/code-review/_results_batch_*.jsonl (only fills skipped entries lacking a file).
Writes: docs/code-review/progress.json, docs/code-review/SUMMARY.md
"""
import glob
import json
import os
import re
import subprocess
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
COMMITS_DIR = os.path.join(BASE, "commits")

MODULE_ALIASES = {
    "ingest": "ingest", "features": "features", "eval": "eval", "extraction": "extraction",
    "reporting": "reporting", "scripts": "scripts", "dashboard": "dashboard", "web": "web",
    "display": "display", "workers": "workers", "worker": "workers", "site": "site",
    "ci": "ci", "docs": "docs", "data": "data", "tests": "tests", "build": "build",
    "calibration": "display", "manuscript": "docs", "factors": "features",
    "prereg": "docs", "research": "docs", "state": "docs", "decisions": "docs",
    "tasks": "docs", "design": "docs", "audit": "docs", "survey": "docs",
    "cot": "ingest", "form4": "ingest", "smart-money": "ingest", "market": "web",
    "themes": "web", "overview": "web", "export": "scripts", "infra": "workers",
    "frontier": "docs", "draft": "docs", "positioning": "docs", "strengthening": "docs",
    "brief": "docs", "readme": "docs", "workflow": "docs", "results": "docs",
}

PATH_MODULE = [
    ("src/aionis/ingest/", "ingest"), ("src/aionis/features/", "features"),
    ("src/aionis/eval/", "eval"), ("src/aionis/extraction/", "extraction"),
    ("src/aionis/reporting/", "reporting"), ("src/aionis/", "other"),
    ("scripts/", "scripts"), ("dashboard/", "dashboard"), ("web/", "web"),
    ("workers/", "workers"), (".github/", "ci"), ("tests/", "tests"),
    ("docs/", "docs"), ("reports/", "docs"), ("decisions/", "docs"),
    ("tasks/", "docs"), ("state/", "docs"), ("evals/", "docs"),
    ("site/", "site"), ("quarto/", "docs"), ("manuscript/", "docs"),
]


def load_order():
    out = []
    with open(os.path.join(BASE, "_batches.json"), encoding="utf-8") as f:
        batches = json.load(f)
    for k in sorted(batches):
        out.extend(batches[k])
    return out


def load_json_results():
    per_hash = {}
    for p in sorted(glob.glob(os.path.join(BASE, "_results_*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            txt = f.read().strip()
        if not txt:
            continue
        try:
            data = json.loads(txt)
            if isinstance(data, dict):
                data = [data]
        except json.JSONDecodeError:
            data = []
            for line in txt.splitlines():
                line = line.strip().rstrip(",")
                if not line or line in "[]":
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        for e in data:
            if isinstance(e, dict) and "hash" in e:
                per_hash[e["hash"]] = e
    return per_hash


ISSUE_RE = re.compile(r"^###\s+(P[0-3])(?:[-–]\d+)?[.:：\s]+(.+?)\s*$", re.M)
FIXED_RE = re.compile(r"已在\s*`?([0-9a-f]{8,40})`?\s*修复")
SCORE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*/\s*10")


def parse_report(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    head = txt[:600]
    if "跳过" in head and len(txt) < 1200:
        return {"status": "skipped", "reason": head.strip()[:200]}
    headers = list(ISSUE_RE.finditer(txt))
    issues = []
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(txt)
        block = txt[start:end]
        fixed = FIXED_RE.search(block)
        loc = re.search(r"位置[：:]\s*`?([^`\n]+)", block)
        issues.append({"level": m.group(1), "title": m.group(2).strip(),
                       "file": loc.group(1) if loc else "", "fixed": fixed.group(1) if fixed else None})
    sm = SCORE_RE.search(txt)
    score = float(sm.group(1)) if sm else None
    return {"status": "done", "score": score, "issues": issues}


def infer_module(commit, json_entry):
    subj = commit["subject"]
    m = re.match(r"^[a-z]+\(([^)]+)\)", subj)
    if m:
        scope = m.group(1).strip().lower()
        if scope in MODULE_ALIASES:
            return MODULE_ALIASES[scope]
    if json_entry and json_entry.get("module"):
        return json_entry["module"]
    try:
        out = subprocess.run(["git", "show", "--name-only", "--format=", commit["hash"]],
                             capture_output=True, text=True, encoding="utf-8").stdout
    except Exception:
        return "other"
    counts = defaultdict(int)
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix, mod in PATH_MODULE:
            if line.startswith(prefix):
                counts[mod] += 1
                break
        else:
            counts["other"] += 1
    return max(counts, key=counts.get) if counts else "other"


def main():
    order = load_order()
    json_res = load_json_results()
    tally = {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "fixed_later": 0}
    mod_stats = defaultdict(lambda: {"commits": 0, "skipped": 0, "p0": 0, "p1": 0, "p2": 0, "p3": 0,
                                     "score_sum": 0.0, "score_n": 0})
    done, skipped, pending, sev_list = [], [], [], []
    missing_detail = []

    for c in order:
        h = c["hash"]
        path = os.path.join(COMMITS_DIR, h + ".md")
        je = json_res.get(h)
        if os.path.exists(path):
            parsed = parse_report(path)
            if parsed["status"] == "skipped":
                entry = {"hash": h, "date": c["date"], "subject": c["subject"],
                         "module": infer_module(c, je), "score": None,
                         "p0": 0, "p1": 0, "p2": 0, "p3": 0, "fixed_later": 0}
                skipped.append({**entry, "reason": parsed.get("reason", "")})
                mod_stats[entry["module"]]["skipped"] += 1
            else:
                lv = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
                fixed_n = 0
                for iss in parsed["issues"]:
                    if iss["fixed"]:
                        fixed_n += 1
                    else:
                        lv[iss["level"]] += 1
                entry = {"hash": h, "date": c["date"], "subject": c["subject"],
                         "module": infer_module(c, je), "score": parsed["score"],
                         "p0": lv["P0"], "p1": lv["P1"], "p2": lv["P2"], "p3": lv["P3"],
                         "fixed_later": fixed_n}
                done.append(entry)
                for k in ("p0", "p1", "p2", "p3", "fixed_later"):
                    tally[k] += entry[k]
                m = mod_stats[entry["module"]]
                m["commits"] += 1
                for k in ("p0", "p1", "p2", "p3"):
                    m[k] += entry[k]
                if entry["score"] is not None:
                    m["score_sum"] += entry["score"]
                    m["score_n"] += 1
                for iss in parsed["issues"]:
                    if iss["level"] in ("P0", "P1") and not iss["fixed"]:
                        sev_list.append((iss["level"], h[:8], iss["title"], iss.get("file", "")))
        elif je and je.get("status") == "skipped":
            entry = {"hash": h, "date": c["date"], "subject": c["subject"],
                     "module": je.get("module") or infer_module(c, je),
                     "score": None, "p0": 0, "p1": 0, "p2": 0, "p3": 0, "fixed_later": 0}
            skipped.append({**entry, "reason": je.get("skip_reason", "")})
            mod_stats[entry["module"]]["skipped"] += 1
        elif je and je.get("status") == "done":
            missing_detail.append(h)  # claimed done but no report -> needs re-review
            pending.append(h)
        else:
            pending.append(h)

    prog = {"meta": {"created": "2026-08-20", "total": len(order),
                     "note": "逐 commit 审查进度。完成标记 = docs/code-review/commits/<hash>.md 已写入（skipped 可仅有 JSON 记录）；由 _sync.py 同步。"},
            "pending": pending, "done": done, "skipped": skipped,
            "claimed_done_without_report": missing_detail}
    with open(os.path.join(BASE, "progress.json"), "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=1)

    scores = [d["score"] for d in done if isinstance(d.get("score"), (int, float))]
    avg = round(sum(scores) / len(scores), 2) if scores else None
    lines = []
    lines.append("# Aionis 全历史代码审查汇总（SUMMARY）")
    lines.append("")
    lines.append(f"- 进度：**{len(done) + len(skipped)} / {len(order)}**（已审 {len(done)}，跳过 {len(skipped)}，待审 {len(pending)}）")
    lines.append(f"- 有效问题（不含已在后续 commit 修复）：**P0={tally['p0']}，P1={tally['p1']}，P2={tally['p2']}，P3={tally['p3']}**；另已在后续 commit 修复 {tally['fixed_later']} 条")
    if avg is not None:
        lines.append(f"- 平均评分：{avg}/10（{len(scores)} 个已评分 commit）")
    lines.append("")
    lines.append("## 按模块分布")
    lines.append("")
    lines.append("| 模块 | 已审 | 跳过 | P0 | P1 | P2 | P3 | 均分 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for m, s in sorted(mod_stats.items(), key=lambda kv: -(kv[1]["p0"] * 1000 + kv[1]["p1"] * 100 + kv[1]["p2"] * 10 + kv[1]["commits"])):
        if s["commits"] == 0 and s["skipped"] == 0:
            continue
        avgm = round(s["score_sum"] / s["score_n"], 1) if s["score_n"] else "-"
        lines.append(f"| {m} | {s['commits']} | {s['skipped']} | {s['p0']} | {s['p1']} | {s['p2']} | {s['p3']} | {avgm} |")
    lines.append("")
    lines.append("## 严重问题清单（P0/P1，未修复，详见各 commit 报告）")
    lines.append("")
    if not sev_list:
        lines.append("（暂无）")
    for lvl, h, title, file in sev_list:
        lines.append(f"- **{lvl}** `{h}` {title}（{file}）")
    lines.append("")
    lines.append("_由 _sync.py 生成；单 commit 报告见 commits/ 目录。_")
    with open(os.path.join(BASE, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"done={len(done)} skipped={len(skipped)} pending={len(pending)} claimed_no_report={len(missing_detail)} "
          f"P0={tally['p0']} P1={tally['p1']} P2={tally['p2']} P3={tally['p3']} fixed={tally['fixed_later']} avg={avg}")


if __name__ == "__main__":
    main()
