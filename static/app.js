/* 口述史事件先后核对 —— 原生 JavaScript 前端 */
"use strict";

const FEASIBLE_EXAMPLE =
  `出门,到车站,15,30
到车站,列车进站,5,10
列车进站,开车铃响,2,5
开车铃响,开车,1,3
出门,到外婆家,90,120`;

// 前三行是一条时间链；最后一行把区间反过来卡死，和链上的累计上界冲突。
const CONFLICT_EXAMPLE =
  `出门,到车站,15,30
到车站,列车进站,5,10
列车进站,开车铃响,2,5
开车铃响,出门,60,120`;

const $ = (id) => document.getElementById(id);
const inputEl = $("input");
const resultEl = $("result");
const globalErrorEl = $("global-error");

function el(tag, props, children) {
  const node = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on") && typeof v === "function")
        node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
  }
  if (children) {
    for (const child of [].concat(children)) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
  }
  return node;
}

function showError(msg) {
  globalErrorEl.className = "alert error";
  globalErrorEl.textContent = msg;
}

function clearOutput() {
  globalErrorEl.className = "alert error hidden";
  globalErrorEl.textContent = "";
  resultEl.className = "hidden";
  resultEl.textContent = "";
}

/* 在输入框中定位到某一原始行 */
function focusLine(lineNo) {
  const lines = inputEl.value.split("\n");
  let start = 0;
  for (let i = 0; i < lineNo - 1 && i < lines.length; i++) start += lines[i].length + 1;
  const end = start + (lines[lineNo - 1] ? lines[lineNo - 1].length : 0);
  inputEl.focus();
  inputEl.setSelectionRange(start, end);
  inputEl.scrollTop = Math.max(0, (start / Math.max(1, inputEl.value.length)) * inputEl.scrollHeight - 60);
}

function buildSummary(counts) {
  return el("div", { class: "summary" }, [
    el("span", { class: "chip", text: `事件 ${counts.event_count} 个` }),
    el("span", { class: "chip", text: `区间 ${counts.constraint_count} 条` }),
    counts.component_count
      ? el("span", { class: "chip", text: `连通分组 ${counts.component_count} 组` })
      : null,
  ]);
}

/* 逐行校验明细表 */
function buildLinesTable(lines, involvedSet) {
  const rows = lines.map((r) =>
    el("tr", { class: (!r.valid || (involvedSet && involvedSet.has(r.line_no))) ? "bad" : "" }, [
      el("td", { class: "line-no", text: String(r.line_no) }),
      el("td", { class: "raw-cell" }, el("code", { text: r.raw })),
      r.valid
        ? el("td", { text: "通过" })
        : el("td", { class: "err-cell", text: r.errors.join("；") }),
    ])
  );
  return el(
    "table",
    { class: "line-table" },
    [
      el("thead", {}, el("tr", {}, [
        el("th", { text: "行号" }),
        el("th", { text: "原始内容" }),
        el("th", { text: "校验" }),
      ])),
      el("tbody", {}, rows),
    ]
  );
}

function renderFeasible(data) {
  globalErrorEl.className = "alert good";
  globalErrorEl.textContent =
    "✔ 全部区间可以同时成立。以下是以最早事件为第 0 分钟的一条可行时间线（分钟为整数）。";

  const frag = document.createDocumentFragment();
  frag.appendChild(buildSummary(data));

  if (data.note) {
    frag.appendChild(el("div", { class: "alert warn", text: data.note }));
  }

  const maxTime = Math.max(1, ...data.timeline.map((t) => t.time));
  const rows = data.timeline.map((item, idx) =>
    el("tr", {}, [
      el("td", { text: String(idx) }),
      el("td", { text: item.event }),
      el("td", { class: "time", text: `第 ${item.time} 分钟` }),
      el("td", { class: "timeline-bar-cell" }, (() => {
        const pct = (item.time / maxTime) * 100;
        return el("div", { class: "bar-track" + (idx === 0 ? " axis" : "") },
          el("div", { class: "bar-fill", style: `width:${Math.max(pct, 1.5)}%` }));
      })()),
    ])
  );
  const timelinePanel = el("section", { class: "panel" }, [
    el("h3", { text: "② 可行时间线（按时间先后排序）" }),
    el(
      "table",
      { class: "timeline-table" },
      [
        el("thead", {}, el("tr", {}, [
          el("th", { text: "顺序" }),
          el("th", { text: "事件" }),
          el("th", { class: "time", text: "时刻" }),
          el("th", { text: "时间轴" }),
        ])),
        el("tbody", {}, rows),
      ]
    ),
  ]);
  frag.appendChild(timelinePanel);

  const linesPanel = el("section", { class: "panel" }, [
    el("h3", { text: "③ 逐行校验" }),
    buildLinesTable(data.lines),
  ]);
  frag.appendChild(linesPanel);

  resultEl.appendChild(frag);
}

