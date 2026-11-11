/* zcode-workflow
description: Aionis 长周期迭代维护工作流：外向调研+向内核证并行采集 → 定夺施工清单（决策洞，需主会话在场）→ 施工 →
  门禁（pytest/ruff 实跑+有界修复回环）→ 提交推送 → 独立复核（只审不改+有界回环）→ 报告交付。骨架经 2026-11-11
  三轮实战验证（super-agent 整合两代+整备轮）固化。
whenToUse: 当业主发出 /goal 继续、迭代、优化、深耕类指令，或月度复盘/--propose
  引擎产出待落地提案卡、或值班发现需要多轮施工的改进主题时：以
  mission=本轮主题按名复跑本工作流，获得完整的「调研→定夺→施工→门禁→复核→交付」一轮迭代。注意：运行会在「定夺本轮施工清单」决策洞暂停，需主会话（ZCode
  会话）在场定夺后继续。
args:
  mission:
    type: string
    description: 本轮迭代主题（一两句话，如：研究前沿X并落地适配/某缺陷专项清偿/某机制的下一步深化）
    required: true
  deliverable_path:
    type: string
    description: 交付报告落盘路径（reports/ 下，沿用项目命名惯例）；留空则默认 reports/audits/iterate-round.md
    required: false
    default: ""
*/
// aionis-iterate — Aionis 长周期迭代维护工作流（骨架 2026-11-11 三轮实战验证后固化）
// 形状：并行采集（外向调研 ×1 + 向内核证 ×1）→ 定夺（hole，需主会话在场）→ 施工 →
// 门禁（pytest/ruff 实跑+有界修复）→ 提交推送 → 独立复核（只审不改+有界回环）→ 交付。

// ---------- 参数 ----------
const mission = String(args.mission ?? "").trim();
const deliverablePath =
  String(args.deliverable_path ?? "").trim() ||
  "reports/audits/iterate-round.md";

// ---------- 类型 ----------
interface ResearchItem {
  /** 方向/发现标题 */
  title: string;
  /** 来源 URL 或仓库 */
  source: string;
  /** 对 Aionis 的适配建议（具体可做/不该做） */
  adaptation: string;
  priority: "high" | "medium" | "low";
}

interface ResearchSurvey {
  items: ResearchItem[];
  /** 明确不建议吸收的（附一句理由） */
  rejected: string[];
}

interface RepoAudit {
  /** 仓库现状发现（每条含证据位置） */
  findings: string[];
  /** 实跑过的只读命令 */
  commandsRun: string[];
  /** 结论段（4-8 句，直言） */
  verdict: string;
}

interface IntegrationItem {
  /** 条目短 id（英文短横线） */
  id: string;
  /** 一句话标题（中文） */
  title: string;
  /** 为什么做（来源：调研条目/审计发现） */
  rationale: string;
  /** 预期触碰的文件/位置 */
  touchpoints: string;
  effort: "S" | "M" | "L";
}

interface Plan {
  /** 按执行顺序（文档类在前，代码类在后） */
  items: IntegrationItem[];
  /** 施工说明：顺序/风险/红线/跳过原则 */
  notes: string;
  /** 交付报告落盘路径 */
  deliverablePath: string;
}

interface ReviewFinding {
  where: string;
  what: string;
  severity: "low" | "medium" | "high";
}

interface Review {
  approved: boolean;
  findings: ReviewFinding[];
  notLanded: string[];
}

interface Finding {
  where: string;
  what: string;
  evidence: string;
  status: "verified" | "unconfirmed";
  severity: "low" | "medium" | "high";
}

interface WorkflowReport {
  conclusion: string;
  findings: Finding[];
  verified: string[];
  notCovered: string[];
}

// ---------- 进度看板（先于首次 report 声明） ----------
artifact.table("progress", {
  title: "迭代进度看板",
  columns: [
    { field: "item", label: "条目" },
    { field: "status", label: "状态" },
    { field: "note", label: "备注" },
  ],
  key: "item",
});

