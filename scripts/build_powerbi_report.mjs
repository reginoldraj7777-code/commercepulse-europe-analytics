import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const powerbiRoot = path.join(root, "powerbi");
const reportRoot = path.join(powerbiRoot, "CommercePulse.Report");
const definitionRoot = path.join(reportRoot, "definition");
const pagesRoot = path.join(definitionRoot, "pages");
const themeName = "CommercePulseExecutive-20260813.json";

const schemas = {
  pbip: "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  platform:
    "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  definition:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  version:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
  report:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.1.0/schema.json",
  pages:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
  page: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  visual:
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
};

const literal = {
  bool: (value) => ({ expr: { Literal: { Value: String(value) } } }),
  number: (value, integer = false) => ({
    expr: { Literal: { Value: `${value}${integer ? "L" : "D"}` } },
  }),
  string: (value) => ({ expr: { Literal: { Value: `'${String(value).replaceAll("'", "''")}'` } } }),
  color: (value) => ({
    solid: { color: { expr: { Literal: { Value: `'${value}'` } } } },
  }),
};

function stableId(value) {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, 20);
}

function measureField(name) {
  return {
    Measure: {
      Expression: { SourceRef: { Entity: "KPI Measures" } },
      Property: name,
    },
  };
}

function columnField(table, name) {
  return {
    Column: {
      Expression: { SourceRef: { Entity: table } },
      Property: name,
    },
  };
}

function projection(field, table, name) {
  return { field, queryRef: `${table}.${name}`, nativeQueryRef: name };
}

function measureProjection(name) {
  return projection(measureField(name), "KPI Measures", name);
}

function columnProjection(table, name) {
  return projection(columnField(table, name), table, name);
}

function position(x, y, width, height, z) {
  return { x, y, z, width, height, tabOrder: z };
}

function containerObjects(title, altText) {
  const objects = {
    background: [
      {
        properties: {
          show: literal.bool(true),
          color: literal.color("#FFFFFF"),
          transparency: literal.number(0),
        },
      },
    ],
    border: [
      {
        properties: {
          show: literal.bool(true),
          color: literal.color("#D9DEE8"),
          radius: literal.number(8),
          width: literal.number(1),
        },
      },
    ],
    padding: [
      {
        properties: {
          top: literal.number(8),
          bottom: literal.number(8),
          left: literal.number(10),
          right: literal.number(10),
        },
      },
    ],
    visualHeader: [{ properties: { show: literal.bool(true) } }],
    general: [{ properties: { altText: literal.string(altText ?? title) } }],
  };
  if (title) {
    objects.title = [
      {
        properties: {
          show: literal.bool(true),
          text: literal.string(title),
          heading: literal.string("Heading3"),
          titleWrap: literal.bool(true),
          fontFamily: literal.string("Segoe UI Semibold"),
          fontSize: literal.number(12),
          fontColor: literal.color("#172033"),
          bold: literal.bool(true),
        },
      },
    ];
    objects.subTitle = [{ properties: { show: literal.bool(false) } }];
  }
  return objects;
}

function visualRoot(pageKey, visualKey, visualType, pos, visual) {
  const name = stableId(`${pageKey}:${visualKey}`);
  return {
    name,
    payload: {
      $schema: schemas.visual,
      name,
      position: pos,
      visual: { visualType, drillFilterOtherVisuals: true, ...visual },
    },
  };
}

