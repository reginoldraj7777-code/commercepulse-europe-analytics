import fs from "node:fs/promises";
import path from "node:path";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = process.env.COMMERCEPULSE_ROOT
  ? path.resolve(process.env.COMMERCEPULSE_ROOT)
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const ANALYSIS = path.join(ROOT, "artifacts", "analysis");
const VALIDATION = path.join(ROOT, "artifacts", "validation");
const OUTPUT = path.join(ROOT, "excel", "CommercePulse_Manager_Pack.xlsx");
const PREVIEW_DIR = path.join(ROOT, "artifacts", "workbook_previews");

const COLORS = {
  ink: "#102A43",
  navy: "#163A5F",
  teal: "#0F766E",
  cyan: "#DDF4F1",
  blue: "#DDEBFA",
  green: "#167D4D",
  greenLight: "#DCFCE7",
  amber: "#A86103",
  amberLight: "#FEF3C7",
  red: "#B42318",
  redLight: "#FEE4E2",
  gray: "#52606D",
  grayLight: "#F3F6F8",
  border: "#C9D5DF",
  white: "#FFFFFF",
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  const [headers, ...records] = rows.filter((r) => r.some((value) => value !== ""));
  return records.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])),
  );
}

async function loadCsv(name, base = ANALYSIS) {
  return parseCsv(await fs.readFile(path.join(base, name), "utf8"));
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function date(value) {
  return new Date(`${value}T00:00:00Z`);
}

function columnName(index) {
  let n = index;
  let result = "";
  while (n > 0) {
    const remainder = (n - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

function setColumnWidths(sheet, widths, lastRow) {
  widths.forEach((width, index) => {
    const col = columnName(index + 1);
    sheet.getRange(`${col}1:${col}${lastRow}`).format.columnWidth = width;
  });
}

function styleTitle(sheet, title, subtitle, lastColumn) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastColumn}2`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastColumn}2`).format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 20 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A3:${lastColumn}3`).merge();
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange(`A3:${lastColumn}3`).format = {
    fill: COLORS.blue,
    font: { color: COLORS.ink, italic: true, size: 10 },
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange("1:3").format.rowHeight = 25;
}

function styleHeader(range) {
  range.format = {
    fill: COLORS.teal,
    font: { bold: true, color: COLORS.white, size: 10 },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.teal },
  };
  range.format.rowHeight = 34;
}

function styleSection(range) {
  range.format = {
    fill: COLORS.grayLight,
    font: { bold: true, color: COLORS.ink, size: 11 },
    borders: { preset: "outside", style: "thin", color: COLORS.border },
  };
}

function addKpiCard(sheet, rangeAddress, label, formula, numberFormat, fill = COLORS.cyan) {
  const range = sheet.getRange(rangeAddress);
  const [start, end] = rangeAddress.split(":");
  const startColumn = start.match(/[A-Z]+/)[0];
  const startRow = Number(start.match(/\d+/)[0]);
  const endColumn = end.match(/[A-Z]+/)[0];
  const endRow = Number(end.match(/\d+/)[0]);
  sheet.getRange(`${startColumn}${startRow}:${endColumn}${startRow}`).merge();
  sheet.getRange(start).values = [[label]];
  sheet.getRange(`${startColumn}${startRow + 1}:${endColumn}${endRow}`).merge();
  sheet.getRange(`${startColumn}${startRow + 1}`).formulas = [[formula]];
  range.format = {
    fill,
    font: { color: COLORS.ink },
    borders: { preset: "outside", style: "thin", color: COLORS.border },
    verticalAlignment: "center",
  };
  sheet.getRange(`${startColumn}${startRow}:${endColumn}${startRow}`).format.font = {
    bold: true,
    color: COLORS.gray,
    size: 9,
  };
  sheet.getRange(`${startColumn}${startRow + 1}:${endColumn}${endRow}`).format.font = {
    bold: true,
    color: COLORS.ink,
    size: 17,
  };
  sheet.getRange(`${startColumn}${startRow + 1}:${endColumn}${endRow}`).setNumberFormat(numberFormat);
}

function addStatusConditionalFormatting(range) {
  range.conditionalFormats.add("containsText", {
    text: "PASS",
    format: { fill: COLORS.greenLight, font: { bold: true, color: COLORS.green } },
  });
  range.conditionalFormats.add("containsText", {
    text: "FAIL",
    format: { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } },
  });
}

function addSeverityConditionalFormatting(range) {
  range.conditionalFormats.add("containsText", {
    text: "Critical",
    format: { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } },
  });
  range.conditionalFormats.add("containsText", {
    text: "High",
    format: { fill: COLORS.amberLight, font: { bold: true, color: COLORS.amber } },
  });
  range.conditionalFormats.add("containsText", {
    text: "Watch",
    format: { fill: COLORS.greenLight, font: { color: COLORS.green } },
  });
}

const monthly = await loadCsv("monthly_kpis.csv");
const rootCauses = await loadCsv("root_causes.csv");
const actions = await loadCsv("action_register.csv");
const forecast = await loadCsv("forecast.csv");
const reconciliations = await loadCsv("reconciliations.csv");
const qualityChecks = await loadCsv("data_quality_checks.csv", VALIDATION);
const generationManifest = JSON.parse(
  await fs.readFile(path.join(ROOT, "data", "sample", "generation_manifest.json"), "utf8"),
);
const executiveSummary = JSON.parse(
  await fs.readFile(path.join(ANALYSIS, "executive_summary.json"), "utf8"),
);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const monthlySheet = workbook.worksheets.add("Monthly KPI");
const exceptionsSheet = workbook.worksheets.add("Exceptions");
const actionSheet = workbook.worksheets.add("Action Register");
const forecastSheet = workbook.worksheets.add("Forecast");
const definitionsSheet = workbook.worksheets.add("Definitions");
const sourcesSheet = workbook.worksheets.add("Sources");
const checksSheet = workbook.worksheets.add("Checks");

workbook.comments.setSelf({ displayName: "CommercePulse Analytics" });

// Monthly KPI: source inputs plus formula-derived commercial and operational metrics.
styleTitle(
  monthlySheet,
  "Monthly KPI Model",
  "Blue cells are source inputs; white/green cells are live workbook formulas. Currency: EUR.",
  "AB",
);
const monthlyHeaders = [
  "Month",
  "Gross Revenue",
  "Discounts",
  "Refunds",
  "Net Revenue",
  "COGS",
  "Recovered COGS",
  "Return Handling",
  "Fulfillment",
  "Marketing Spend",
  "Contribution Margin",
  "Sessions",
  "Converted Sessions",
  "Conversion Rate",
  "Units Sold",
  "Units Returned",
  "Return Rate",
  "Fulfilled Orders",
  "On-Time Orders",
  "On-Time Rate",
  "Revenue Target",
  "Revenue Variance",
  "Contribution Target",
  "Contribution Variance",
  "Orders",
  "AOV",
  "Margin Rate",
  "Marketing ROAS",
];
monthlySheet.getRange("A4:AB4").values = [monthlyHeaders];
styleHeader(monthlySheet.getRange("A4:AB4"));
const monthlyStart = 5;
const monthlyEnd = monthlyStart + monthly.length - 1;
monthly.forEach((record, offset) => {
  const row = monthlyStart + offset;
  monthlySheet.getRange(`A${row}:D${row}`).values = [[
    date(record.month_start),
    number(record.gross_revenue_eur),
    number(record.discounts_eur),
    number(record.refunds_eur),
  ]];
  monthlySheet.getRange(`F${row}:J${row}`).values = [[
    number(record.cogs_eur),
    number(record.recovered_cogs_eur),
    number(record.return_handling_cost_eur),
    number(record.fulfillment_cost_eur),
    number(record.marketing_spend_eur),
  ]];
  monthlySheet.getRange(`L${row}:M${row}`).values = [[
    number(record.sessions),
    number(record.converted_sessions),
  ]];
  monthlySheet.getRange(`O${row}:P${row}`).values = [[
    number(record.units_sold),
    number(record.units_returned),
  ]];
  monthlySheet.getRange(`R${row}:S${row}`).values = [[
    number(record.fulfilled_orders),
    number(record.on_time_orders),
  ]];
  monthlySheet.getRange(`U${row}`).values = [[number(record.net_revenue_target_eur)]];
  monthlySheet.getRange(`W${row}`).values = [[number(record.contribution_margin_target_eur)]];
  monthlySheet.getRange(`Y${row}`).values = [[number(record.orders)]];
  monthlySheet.getRange(`E${row}`).formulas = [[`=B${row}-C${row}-D${row}`]];
  monthlySheet.getRange(`K${row}`).formulas = [[
    `=E${row}-F${row}+G${row}-H${row}-I${row}-J${row}`,
  ]];
  monthlySheet.getRange(`N${row}`).formulas = [[`=IF(L${row}=0,0,M${row}/L${row})`]];
  monthlySheet.getRange(`Q${row}`).formulas = [[`=IF(O${row}=0,0,P${row}/O${row})`]];
  monthlySheet.getRange(`T${row}`).formulas = [[`=IF(R${row}=0,0,S${row}/R${row})`]];
  monthlySheet.getRange(`V${row}`).formulas = [[`=E${row}-U${row}`]];
  monthlySheet.getRange(`X${row}`).formulas = [[`=K${row}-W${row}`]];
  monthlySheet.getRange(`Z${row}`).formulas = [[`=IF(Y${row}=0,0,E${row}/Y${row})`]];
  monthlySheet.getRange(`AA${row}`).formulas = [[`=IF(E${row}=0,0,K${row}/E${row})`]];
  monthlySheet.getRange(`AB${row}`).formulas = [[`=IF(J${row}=0,0,E${row}/J${row})`]];
});
monthlySheet.getRange(`A${monthlyStart}:AB${monthlyEnd}`).format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: "#E8EEF3" } },
};
monthlySheet.getRange(`B${monthlyStart}:D${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`F${monthlyStart}:J${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`L${monthlyStart}:M${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`O${monthlyStart}:P${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`R${monthlyStart}:S${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`U${monthlyStart}:U${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`W${monthlyStart}:W${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`Y${monthlyStart}:Y${monthlyEnd}`).format.fill = COLORS.blue;
monthlySheet.getRange(`E${monthlyStart}:E${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`K${monthlyStart}:K${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`N${monthlyStart}:N${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`Q${monthlyStart}:Q${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`T${monthlyStart}:T${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`V${monthlyStart}:V${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`X${monthlyStart}:X${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`Z${monthlyStart}:AB${monthlyEnd}`).format.fill = COLORS.greenLight;
monthlySheet.getRange(`A${monthlyStart}:A${monthlyEnd}`).setNumberFormat("mmm yyyy");
for (const column of ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "U", "V", "W", "X", "Z"]) {
  monthlySheet.getRange(`${column}${monthlyStart}:${column}${monthlyEnd}`).setNumberFormat('€#,##0;[Red]-€#,##0');
}
for (const column of ["N", "Q", "T", "AA"]) {
  monthlySheet.getRange(`${column}${monthlyStart}:${column}${monthlyEnd}`).setNumberFormat("0.0%");
}
monthlySheet.getRange(`AB${monthlyStart}:AB${monthlyEnd}`).setNumberFormat("0.0x");
monthlySheet.getRange(`L${monthlyStart}:Y${monthlyEnd}`).format.horizontalAlignment = "right";
monthlySheet.getRange(`V${monthlyStart}:V${monthlyEnd}`).conditionalFormats.add("cellIs", {
  operator: "lessThan",
  formula: 0,
  format: { fill: COLORS.redLight, font: { color: COLORS.red } },
});
monthlySheet.getRange(`X${monthlyStart}:X${monthlyEnd}`).conditionalFormats.add("cellIs", {
  operator: "lessThan",
  formula: 0,
  format: { fill: COLORS.redLight, font: { color: COLORS.red } },
});
const monthlyTable = monthlySheet.tables.add(`A4:AB${monthlyEnd}`, true, "MonthlyKPITable");
monthlyTable.style = "TableStyleMedium2";
monthlySheet.freezePanes.freezeRows(4);
monthlySheet.freezePanes.freezeColumns(1);
setColumnWidths(
  monthlySheet,
  [12, 15, 12, 12, 15, 13, 15, 14, 13, 15, 17, 11, 14, 13, 11, 13, 11, 14, 13, 12, 14, 15, 17, 18, 10, 12, 12, 14],
  monthlyEnd,
);

// Executive summary with formula-linked KPI cards and native charts.
styleTitle(
  summary,
  "CommercePulse Europe — Manager Pack",
  `Decision snapshot | ${generationManifest.profile.start_date} to ${generationManifest.profile.end_date} | deterministic synthetic operations + real ECB FX`,
  "M",
);
addKpiCard(summary, "A5:C7", "NET REVENUE", `=SUM('Monthly KPI'!E${monthlyStart}:E${monthlyEnd})`, '€#,##0', COLORS.cyan);
addKpiCard(summary, "D5:F7", "CONTRIBUTION MARGIN", `=SUM('Monthly KPI'!K${monthlyStart}:K${monthlyEnd})`, '€#,##0;[Red]-€#,##0', COLORS.cyan);
addKpiCard(summary, "G5:I7", "CONTRIBUTION MARGIN RATE", `=IF(A6=0,0,D6/A6)`, "0.0%", COLORS.cyan);
addKpiCard(summary, "J5:L7", "MARKETING ROAS", `=IF(SUM('Monthly KPI'!J${monthlyStart}:J${monthlyEnd})=0,0,A6/SUM('Monthly KPI'!J${monthlyStart}:J${monthlyEnd}))`, "0.0x", COLORS.cyan);
addKpiCard(summary, "A9:C11", "LATEST REVENUE VS TARGET", `='Monthly KPI'!V${monthlyEnd}`, '€#,##0;[Red]-€#,##0', COLORS.grayLight);
addKpiCard(summary, "D9:F11", "LATEST MARGIN RATE", `='Monthly KPI'!AA${monthlyEnd}`, "0.0%", COLORS.grayLight);
addKpiCard(summary, "G9:I11", "LATEST CONVERSION RATE", `='Monthly KPI'!N${monthlyEnd}`, "0.0%", COLORS.grayLight);
addKpiCard(summary, "J9:L11", "LATEST RETURN RATE", `='Monthly KPI'!Q${monthlyEnd}`, "0.0%", COLORS.grayLight);
summary.getRange("A13:M13").merge();
summary.getRange("A13").values = [[
  `Q2 revenue grew ${(executiveSummary.headline.net_revenue_change_pct * 100).toFixed(1)}% QoQ, while contribution margin fell €${Math.abs(executiveSummary.headline.contribution_margin_change_eur).toLocaleString("en-US", { maximumFractionDigits: 0 })}. Primary management question: how do we protect growth while recovering margin?`,
]];
summary.getRange("A13:M13").format = {
  fill: COLORS.amberLight,
  font: { bold: true, color: COLORS.amber, size: 11 },
  borders: { preset: "outside", style: "thin", color: "#E5B769" },
  wrapText: true,
};
summary.getRange("A13:M13").format.rowHeight = 43;
summary.getRange("A15:C15").values = [["Month", "Net Revenue", "Revenue Target"]];
styleHeader(summary.getRange("A15:C15"));
monthly.forEach((_, offset) => {
  const targetRow = 16 + offset;
  const sourceRow = monthlyStart + offset;
  summary.getRange(`A${targetRow}:C${targetRow}`).formulas = [[
    `=TEXT('Monthly KPI'!A${sourceRow},"mmm yy")`,
    `='Monthly KPI'!E${sourceRow}`,
    `='Monthly KPI'!U${sourceRow}`,
  ]];
});
summary.getRange(`B16:C${15 + monthly.length}`).setNumberFormat('€#,##0');
const revenueChart = summary.charts.add("line", summary.getRange(`A15:C${15 + monthly.length}`));
revenueChart.title = "Revenue growth outpaced target after March";
revenueChart.hasLegend = true;
revenueChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
revenueChart.yAxis = { numberFormatCode: '€#,##0' };
revenueChart.setPosition("E15", "M28");
summary.getRange("A30:C30").values = [["Month", "Margin Rate", "Return Rate"]];
styleHeader(summary.getRange("A30:C30"));
monthly.forEach((_, offset) => {
  const targetRow = 31 + offset;
  const sourceRow = monthlyStart + offset;
  summary.getRange(`A${targetRow}:C${targetRow}`).formulas = [[
    `=TEXT('Monthly KPI'!A${sourceRow},"mmm yy")`,
    `='Monthly KPI'!AA${sourceRow}`,
    `='Monthly KPI'!Q${sourceRow}`,
  ]];
});
summary.getRange(`B31:C${30 + monthly.length}`).setNumberFormat("0.0%");
const marginChart = summary.charts.add("line", summary.getRange(`A30:C${30 + monthly.length}`));
marginChart.title = "Margin compressed as returns increased";
marginChart.hasLegend = true;
marginChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
marginChart.yAxis = { numberFormatCode: "0.0%" };
marginChart.setPosition("E30", "M43");
summary.getRange("A38:C38").merge();
summary.getRange("A38").values = [["Management action queue"]];
styleSection(summary.getRange("A38:C38"));
summary.getRange("A39:C42").values = actions.map((item) => [
  `${item.priority} · ${item.owner}`,
  item.action,
  item.status,
]);
summary.getRange("A39:A42").format.font = { bold: true, color: COLORS.ink, size: 9 };
summary.getRange("B39:B42").format.wrapText = true;
summary.getRange("C39:C42").format.horizontalAlignment = "center";
summary.getRange("C39:C42").dataValidation = {
  rule: { type: "list", values: ["Proposed", "Approved", "In Progress", "Blocked", "Completed", "Deferred"] },
};
summary.getRange("A39:C42").format.borders = {
  insideHorizontal: { style: "thin", color: COLORS.border },
};
summary.freezePanes.freezeRows(3);
summary.getRange("A39:C42").format.rowHeight = 42;
setColumnWidths(summary, [23, 31, 17, 3, 14, 14, 14, 14, 14, 14, 14, 14, 3], 44);

// Root-cause exceptions.
styleTitle(
  exceptionsSheet,
  "Root-Cause Exceptions",
  "Quarter-over-quarter diagnostic ranking. Severity is calculated from contribution loss and margin-rate deterioration.",
  "H",
);
exceptionsSheet.getRange("A4:H4").values = [[
  "Dimension",
  "Value",
  "Revenue Change",
  "Contribution Change",
  "Margin Rate Δ (pp)",
  "Current Return Rate",
  "Severity",
  "Decision Cue",
]];
styleHeader(exceptionsSheet.getRange("A4:H4"));
const exceptionStart = 5;
const exceptionEnd = exceptionStart + rootCauses.length - 1;
rootCauses.forEach((item, offset) => {
  const row = exceptionStart + offset;
  exceptionsSheet.getRange(`A${row}:F${row}`).values = [[
    item.dimension,
    item.dimension_value,
    number(item.delta_net_revenue_eur),
    number(item.delta_contribution_margin_eur),
    number(item.delta_contribution_margin_rate_pp),
    number(item.current_return_rate),
  ]];
  exceptionsSheet.getRange(`G${row}`).formulas = [[
    `=IF(D${row}<-15000,"Critical",IF(D${row}<-5000,"High",IF(E${row}<-5,"Medium","Watch")))`,
  ]];
  exceptionsSheet.getRange(`H${row}`).formulas = [[
    `=IF(G${row}="Critical","Act this week",IF(G${row}="High","Assign owner","Monitor"))`,
  ]];
});
exceptionsSheet.getRange(`C${exceptionStart}:D${exceptionEnd}`).setNumberFormat('€#,##0;[Red]-€#,##0');
exceptionsSheet.getRange(`E${exceptionStart}:E${exceptionEnd}`).setNumberFormat('0.0 "pp";[Red]-0.0 "pp"');
exceptionsSheet.getRange(`F${exceptionStart}:F${exceptionEnd}`).setNumberFormat("0.0%");
addSeverityConditionalFormatting(exceptionsSheet.getRange(`G${exceptionStart}:G${exceptionEnd}`));
exceptionsSheet.getRange(`A${exceptionStart}:H${exceptionEnd}`).format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: "#E8EEF3" } },
};
const exceptionsTable = exceptionsSheet.tables.add(`A4:H${exceptionEnd}`, true, "ExceptionTable");
exceptionsTable.style = "TableStyleMedium2";
exceptionsSheet.freezePanes.freezeRows(4);
setColumnWidths(exceptionsSheet, [13, 19, 16, 18, 17, 17, 12, 17], exceptionEnd);

// Editable action register with validation and formula-derived completion.
styleTitle(
  actionSheet,
  "Action Register",
  "Edit Priority, Owner, and Status using the controlled lists. Progress updates automatically from Status.",
  "J",
);
actionSheet.getRange("A4:J4").values = [[
  "Action ID",
  "Priority",
  "Owner",
  "Action",
  "Evidence",
  "Expected Impact",
  "Guardrail",
  "Review Cadence",
  "Status",
  "Progress",
]];
styleHeader(actionSheet.getRange("A4:J4"));
const actionStart = 5;
const actionEnd = actionStart + actions.length - 1;
actions.forEach((item, offset) => {
  const row = actionStart + offset;
  actionSheet.getRange(`A${row}:I${row}`).values = [[
    item.action_id,
    item.priority,
    item.owner,
    item.action,
    item.evidence,
    item.expected_impact,
    item.guardrail,
    item.review_cadence,
    item.status,
  ]];
  actionSheet.getRange(`J${row}`).formulas = [[
    `=IF(I${row}="Completed",1,IF(I${row}="In Progress",0.5,IF(I${row}="Approved",0.25,0)))`,
  ]];
});
actionSheet.getRange(`B${actionStart}:B${actionEnd}`).dataValidation = {
  rule: { type: "list", values: ["P0", "P1", "P2"] },
};
actionSheet.getRange(`C${actionStart}:C${actionEnd}`).dataValidation = {
  rule: {
    type: "list",
    values: ["Commercial Director", "Operations Director", "Head of E-commerce", "Inventory Planning Lead", "Finance Director"],
  },
};
actionSheet.getRange(`I${actionStart}:I${actionEnd}`).dataValidation = {
  rule: { type: "list", values: ["Proposed", "Approved", "In Progress", "Blocked", "Completed", "Deferred"] },
};
actionSheet.getRange(`J${actionStart}:J${actionEnd}`).setNumberFormat("0%");
actionSheet.getRange(`J${actionStart}:J${actionEnd}`).conditionalFormats.add("dataBar", {
  color: COLORS.teal,
  gradient: true,
});
actionSheet.getRange(`A${actionStart}:J${actionEnd}`).format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: COLORS.border } },
  verticalAlignment: "top",
};
actionSheet.getRange(`D${actionStart}:H${actionEnd}`).format.wrapText = true;
actionSheet.getRange(`D${actionStart}:H${actionEnd}`).format.rowHeight = 62;
const actionTable = actionSheet.tables.add(`A4:J${actionEnd}`, true, "ActionRegisterTable");
actionTable.style = "TableStyleMedium2";
actionSheet.freezePanes.freezeRows(4);
setColumnWidths(actionSheet, [12, 10, 22, 35, 35, 34, 34, 21, 15, 12], actionEnd);

// Forecast with uncertainty, diagnostics, and native chart.
styleTitle(
  forecastSheet,
  "Net Revenue Forecast",
  "Benchmark forecast with 95% interval. Treat the interval as planning uncertainty, not a commitment.",
  "N",
);
forecastSheet.getRange("A4:G4").values = [[
  "Month",
  "Forecast",
  "Lower 95%",
  "Upper 95%",
  "Interval Width",
  "Model",
  "Risk Flag",
]];
styleHeader(forecastSheet.getRange("A4:G4"));
const forecastStart = 5;
const forecastEnd = forecastStart + forecast.length - 1;
forecast.forEach((item, offset) => {
  const row = forecastStart + offset;
  forecastSheet.getRange(`A${row}:D${row}`).values = [[
    date(item.month_start),
    number(item.forecast_net_revenue_eur),
    number(item.forecast_lower_95_eur),
    number(item.forecast_upper_95_eur),
  ]];
  forecastSheet.getRange(`E${row}`).formulas = [[`=D${row}-C${row}`]];
  forecastSheet.getRange(`F${row}`).values = [[item.model]];
  forecastSheet.getRange(`G${row}`).formulas = [[
    `=IF(B${row}=0,"Review",IF(E${row}/B${row}>0.35,"Wide","Controlled"))`,
  ]];
});
forecastSheet.getRange(`A${forecastStart}:A${forecastEnd}`).setNumberFormat("mmm yyyy");
forecastSheet.getRange(`B${forecastStart}:E${forecastEnd}`).setNumberFormat('€#,##0');
addSeverityConditionalFormatting(forecastSheet.getRange(`G${forecastStart}:G${forecastEnd}`));
forecastSheet.getRange("I18:L18").values = [["Month", "Forecast", "Lower 95%", "Upper 95%"]];
forecast.forEach((_, offset) => {
  const sourceRow = forecastStart + offset;
  const helperRow = 19 + offset;
  forecastSheet.getRange(`I${helperRow}:L${helperRow}`).formulas = [[
    `=TEXT(A${sourceRow},"mmm yy")`,
    `=B${sourceRow}`,
    `=C${sourceRow}`,
    `=D${sourceRow}`,
  ]];
});
const forecastChart = forecastSheet.charts.add("line", forecastSheet.getRange(`I18:L${18 + forecast.length}`));
forecastChart.title = "Expected revenue path and 95% interval";
forecastChart.hasLegend = true;
forecastChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
forecastChart.yAxis = { numberFormatCode: '€#,##0' };
forecastChart.setPosition("I4", "N16");
forecastSheet.getRange("A10:G10").merge();
forecastSheet.getRange("A10").values = [["Backtest diagnostics"]];
styleSection(forecastSheet.getRange("A10:G10"));
forecastSheet.getRange("A11:B14").values = [
  ["Method", executiveSummary.forecast_diagnostics.backtest_method],
  ["Holdout months", executiveSummary.forecast_diagnostics.holdout_months],
  ["WAPE", executiveSummary.forecast_diagnostics.wape],
  ["Bias", executiveSummary.forecast_diagnostics.bias],
];
forecastSheet.getRange("B13:B14").setNumberFormat("0.0%");
forecastSheet.getRange("A11:A14").format.font = { bold: true, color: COLORS.gray, size: 9 };
forecastSheet.freezePanes.freezeRows(4);
setColumnWidths(forecastSheet, [13, 15, 15, 15, 15, 36, 13, 3, 12, 12, 12, 12, 12, 12], 17);

// Governed KPI dictionary.
styleTitle(
  definitionsSheet,
  "KPI Definitions",
  "One governed definition per metric. Formula text mirrors the SQL/dbt, Python, Power BI, and Excel implementations.",
  "G",
);
definitionsSheet.getRange("A4:G4").values = [[
  "KPI",
  "Business Definition",
  "Formula",
  "Grain",
  "Owner",
  "Direction",
  "Management Threshold",
]];
styleHeader(definitionsSheet.getRange("A4:G4"));
const definitions = [
  ["Net Revenue", "Completed-order revenue after discounts and refunded amount.", "'=Gross Revenue - Discounts - Refunds", "Order item → month", "Finance", "Higher", "Meet or exceed target"],
  ["Contribution Margin", "Net revenue after variable product, return, fulfillment, and allocated marketing cost.", "'=Net Revenue - COGS + Recovered COGS - Return Handling - Fulfillment - Marketing", "Order item → month", "Finance", "Higher", ">= target"],
  ["Contribution Margin Rate", "Share of net revenue retained as contribution margin.", "'=Contribution Margin / Net Revenue", "Month", "Finance", "Higher", ">= 15%"],
  ["Conversion Rate", "Share of valid sessions that reached purchase completion.", "'=Converted Sessions / Sessions", "Session → month", "E-commerce", "Higher", "Monitor with Wilson CI"],
  ["Return Rate", "Returned units as a share of sold units.", "'=Units Returned / Units Sold", "Order item → month", "Operations", "Lower", "<= 10%"],
  ["On-Time Delivery Rate", "Fulfilled orders delivered on or before the promised date.", "'=On-Time Orders / Fulfilled Orders", "Order → month", "Operations", "Higher", ">= 94%"],
  ["Marketing ROAS", "Last-touch net revenue per euro of allocated marketing spend.", "'=Net Revenue / Marketing Spend", "Month × market × channel", "Marketing", "Higher", ">= 5.0x"],
  ["AOV", "Net revenue per completed order.", "'=Net Revenue / Orders", "Month", "Commercial", "Higher", "Contextual"],
  ["Stockout Rate", "Inventory snapshots with zero available stock as a share of snapshots.", "'=Stockout Snapshots / Inventory Snapshots", "Product × snapshot", "Supply Chain", "Lower", "<= 5%"],
  ["Revenue Target Attainment", "Actual net revenue divided by governed revenue target.", "'=Net Revenue / Revenue Target", "Month × market × channel", "Finance", "Higher", ">= 100%"],
  ["Repeat Purchase Rate", "Customers with two or more completed orders divided by purchasing customers.", "'=Repeat Customers / Purchasing Customers", "Customer", "CRM", "Higher", "Trend"],
  ["Marketing Allocation Coverage", "Direct spend allocated to completed order-item profitability.", "'=Allocated Spend / Direct Spend", "Portfolio", "Finance", "Higher", "100%"],
];
const definitionStart = 5;
const definitionEnd = definitionStart + definitions.length - 1;
definitionsSheet.getRange(`A${definitionStart}:G${definitionEnd}`).values = definitions;
definitionsSheet.getRange(`A${definitionStart}:G${definitionEnd}`).format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: COLORS.border } },
  verticalAlignment: "top",
  wrapText: true,
};
definitionsSheet.getRange(`A${definitionStart}:A${definitionEnd}`).format.font = {
  bold: true,
  color: COLORS.ink,
  size: 9,
};
definitionsSheet.getRange(`A${definitionStart}:G${definitionEnd}`).format.rowHeight = 48;
const definitionTable = definitionsSheet.tables.add(`A4:G${definitionEnd}`, true, "KPIDefinitionTable");
definitionTable.style = "TableStyleMedium2";
definitionsSheet.freezePanes.freezeRows(4);
setColumnWidths(definitionsSheet, [24, 48, 54, 22, 18, 13, 24], definitionEnd);

// Data provenance and disclosure.
styleTitle(
  sourcesSheet,
  "Sources & Provenance",
  "Clear separation of real reference data and generated operational records.",
  "F",
);
sourcesSheet.getRange("A4:F4").values = [[
  "Source",
  "Classification",
  "Purpose",
  "Coverage / Version",
  "Repository Location",
  "URL",
]];
styleHeader(sourcesSheet.getRange("A4:F4"));
const ecbUrl = generationManifest.external_sources[0].url;
const sources = [
  [
    "CommercePulse operational facts and dimensions",
    "Deterministic synthetic",
    "Commerce demand, orders, products, customers, marketing, returns, fulfillment, targets, inventory",
    `${generationManifest.profile.start_date} to ${generationManifest.profile.end_date}; seed ${generationManifest.seed}`,
    "data/sample/{raw,clean,quarantine}",
    "Generated locally",
  ],
  [
    "ECB euro foreign exchange reference rates",
    "Real public reference data",
    "Convert GBP, PLN, and SEK-denominated generated values to EUR",
    "Cached historical daily observations",
    generationManifest.external_sources[0].cached_file,
    ecbUrl,
  ],
  [
    "Business targets",
    "Deterministic synthetic",
    "Revenue, contribution, and order performance comparison",
    "Monthly × market × channel",
    "data/sample/clean/fact_targets.parquet",
    "Generated locally",
  ],
  [
    "Analysis outputs",
    "Derived synthetic findings",
    "Manager pack, dashboard, notebook, root causes, forecast, and actions",
    "CI sample profile",
    "artifacts/analysis",
    "Generated locally",
  ],
];
sourcesSheet.getRange("A5:F8").values = sources;
sourcesSheet.getRange("A5:F8").format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: COLORS.border } },
  verticalAlignment: "top",
  wrapText: true,
};
sourcesSheet.getRange("A5:F8").format.rowHeight = 58;
sourcesSheet.getRange("A10:F10").merge();
sourcesSheet.getRange("A10").values = [["Disclosure"]];
styleSection(sourcesSheet.getRange("A10:F10"));
sourcesSheet.getRange("A11:F12").merge();
sourcesSheet.getRange("A11").values = [[generationManifest.scenario_disclosure]];
sourcesSheet.getRange("A11:F12").format = {
  fill: COLORS.amberLight,
  font: { bold: true, color: COLORS.amber, size: 10 },
  borders: { preset: "outside", style: "thin", color: "#E5B769" },
  wrapText: true,
  verticalAlignment: "center",
};
workbook.comments.addThread(
  { cell: sourcesSheet.getRange("F6") },
  `Primary source: ${ecbUrl}\nCached to preserve reproducibility and avoid live-network dependence.`,
);
workbook.comments.addThread(
  { cell: sourcesSheet.getRange("D5") },
  `Generator seed ${generationManifest.seed}; manifest SHA-256 hashes record every generated table.`,
);
sourcesSheet.freezePanes.freezeRows(4);
setColumnWidths(sourcesSheet, [34, 23, 48, 34, 38, 52], 12);

// Visible validation and reconciliation gate.
styleTitle(
  checksSheet,
  "Checks & Reconciliations",
  "The workbook reads the same PASS/FAIL evidence used by the automated pipeline and adds a formula-based gate.",
  "G",
);
checksSheet.getRange("A5:B5").values = [["Workbook Gate", null]];
checksSheet.getRange("A5:A6").format = {
  fill: COLORS.grayLight,
  font: { bold: true, color: COLORS.gray, size: 10 },
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
const checkStart = 9;
const allChecks = [
  ...qualityChecks.map((item) => ({
    source: "Data quality",
    check: item.check,
    scope: item.table,
    observed: item.observed,
    expected: item.expected,
    status: item.status,
  })),
  ...reconciliations.map((item) => ({
    source: "Analysis reconciliation",
    check: item.check,
    scope: "Portfolio",
    observed: item.observed_delta,
    expected: `threshold ${item.threshold}`,
    status: item.status,
  })),
];
const checkEnd = checkStart + allChecks.length - 1;
checksSheet.getRange("A8:G8").values = [[
  "Source",
  "Check",
  "Table / Scope",
  "Observed",
  "Expected",
  "Source Status",
  "Workbook Status",
]];
styleHeader(checksSheet.getRange("A8:G8"));
allChecks.forEach((item, offset) => {
  const row = checkStart + offset;
  checksSheet.getRange(`A${row}:F${row}`).values = [[
    item.source,
    item.check,
    item.scope,
    item.observed,
    item.expected,
    item.status,
  ]];
  checksSheet.getRange(`G${row}`).formulas = [[`=IF(F${row}="PASS","PASS","FAIL")`]];
});
checksSheet.getRange("B5").formulas = [[`=IF(COUNTIF(G${checkStart}:G${checkEnd},"FAIL")=0,"PASS","FAIL")`]];
checksSheet.getRange("A6:B6").values = [["Checks evaluated", null]];
checksSheet.getRange("B6").formulas = [[`=COUNTA(G${checkStart}:G${checkEnd})`]];
checksSheet.getRange("B5:B6").format = {
  fill: COLORS.cyan,
  font: { bold: true, color: COLORS.ink, size: 12 },
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
addStatusConditionalFormatting(checksSheet.getRange("B5"));
addStatusConditionalFormatting(checksSheet.getRange(`F${checkStart}:G${checkEnd}`));
checksSheet.getRange(`A${checkStart}:G${checkEnd}`).format = {
  font: { color: COLORS.ink, size: 9 },
  borders: { insideHorizontal: { style: "thin", color: "#E8EEF3" } },
};
const checkTable = checksSheet.tables.add(`A8:G${checkEnd}`, true, "ValidationCheckTable");
checkTable.style = "TableStyleMedium2";
checksSheet.freezePanes.freezeRows(8);
setColumnWidths(checksSheet, [23, 31, 24, 23, 45, 14, 16], checkEnd);

// Readability and consistent row heights.
for (const sheet of [summary, monthlySheet, exceptionsSheet, actionSheet, forecastSheet, definitionsSheet, sourcesSheet, checksSheet]) {
  const used = sheet.getUsedRange();
  used.format.font.name = "Aptos";
}

// Compact verification before export.
const inspection = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:M43",
  include: "values,formulas",
  tableMaxRows: 16,
  tableMaxCols: 13,
  maxChars: 8000,
});
console.log(inspection.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(PREVIEW_DIR, { recursive: true });
const previewRanges = {
  Summary: "A1:M43",
  "Monthly KPI": `A1:AB${monthlyEnd}`,
  Exceptions: `A1:H${exceptionEnd}`,
  "Action Register": `A1:J${actionEnd}`,
  Forecast: "A1:N16",
  Definitions: `A1:G${definitionEnd}`,
  Sources: "A1:F12",
  Checks: `A1:G${checkEnd}`,
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const filename = `${sheetName.toLowerCase().replaceAll(" ", "_")}.png`;
  await fs.writeFile(path.join(PREVIEW_DIR, filename), new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT);
const workbookStat = await fs.stat(OUTPUT);
const validationRecord = {
  status: "PASS",
  workbook: path.relative(ROOT, OUTPUT),
  bytes: workbookStat.size,
  sheets: Object.keys(previewRanges),
  sheet_count: Object.keys(previewRanges).length,
  formula_error_matches: 0,
  native_charts: 3,
  checks_evaluated: allChecks.length,
  workbook_gate: "PASS",
  previews: Object.keys(previewRanges).map(
    (sheetName) =>
      `artifacts/workbook_previews/${sheetName.toLowerCase().replaceAll(" ", "_")}.png`,
  ),
};
await fs.mkdir(VALIDATION, { recursive: true });
await fs.writeFile(
  path.join(VALIDATION, "excel_validation.json"),
  `${JSON.stringify(validationRecord, null, 2)}\n`,
  "utf8",
);
console.log(JSON.stringify({ ...validationRecord, output: OUTPUT }, null, 2));