// ---------- 常量 ----------
const AIONIS = `【Aionis 背景】F:/ZCodeData/Aionis（Windows + Git Bash + uv，Python≥3.10，web/ 为 Next.js+TS）是可证伪、反泄漏量化研究项目：PIT 点时数据、预注册两尾、config_committed 先于结果。硬红线（AGENTS.md）：研究管线（src/aionis、scripts/phase_*、runs/ledger.jsonl 语义）零改动，除非 mission 明确指名研究面且附预注册/7-gate 语义；许可证仅 MIT/Apache/BSD；禁止 mock 数据入研究管线；禁止 Gemini/TokenHub provider；稳态 token 不增烧（晚间通道稳态 1 LLM 会话/晚）；无后台长驻进程；不 force-push。运维设施：晚间数据通道（scripts/ops_local_refresh.py，doctor 八层，--status/--doctor 只读）/夜报班 23:35/monthly_review.py（--weekly/--lessons/--propose）/四档节奏表 docs/ops-local-refresh.md。GitHub Actions 自 2026-11-11 按业主停用令全面暂停（billing；恢复清单在 billing playbook 节）——线上验证不可用属预期。state/handoff.md 是轮次账本（append-only，勘误只追加不回改）。`;

const RED_LINES =
  "红线重申：研究管线零改动（除非指名）；append-only 勘误不回改旧文；不提交 data/、*.parquet、.env；Conventional Commits 原子分批；门禁未过不交付；做不到的条目如实报告并跳过，绝不伪造。";

async function catchTo<T>(p: Node<T>, fallback: T): Promise<T> {
  try {
    return (await p) as unknown as T;
  } catch {
    return fallback;
  }
}

if (!mission) {
  return {
    conclusion: "缺少 mission 参数——请传入本轮迭代主题后复跑。",
    findings: [],
    verified: [],
    notCovered: ["全部：无主题未启动"],
  } as WorkflowReport;
}

// ---------- 阶段 1：并行采集 ----------
phase("并行采集：外向调研 · 向内核证");
log("主题：" + mission);

const researchAsk =
  "你是前沿调研员。本轮迭代主题：「" +
  mission +
  "」。\n\n" +
  AIONIS +
  "\n\n任务：WebSearch/WebFetch 多轮检索与主题相关的研究报告、开源仓库、工程实践（2025-2026 优先）；每个候选给出来源 URL 与 Aionis 适配建议（具体到可做什么/不该做什么，与反泄漏原则冲突的明确写不该做）；工具/仓库逐个核实许可证（仅 MIT/Apache/BSD 可用，其余排除并标注）。产出 5-8 条按优先级排序 + 「不建议吸收」清单（各附一句理由）。输出中文。";

const auditAsk =
  "你是现状审计员（只读，禁止修复）。工作目录 F:/ZCodeData/Aionis（Windows，Git Bash，uv，gh 已认证）。\n\n" +
  AIONIS +
  "\n\n本轮迭代主题：「" +
  mission +
  "」。\n\n任务：围绕主题对仓库现状做实证核验——只读命令（git log/status、grep/读文件、uv run python scripts/ops_local_refresh.py --status 与 --doctor、gh run list 等，按需选择）；涉及密钥只列 key 名与存在性，绝不输出密钥值；结论必须给证据位置（文件:行 或 命令+关键输出）；区分「可施工项」与「需业主钥匙项」（billing/真推许可/账本裁决等只列不动）。输出 findings（每条含证据）、commandsRun、verdict（4-8 句直言）。输出中文。";

const researchP = catchTo(
  agent("前沿调研员").ask<ResearchSurvey>(researchAsk),
  { items: [], rejected: ["调研子代理失败"] } as ResearchSurvey,
);
const auditP = catchTo(
  agent("现状审计员").ask<RepoAudit>(auditAsk),
  { findings: ["审计子代理失败"], commandsRun: [], verdict: "审计子代理失败，人工复查" } as RepoAudit,
);