function textbox(pageKey, visualKey, pos, paragraphs, options = {}) {
  const name = stableId(`${pageKey}:${visualKey}`);
  const textParagraphs = paragraphs.map((paragraph) => ({
    textRuns: [
      {
        value: paragraph.value,
        textStyle: {
          fontFamily: paragraph.fontFamily ?? "Segoe UI",
          fontSize: `${paragraph.fontSize ?? 12}px`,
          color: paragraph.color ?? "#172033",
          fontWeight: paragraph.bold ? "bold" : "normal",
        },
      },
    ],
    horizontalTextAlignment: paragraph.alignment ?? "left",
  }));
  return {
    name,
    payload: {
      $schema: schemas.visual,
      name,
      position: pos,
      visual: {
        visualType: "textbox",
        objects: { general: [{ properties: { paragraphs: textParagraphs } }] },
        visualContainerObjects: {
          background: [
            {
              properties: {
                show: literal.bool(options.background !== false),
                color: literal.color(options.backgroundColor ?? "#FFFFFF"),
                transparency: literal.number(options.transparency ?? 0),
              },
            },
          ],
          border: [{ properties: { show: literal.bool(options.border ?? false) } }],
          padding: [
            {
              properties: {
                top: literal.number(options.padding ?? 8),
                bottom: literal.number(options.padding ?? 8),
                left: literal.number(options.padding ?? 12),
                right: literal.number(options.padding ?? 12),
              },
            },
          ],
          general: [
            {
              properties: {
                altText: literal.string(
                  options.altText ?? paragraphs.map((paragraph) => paragraph.value).join(" "),
                ),
              },
            },
          ],
        },
      },
    },
  };
}

function header(pageKey, title, subtitle) {
  return textbox(
    pageKey,
    "header",
    position(0, 0, 1280, 70, 0),
    [
      { value: title, fontSize: 25, color: "#FFFFFF", bold: true },
      { value: subtitle, fontSize: 11, color: "#D7E4FF" },
    ],
    {
      backgroundColor: "#172033",
      border: false,
      padding: 10,
      altText: `${title}. ${subtitle}`,
    },
  );
}

function card(pageKey, visualKey, pos, measures, altText) {
  return visualRoot(pageKey, visualKey, "cardVisual", pos, {
    query: {
      queryState: { Data: { projections: measures.map(measureProjection) } },
    },
    objects: {
      outline: [
        { properties: { show: literal.bool(false) }, selector: { id: "default" } },
      ],
      value: [
        {
          properties: {
            fontSize: literal.number(26),
            bold: literal.bool(true),
            fontColor: literal.color("#172033"),
          },
          selector: { id: "default" },
        },
      ],
      label: [
        {
          properties: { show: literal.bool(true), fontSize: literal.number(11) },
          selector: { id: "default" },
        },
      ],
      padding: [
        {
          properties: { paddingUniform: literal.number(6, true) },
          selector: { id: "default" },
        },
      ],
    },
    visualContainerObjects: containerObjects(null, altText),
  });
}

function chart(
  pageKey,
  visualKey,
  pos,
  visualType,
  title,
  category,
  measures,
  options = {},
) {
  const queryState = {
    Category: { projections: [columnProjection(category.table, category.column)] },
    Y: { projections: measures.map(measureProjection) },
  };
  if (options.series) {
    queryState.Series = {
      projections: [columnProjection(options.series.table, options.series.column)],
    };
  }
  const query = { queryState };
  if (options.sortBy) {
    query.sortDefinition = {
      sort: [{ field: measureField(options.sortBy), direction: options.sortDirection ?? "Descending" }],
      isDefaultSort: false,
    };
  }
  return visualRoot(pageKey, visualKey, visualType, pos, {
    query,
    visualContainerObjects: containerObjects(title, options.altText ?? title),
  });
}

function table(pageKey, visualKey, pos, title, fields, altText) {
  const projections = fields.map((field) =>
    field.type === "measure"
      ? measureProjection(field.name)
      : columnProjection(field.table, field.name),
  );
  return visualRoot(pageKey, visualKey, "tableEx", pos, {
    query: { queryState: { Values: { projections } } },
    objects: {
      columnHeaders: [
        {
          properties: {
            columnAdjustment: literal.string("growToFit"),
            autoSizeColumnWidth: literal.bool(true),
          },
        },
      ],
    },
    visualContainerObjects: containerObjects(title, altText ?? title),
  });
}