function renderConflict(data) {
  globalErrorEl.className = "alert error";
  globalErrorEl.textContent =
    "✘ 联立后存在冲突：下列各行构成一条首尾相接的闭合矛盾链（点击任一卡片可定位到原始行）。";

  const cycle = data.cycle;
  const involved = new Set(cycle.involved_lines);
  const frag = document.createDocumentFragment();
  frag.appendChild(buildSummary(data));

  const chainWrap = el("div", { class: "chain-wrap" });
  const seq = cycle.sequence;
  for (let i = 0; i < cycle.steps.length; i++) {
    const s = cycle.steps[i];
    const card = el("div", { class: "chain-card", onclick: () => focusLine(s.line_no) }, [
      el("span", { class: "tag", text: `原始第 ${s.line_no} 行 · ${s.kind}` }),
      el("div", { class: "edge", text: `${s.from_event} → ${s.to_event}` }),
      el("div", { class: "ineq", text: s.inequality }),
      el("div", { class: "src" }, [document.createTextNode("原行："), el("code", { text: s.raw })]),
    ]);
    chainWrap.appendChild(el("div", { class: "chain-step" }, card));

    const arrow = el("div", { class: "chain-arrow" }, [
      el("span", { text: "→" }),
      el("small", { text: i === cycle.steps.length - 1 ? "回到起点，链闭合" : "下一条" }),
    ]);
    chainWrap.appendChild(arrow);
  }
  // 最后补一张“起点”卡，强调首尾相同
  const startName = seq[0];
  chainWrap.appendChild(
    el("div", { class: "chain-step" },
      el("div", { class: "chain-card", style: "cursor:default;background:#fbf8f3;" }, [
        el("div", { class: "edge", text: startName }),
        el("div", { style: "color:#7a7268;font-size:.8rem", text: "（回到链的起点）" }),
      ])
    )
  );

  const proof = el("div", { class: "proof" }, [
    el("strong", { text: "为什么矛盾：" }),
    el("span", { text: "把链上每个方向的不等式全部相加——" }),
    el("span", { class: "math", text: cycle.sum_inequality }),
    el("span", { class: "math", text: `左边逐项抵消为 0，右边相加为 ${cycle.bounds_sum}` }),
    el("span", { text: cycle.conclusion }),
    el("div", { style: "margin-top:8px;color:#7a7268;font-size:.84rem" },
      `涉及原始行：第 ${cycle.involved_lines.join("、")} 行`),
  ]);

  frag.appendChild(el("section", { class: "panel" }, [
    el("h3", { text: `② 闭合矛盾链（${startName} → … → ${startName}）` }),
    chainWrap,
    proof,
  ]));

  frag.appendChild(el("section", { class: "panel" }, [
    el("h3", { text: "③ 逐行校验（红底为参与矛盾链的行）" }),
    buildLinesTable(data.lines, involved),
  ]));

  resultEl.appendChild(frag);
}

function renderInvalid(data) {
  showError(data.error);
  const frag = document.createDocumentFragment();
  frag.appendChild(el("section", { class: "panel" }, [
    el("h3", { text: "逐行校验" }),
    buildLinesTable(data.lines),
  ]));
  resultEl.appendChild(frag);
}

async function runCheck() {
  const text = inputEl.value;
  if (!text.trim()) {
    clearOutput();
    showError("输入为空：请先粘贴若干行，或点击“一键填充示例”。");
    resultEl.className = "";
    return;
  }
  clearOutput();
  const btn = $("btn-check");
  btn.disabled = true;
  btn.textContent = "核对中…";
  try {
    const resp = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) throw new Error(`服务返回 ${resp.status}`);
    const data = await resp.json();

    resultEl.className = "";
    if (data.status === "empty") {
      showError(data.error);
    } else if (data.status === "invalid") {
      renderInvalid(data);
    } else if (data.status === "conflict") {
      renderConflict(data);
    } else if (data.status === "feasible") {
      renderFeasible(data);
    }
  } catch (err) {
    showError(`核对失败：${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "核对事件先后";
  }
}

$("btn-check").addEventListener("click", runCheck);
$("btn-example").addEventListener("click", () => {
  inputEl.value = FEASIBLE_EXAMPLE;
  clearOutput();
  runCheck();
});
$("btn-conflict").addEventListener("click", () => {
  inputEl.value = CONFLICT_EXAMPLE;
  clearOutput();
  runCheck();
});
$("btn-clear").addEventListener("click", () => {
  inputEl.value = "";
  clearOutput();
});