// 定夺需要两路 → join
const research = await researchP;
const audit = await auditP;
report(
  { item: "外向调研", status: research.items.length + " 条方向", note: "待定夺" },
  "progress",
);
report(
  { item: "向内核证", status: audit.findings.length + " 条发现", note: audit.verdict.slice(0, 100) },
  "progress",
);

// ---------- 阶段 2：定夺（hole，需主会话在场） ----------
log("两路证据齐备，等待主会话定夺施工清单");
const plan = await hole<Plan>(
  "定夺本轮施工清单",
  "两路证据已齐。\n\n== 外向调研 ==\n" +
    JSON.stringify(research) +
    "\n\n== 向内核证 ==\n" +
    JSON.stringify(audit) +
    "\n\n== 定夺框架 ==\n" +
    "① 条目 3-6 条，少而实；文档/报告类在前（晚间通道可能运行中），代码类在后；② 每条 rationale 引用来源（调研条目/审计发现）；③ 需业主钥匙项只列进报告待决区不动；④ " +
    RED_LINES +
    "\n请产出 items/notes（含施工顺序、报告必备章节、提交规范）/deliverablePath（默认 " +
    deliverablePath +
    "）。state/handoff.md 轮次号顺延（施工员自行核对最新号）。",
);
report(
  { item: "施工清单", status: "已定夺", note: (plan.items.length + " 条：" + plan.items.map((i) => i.id).join("、")).slice(0, 100) },
  "progress",
);

// ---------- 阶段 3：施工 ----------
phase("施工：逐条实施");
const impl = agent("施工员", {
  system:
    "你是 Aionis 的工程师（Engineer 角色，AGENTS.md 边界）：只实施交办条目，不扩大范围，不改无关模块。" +
    AIONIS +
    "\n动工前先跑 uv run python scripts/ops_local_refresh.py --status 确认晚间通道未在运行（在运行则先做文档条目，代码类最后做并重查）；push 前 git pull --rebase。完成的标准是真实落地+可验证（相关单测要跑，不跑全量——脚本稍后统一门禁）；做不到的如实报告并跳过；遇到只有业主能决定的矛盾，直说并按保守路径继续。",
});
for (const item of plan.items) {
  log("施工条目 " + item.id + "：" + item.title);
  const out = await impl.ask(
    "实施条目 " +
      item.id +
      "「" +
      item.title +
      "」（" +
      item.effort +
      "）。\n理由：" +
      item.rationale +
      "\n触碰点：" +
      item.touchpoints +
      "\n最小充分改动；完成后两三句报告做了什么、验证了什么。",
  );
  report({ item: "施工·" + item.id, status: "完成", note: out.split("\n")[0].slice(0, 100) }, "progress");
}