const summary = JSON.parse(
  await fs.readFile(path.join(root, "artifacts", "analysis", "executive_summary.json"), "utf8"),
);
const actionText = summary.actions
  .slice(0, 4)
  .map((action) => `${action.priority} · ${action.owner}: ${action.action} Evidence: ${action.evidence}`)
  .join("\n\n");

const pages = [
  {
    key: "executive",
    displayName: "Executive Overview",
    visuals: [
      header(
        "executive",
        "CommercePulse Europe",
        "Executive growth quality · governed EUR economics · generated business scenario",
      ),
      card(
        "executive",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["Net Revenue", "Contribution Margin", "Contribution Margin Rate", "Net Revenue QoQ"],
        "Net revenue, contribution margin, contribution margin rate, and quarter over quarter revenue growth.",
      ),
      chart(
        "executive",
        "trend",
        position(20, 225, 610, 250, 2000),
        "lineChart",
        "Revenue and contribution trend",
        { table: "Date", column: "Month Start" },
        ["Net Revenue", "Contribution Margin"],
      ),
      chart(
        "executive",
        "market",
        position(650, 225, 610, 250, 3000),
        "clusteredBarChart",
        "Contribution margin by market",
        { table: "Market", column: "Market Code" },
        ["Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      table(
        "executive",
        "scorecard",
        position(20, 493, 800, 207, 4000),
        "Management scorecard",
        [
          { type: "column", table: "Market", name: "Market Code" },
          { type: "measure", name: "Net Revenue" },
          { type: "measure", name: "Contribution Margin" },
          { type: "measure", name: "Contribution Margin Rate" },
          { type: "measure", name: "Return Rate" },
        ],
      ),
      textbox(
        "executive",
        "readout",
        position(840, 493, 420, 207, 5000),
        [
          { value: "HOW TO READ", fontSize: 11, color: "#2563EB", bold: true },
          {
            value:
              "Lead with contribution, not revenue alone. Use the market chart to isolate mix, then open Root Cause & Actions for owners and guardrails. Rates are weighted from governed numerators and denominators.",
            fontSize: 13,
          },
        ],
        { backgroundColor: "#EEF4FF", border: true, altText: "Executive interpretation guidance." },
      ),
    ],
  },
  {
    key: "growth",
    displayName: "Growth & Profitability",
    visuals: [
      header(
        "growth",
        "Growth & Profitability",
        "Revenue quality, channel efficiency, product mix, and plan attainment",
      ),
      card(
        "growth",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["Net Revenue", "Orders", "Average Order Value", "Attributed ROAS"],
      ),
      chart(
        "growth",
        "monthly",
        position(20, 225, 610, 250, 2000),
        "lineChart",
        "Revenue and paid-media trend",
        { table: "Date", column: "Month Start" },
        ["Net Revenue", "Marketing Spend"],
      ),
      chart(
        "growth",
        "channels",
        position(650, 225, 610, 250, 3000),
        "clusteredBarChart",
        "Channel contribution and revenue",
        { table: "Channel", column: "Channel Name" },
        ["Net Revenue", "Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      chart(
        "growth",
        "categories",
        position(20, 493, 610, 207, 4000),
        "clusteredBarChart",
        "Category contribution margin",
        { table: "Product", column: "Category" },
        ["Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      table(
        "growth",
        "channel_table",
        position(650, 493, 610, 207, 5000),
        "Channel economics",
        [
          { type: "column", table: "Channel", name: "Channel Name" },
          { type: "measure", name: "Orders" },
          { type: "measure", name: "Net Revenue" },
          { type: "measure", name: "Marketing Spend" },
          { type: "measure", name: "Attributed ROAS" },
          { type: "measure", name: "Contribution Margin Rate" },
        ],
      ),
    ],
  },
  {
    key: "customer",
    displayName: "Customer & Retention",
    visuals: [
      header(
        "customer",
        "Customer & Retention",
        "Acquisition quality, repeat behavior, value segments, and cohort durability",
      ),
      card(
        "customer",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["Purchasing Customers", "Repeat Purchase Rate", "Cohort Retention Rate", "Average Order Value"],
      ),
      chart(
        "customer",
        "cohorts",
        position(20, 225, 610, 250, 2000),
        "lineChart",
        "Cohort retention by month since first purchase",
        { table: "Customer Cohorts", column: "Month Index" },
        ["Cohort Retention Rate"],
        { series: { table: "Customer Cohorts", column: "Cohort Month" } },
      ),
      chart(
        "customer",
        "segments",
        position(650, 225, 610, 250, 3000),
        "clusteredBarChart",
        "Net revenue by customer segment",
        { table: "Customer", column: "Customer Segment" },
        ["Net Revenue"],
        { sortBy: "Net Revenue" },
      ),
      chart(
        "customer",
        "loyalty",
        position(20, 493, 610, 207, 4000),
        "clusteredBarChart",
        "Orders by loyalty tier",
        { table: "Customer", column: "Loyalty Tier" },
        ["Orders"],
        { sortBy: "Orders" },
      ),
      table(
        "customer",
        "segment_table",
        position(650, 493, 610, 207, 5000),
        "Segment value and retention guardrails",
        [
          { type: "column", table: "Customer", name: "Customer Segment" },
          { type: "measure", name: "Purchasing Customers" },
          { type: "measure", name: "Orders" },
          { type: "measure", name: "Average Order Value" },
          { type: "measure", name: "Return Rate" },
          { type: "measure", name: "Contribution Margin Rate" },
        ],
      ),
    ],
  },
  {
    key: "product",
    displayName: "Product & Conversion",
    visuals: [
      header(
        "product",
        "Product & Conversion",
        "Digital funnel, mobile performance, category economics, and conversion quality",
      ),
      card(
        "product",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["Sessions", "Conversion Rate", "Average Page Load MS", "Return Rate"],
      ),
      chart(
        "product",
        "funnel",
        position(20, 225, 610, 250, 2000),
        "clusteredBarChart",
        "Commerce conversion funnel",
        { table: "Funnel", column: "Stage" },
        ["Funnel Sessions"],
        { sortBy: "Funnel Sessions", sortDirection: "Descending" },
      ),
      chart(
        "product",
        "device",
        position(650, 225, 610, 250, 3000),
        "clusteredBarChart",
        "Conversion rate by device",
        { table: "Sessions", column: "Device Type" },
        ["Conversion Rate"],
        { sortBy: "Conversion Rate" },
      ),
      chart(
        "product",
        "sessions_trend",
        position(20, 493, 610, 207, 4000),
        "lineChart",
        "Sessions and conversions over time",
        { table: "Date", column: "Month Start" },
        ["Sessions", "Converted Sessions"],
      ),
      table(
        "product",
        "category_table",
        position(650, 493, 610, 207, 5000),
        "Category growth-quality scorecard",
        [
          { type: "column", table: "Product", name: "Category" },
          { type: "column", table: "Product", name: "Subcategory" },
          { type: "measure", name: "Net Revenue" },
          { type: "measure", name: "Units Sold" },
          { type: "measure", name: "Return Rate" },
          { type: "measure", name: "Contribution Margin" },
        ],
      ),
    ],
  },
  {
    key: "operations",
    displayName: "Operations & Returns",
    visuals: [
      header(
        "operations",
        "Operations & Returns",
        "Delivery reliability, return economics, inventory exceptions, and recoverable opportunity",
      ),
      card(
        "operations",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["On Time Delivery Rate", "Shipping Cost Per Order", "Return Rate", "Stockout Rate", "Estimated Lost Revenue"],
      ),
      chart(
        "operations",
        "hub",
        position(20, 225, 610, 250, 2000),
        "clusteredBarChart",
        "On-time delivery by fulfillment hub",
        { table: "Operations", column: "Fulfillment Hub" },
        ["On Time Delivery Rate"],
        { sortBy: "On Time Delivery Rate" },
      ),
      chart(
        "operations",
        "carrier",
        position(650, 225, 610, 250, 3000),
        "clusteredBarChart",
        "Carrier service level",
        { table: "Operations", column: "Carrier" },
        ["On Time Delivery Rate"],
        { sortBy: "On Time Delivery Rate" },
      ),
      chart(
        "operations",
        "stockout",
        position(20, 493, 610, 207, 4000),
        "clusteredBarChart",
        "Estimated lost revenue by category",
        { table: "Product", column: "Category" },
        ["Estimated Lost Revenue"],
        { sortBy: "Estimated Lost Revenue" },
      ),
      table(
        "operations",
        "market_table",
        position(650, 493, 610, 207, 5000),
        "Market exception watchlist",
        [
          { type: "column", table: "Market", name: "Market Code" },
          { type: "measure", name: "On Time Delivery Rate" },
          { type: "measure", name: "Shipping Cost Per Order" },
          { type: "measure", name: "Return Rate" },
          { type: "measure", name: "Stockout Rate" },
          { type: "measure", name: "Estimated Lost Revenue" },
        ],
      ),
    ],
  },
  {
    key: "actions",
    displayName: "Root Cause & Actions",
    visuals: [
      header(
        "actions",
        "Root Cause & Actions",
        "Ranked drivers, accountable owners, evidence, impact hypotheses, and operating guardrails",
      ),
      card(
        "actions",
        "kpis",
        position(20, 88, 1240, 120, 1000),
        ["Contribution Margin QoQ Delta", "Margin Rate QoQ Delta PP", "Net Revenue Variance", "Estimated Lost Revenue"],
      ),
      chart(
        "actions",
        "market",
        position(20, 225, 400, 235, 2000),
        "clusteredBarChart",
        "Contribution by market",
        { table: "Market", column: "Market Code" },
        ["Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      chart(
        "actions",
        "channel",
        position(440, 225, 400, 235, 3000),
        "clusteredBarChart",
        "Contribution by channel",
        { table: "Channel", column: "Channel Name" },
        ["Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      chart(
        "actions",
        "category",
        position(860, 225, 400, 235, 4000),
        "clusteredBarChart",
        "Contribution by category",
        { table: "Product", column: "Category" },
        ["Contribution Margin"],
        { sortBy: "Contribution Margin" },
      ),
      textbox(
        "actions",
        "register",
        position(20, 478, 1240, 222, 5000),
        [
          { value: "VALIDATED SAMPLE ACTION REGISTER", fontSize: 11, color: "#2563EB", bold: true },
          { value: actionText, fontSize: 11, color: "#172033" },
          {
            value:
              "Scenario disclosure: these findings describe deterministic generated operations. Refresh the narrative after rebuilding the pipeline; validate interventions with owned pilots or experiments.",
            fontSize: 10,
            color: "#5F6B7A",
          },
        ],
        {
          backgroundColor: "#F7F9FC",
          border: true,
          padding: 10,
          altText: "Sample management actions with priority, owner, evidence, and scenario disclosure.",
        },
      ),
    ],
  },
];

await fs.rm(reportRoot, { recursive: true, force: true });
await fs.mkdir(pagesRoot, { recursive: true });
await fs.mkdir(path.join(reportRoot, "StaticResources", "RegisteredResources"), {
  recursive: true,
});

const pbip = {
  $schema: schemas.pbip,
  version: "1.0",
  artifacts: [{ report: { path: "CommercePulse.Report" } }],
  settings: { enableAutoRecovery: true },
};
const platform = {
  $schema: schemas.platform,
  metadata: { type: "Report", displayName: "CommercePulse Europe" },
  config: { version: "2.0", logicalId: "da4e429e-e684-45ab-97ab-78b89647c4fd" },
};
const definition = {
  $schema: schemas.definition,
  version: "4.0",
  datasetReference: { byPath: { path: "../CommercePulse.SemanticModel" } },
};
const report = {
  $schema: schemas.report,
  themeCollection: {
    customTheme: {
      name: themeName,
      reportVersionAtImport: { visual: "2.6.0", report: "3.1.0", page: "2.3.0" },
      type: "RegisteredResources",
    },
  },
  resourcePackages: [
    {
      name: "RegisteredResources",
      type: "RegisteredResources",
      items: [{ name: themeName, path: themeName, type: "CustomTheme" }],
    },
  ],
  settings: {
    useStylableVisualContainerHeader: true,
    exportDataMode: "AllowSummarized",
  },
};
const theme = {
  name: themeName,
  dataColors: [
    "#2563EB",
    "#D99A16",
    "#EA7A1F",
    "#6E7F2B",
    "#C84B83",
    "#0F8B8D",
    "#6B5FD2",
    "#8A5A44",
  ],
  good: "#2F855A",
  neutral: "#D99A16",
  bad: "#C53030",
  maximum: "#2563EB",
  center: "#D99A16",
  minimum: "#DCE8FF",
  null: "#A0AEC0",
  foreground: "#172033",
  background: "#FFFFFF",
  tableAccent: "#2563EB",
  textClasses: {
    callout: { fontFace: "Segoe UI Semibold", fontSize: 26, color: "#172033" },
    title: { fontFace: "Segoe UI Semibold", fontSize: 12, color: "#172033" },
    header: { fontFace: "Segoe UI Semibold", fontSize: 12, color: "#172033" },
    label: { fontFace: "Segoe UI", fontSize: 10, color: "#344054" },
  },
};

await fs.writeFile(path.join(powerbiRoot, "CommercePulse.pbip"), `${JSON.stringify(pbip, null, 2)}\n`);
await fs.writeFile(path.join(reportRoot, ".platform"), `${JSON.stringify(platform, null, 2)}\n`);
await fs.writeFile(path.join(reportRoot, "definition.pbir"), `${JSON.stringify(definition, null, 2)}\n`);
await fs.writeFile(
  path.join(definitionRoot, "version.json"),
  `${JSON.stringify({ $schema: schemas.version, version: "2.0.0" }, null, 2)}\n`,
);
await fs.writeFile(path.join(definitionRoot, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
await fs.writeFile(
  path.join(reportRoot, "StaticResources", "RegisteredResources", themeName),
  `${JSON.stringify(theme, null, 2)}\n`,
);

const pageOrder = pages.map((page) => stableId(`page:${page.key}`));
await fs.writeFile(
  path.join(pagesRoot, "pages.json"),
  `${JSON.stringify(
    { $schema: schemas.pages, pageOrder, activePageName: pageOrder[0] },
    null,
    2,
  )}\n`,
);

for (const [index, page] of pages.entries()) {
  const pageName = pageOrder[index];
  const pageRoot = path.join(pagesRoot, pageName);
  await fs.mkdir(path.join(pageRoot, "visuals"), { recursive: true });
  await fs.writeFile(
    path.join(pageRoot, "page.json"),
    `${JSON.stringify(
      {
        $schema: schemas.page,
        name: pageName,
        displayName: page.displayName,
        displayOption: "FitToPage",
        height: 720,
        width: 1280,
        objects: {
          background: [
            {
              properties: {
                color: literal.color("#F3F6FA"),
                transparency: literal.number(0),
              },
            },
          ],
          outspace: [
            {
              properties: {
                color: literal.color("#172033"),
                transparency: literal.number(0),
              },
            },
          ],
        },
      },
      null,
      2,
    )}\n`,
  );
  for (const visual of page.visuals) {
    const visualRootPath = path.join(pageRoot, "visuals", visual.name);
    await fs.mkdir(visualRootPath, { recursive: true });
    await fs.writeFile(
      path.join(visualRootPath, "visual.json"),
      `${JSON.stringify(visual.payload, null, 2)}\n`,
    );
  }
}

process.stdout.write(`${path.join(powerbiRoot, "CommercePulse.pbip")}\n`);