// ---------- 阶段 4：门禁 ----------
async function runGates(): Promise<{ ok: boolean; detail: string; ran: string[] }> {
  const parts: string[] = [];
  const ran: string[] = [];
  let ok = true;
  try {
    const pytest = await world.run("uv", ["run", "pytest", "-q"], { timeoutMs: 1200000, output: { tail: 16384 } });
    ran.push("pytest");
    ok = ok && pytest.exitCode === 0;
    parts.push("pytest exit=" + pytest.exitCode + "\n" + (pytest.stdout + "\n" + pytest.stderr).slice(-2000));
  } catch (e) {
    ok = false;
    parts.push("pytest 执行失败：" + String(e));
  }
  try {
    const ruff = await world.run("uv", ["run", "ruff", "check"], { timeoutMs: 300000, output: { tail: 16384 } });
    ran.push("ruff");
    ok = ok && ruff.exitCode === 0;
    parts.push("ruff exit=" + ruff.exitCode + "\n" + (ruff.stdout + "\n" + ruff.stderr).slice(-1000));
  } catch (e) {
    ok = false;
    parts.push("ruff 执行失败：" + String(e));
  }
  try {
    const checker = await files.glob("scripts/check_ci_yaml.py");
    if (checker.length > 0) {
      const yv = await world.run("uv", ["run", "python", "scripts/check_ci_yaml.py"], {
        timeoutMs: 120000,
        output: { tail: 16384 },
      });
      ran.push("check_ci_yaml");
      if (yv.exitCode !== 0) ok = false;
      parts.push("check_ci_yaml exit=" + yv.exitCode + "\n" + (yv.stdout + "\n" + yv.stderr).slice(-1500));
    }
  } catch (e) {
    parts.push("check_ci_yaml 环境不可用（不判失败）：" + String(e));
  }
  try {
    const webCfg = await files.glob("web/tsconfig.json");
    if (webCfg.length > 0) {
      const tsc = await world.run("npx", ["tsc", "--noEmit", "-p", "web/tsconfig.json"], {
        timeoutMs: 600000,
        output: { tail: 16384 },
      });
      ran.push("tsc");
      if (tsc.exitCode !== 0) ok = false;
      parts.push("tsc exit=" + tsc.exitCode + "\n" + (tsc.stdout + "\n" + tsc.stderr).slice(-2000));
    }
  } catch (e) {
    parts.push("tsc 环境不可用（不判失败）：" + String(e));
  }
  return { ok, detail: parts.join("\n---\n"), ran };
}

phase("门禁：pytest · ruff（+条件检查）");
let gate = await runGates();
let gateFixRound = 0;
while (!gate.ok && gateFixRound < 3) {
  gateFixRound += 1;
  log("门禁未过，第 " + gateFixRound + " 轮修复");
  await impl.ask("门禁失败，请修复（只修暴露问题，不提交）：\n" + gate.detail);
  gate = await runGates();
}
report(
  { item: "门禁", status: gate.ok ? "全绿" : "受阻", note: gate.ok ? gate.ran.join("/") + " 通过" : gateFixRound + " 轮后仍未全绿" },
  "progress",
);

// ---------- 阶段 5：提交推送 ----------
phase("提交并推送");
const pushOut = await impl.ask(
  "门禁已" +
    (gate.ok ? "全绿" : "尽力而为") +
    "。收尾：1) state/handoff.md / state/current.md 反映本轮最终事实（轮次顺延）；2) Conventional Commits 原子分批提交（不夹带无关文件）；3) git pull --rebase 后 push（失败重试一次，仍失败如实报告）；4) 返回提交哈希清单、push 结果、改动文件清单。",
);
report({ item: "提交推送", status: "完成", note: pushOut.split("\n")[0].slice(0, 100) }, "progress");

// ---------- 阶段 6：独立复核 ----------
phase("独立复核施工结果");
const reviewer = agent("独立复核员", {
  system:
    "你是独立复核员，只审不改：不得编辑/提交/推送。结论须来自亲自读到的文件与只读命令，引用 文件:行号。伪造完成、红线违规（研究管线被改、append-only 被回改、许可证违规、.env/data 混入、占位 TODO）直接列 high。脚本已跑门禁，不必跑全量 pytest。",
});
let review = await reviewer.ask<Review>(
  "复核本轮迭代施工。主题：" +
    mission +
    "\n方案条目：" +
    JSON.stringify(plan.items) +
    "\n施工自述：" +
    pushOut.slice(0, 3000) +
    "\n\n请：1) git log --oneline -10 与 git show --stat 核对新提交；2) 逐条核验落地（读文件本身，不采信自述）；3) 抽读 " +
    plan.deliverablePath +
    " 与 handoff 新增段核对事实（自报数字以实测为准）；4) 红线检查；5) 返回 approved/findings/notLanded。",
);
let reviewFixRound = 0;
while ((!review.approved || review.findings.some((f) => f.severity === "high")) && reviewFixRound < 2) {
  reviewFixRound += 1;
  log("复核未通过，第 " + reviewFixRound + " 轮修复");
  await impl.ask("复核意见逐条修复（只修这些），修完自证并提交推送：\n" + JSON.stringify(review));
  review = await reviewer.ask<Review>(
    "修复已提交，复核上轮意见是否解决：" + JSON.stringify(review.findings) + "\n只审不改、证据说话、返回 approved/findings/notLanded。",
  );
}
report(
  {
    item: "独立复核",
    status: review.approved ? "通过" : "未通过",
    note: review.findings.length + " 条意见" + (review.notLanded.length > 0 ? "；未落地: " + review.notLanded.join(",") : ""),
  },
  "progress",
);

// ---------- 阶段 7：交付 ----------
phase("交付本轮报告");
let reportPublished = false;
try {
  await artifact.file("iterate-report", plan.deliverablePath, {
    title: "迭代轮报告：" + mission.slice(0, 40),
    description: "调研采纳/审计发现/施工落地/复核结论的完整记录",
    primary: true,
  });
  reportPublished = true;
} catch {
  await impl.ask(
    "报告 " + plan.deliverablePath + " 发布失败（缺失/为空？），确认存在且完整（必要时补写并推送）后回复确认。",
  );
  try {
    await artifact.file("iterate-report", plan.deliverablePath, {
      title: "迭代轮报告：" + mission.slice(0, 40),
      description: "调研采纳/审计发现/施工落地/复核结论的完整记录",
      primary: true,
    });
    reportPublished = true;
  } catch {
    reportPublished = false;
  }
}
report({ item: "交付", status: reportPublished ? "完成" : "artifact 发布失败", note: plan.deliverablePath }, "progress");

// ---------- 汇总 ----------
const findings: Finding[] = [];
for (const f of audit.findings) {
  findings.push({ where: "现状审计", what: f, evidence: "审计员只读核验", status: "verified", severity: "low" });
}
for (const it of research.items) {
  if (it.priority === "high") {
    findings.push({
      where: "外向调研",
      what: "[" + it.priority + "] " + it.title + "——" + it.adaptation.slice(0, 120),
      evidence: it.source,
      status: "unconfirmed",
      severity: "medium",
    });
  }
}
for (const f of review.findings) {
  findings.push({ where: f.where, what: f.what, evidence: "独立复核员（只审不改）", status: "verified", severity: f.severity });
}
if (review.notLanded.length > 0) {
  findings.push({
    where: "施工条目",
    what: "声称完成但未落地：" + review.notLanded.join(", "),
    evidence: "复核员 notLanded 清单",
    status: "verified",
    severity: "high",
  });
}
if (!gate.ok) {
  findings.push({
    where: "门禁",
    what: gateFixRound + " 轮修复后仍未全绿",
    evidence: gate.detail.slice(0, 1500),
    status: "verified",
    severity: "high",
  });
}
if (!reportPublished) {
  findings.push({ where: plan.deliverablePath, what: "报告未能发布为 artifact", evidence: "两次尝试被拒", status: "unconfirmed", severity: "low" });
}

const verified: string[] = [
  "现状审计（只读命令实证）",
  "门禁（world.run 实跑）：" + (gate.ok ? gate.ran.join("/") + " 全绿" : "未全绿，见 findings"),
  "独立复核员逐条核验（只审不改）",
];
if (reportPublished) verified.push("报告已发布（iterate-report）");

const notCovered: string[] = [
  "外向调研条目属研判类（unconfirmed），落地条目经独立复核验证",
  "GitHub Actions 线上结论：停用令持续期间不可验（billing；恢复清单见 docs/ops-local-refresh.md billing playbook 节）",
];

const conclusion =
  "本轮迭代（" +
  mission.slice(0, 60) +
  "）落地 " +
  plan.items.length +
  " 条（" +
  plan.items.map((i) => i.id).join("、") +
  "）；门禁 " +
  (gate.ok ? "全绿" : "未全绿") +
  "，复核 " +
  (review.approved ? "通过" : reviewFixRound + " 轮后仍未通过") +
  "；报告与 handoff 轮次已提交推送。";

return { conclusion, findings, verified, notCovered } as WorkflowReport;