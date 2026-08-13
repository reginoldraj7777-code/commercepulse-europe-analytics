import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "../powerbi/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js";
import { StdioClientTransport } from "../powerbi/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const modelRoot = path.join(root, "powerbi", "CommercePulse.SemanticModel");
const definitionRoot = path.join(modelRoot, "definition");
const mcpCommand = path.join(
  root,
  "powerbi",
  "node_modules",
  ".bin",
  "powerbi-modeling-mcp",
);

const transport = new StdioClientTransport({
  command: mcpCommand,
  args: ["--start", "--compatibility=powerbi"],
  stderr: "pipe",
});
const client = new Client({ name: "commercepulse-model-builder", version: "1.0.0" });

function parseToolResponse(response, label) {
  if (response.isError) {
    throw new Error(`${label} failed: ${JSON.stringify(response.content)}`);
  }
  const textPart = response.content?.find((item) => item.type === "text");
  if (!textPart) return {};
  const parsed = JSON.parse(textPart.text);
  const serialized = JSON.stringify(parsed);
  if (/"success":false|"status":"failed"|"error"/i.test(serialized)) {
    throw new Error(`${label} failed: ${textPart.text}`);
  }
  process.stdout.write(`${label}: ok\n`);
  return parsed;
}

async function call(name, request, label = `${name}.${request.operation}`) {
  const response = await client.callTool({ name, arguments: { request } });
  return parseToolResponse(response, label);
}

function column(name, sourceColumn, dataType, options = {}) {
  return {
    name,
    sourceColumn,
    dataType,
    isNullable: options.isNullable ?? true,
    isHidden: options.isHidden ?? false,
    isKey: options.isKey ?? false,
    isUnique: options.isUnique ?? false,
    formatString: options.formatString ?? null,
    summarizeBy: options.summarizeBy ?? (dataType === "String" || dataType === "Boolean" ? "None" : "Sum"),
    description: options.description ?? null,
  };
}

function postgresTable(name, item, columns, description) {
  const mExpression = `let
    Source = PostgreSQL.Database(Server, Database, [CreateNavigationProperties = false]),
    Data = Source{[Schema = "portfolio", Item = "${item}"]}[Data]
in
    Data`;
  return {
    name,
    description,
    mode: "Import",
    partitionName: name,
    mExpression,
    columns,
  };
}

const tables = [
  postgresTable(
    "Date",
    "dim_date",
    [
      column("Date Key", "date_key", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Date", "date", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Year", "year", "Int64", { summarizeBy: "None" }),
      column("Quarter", "quarter", "String"),
      column("Month Number", "month_number", "Int64", { summarizeBy: "None" }),
      column("Month Name", "month_name", "String"),
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Week Start", "week_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("ISO Week", "iso_week", "Int64", { summarizeBy: "None" }),
      column("Day Name", "day_name", "String"),
      column("Is Weekend", "is_weekend", "Boolean"),
      column("Is Month End", "is_month_end", "Boolean"),
    ],
    "Conformed European calendar used for all active time relationships.",
  ),
  postgresTable(
    "Market",
    "dim_market",
    [
      column("Market Key", "market_key", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Market Code", "market_code", "String"),
      column("Market Name", "market_name", "String"),
      column("Region Cluster", "region_cluster", "String"),
      column("Currency Code", "currency_code", "String"),
      column("VAT Rate", "vat_rate", "Double", { formatString: "0.0%", summarizeBy: "None" }),
      column("Fulfillment Hub", "fulfillment_hub", "String"),
    ],
    "Ten European commerce markets with local-currency and fulfillment attributes.",
  ),
  postgresTable(
    "Channel",
    "dim_channel",
    [
      column("Channel Key", "channel_key", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Channel Name", "channel_name", "String"),
      column("Channel Group", "channel_group", "String"),
      column("Is Paid", "is_paid", "Boolean"),
    ],
    "Last-touch acquisition and commerce channel taxonomy.",
  ),
  postgresTable(
    "Product",
    "dim_product",
    [
      column("Product Key", "product_key", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("SKU", "sku", "String"),
      column("Product Name", "product_name", "String"),
      column("Category", "category", "String"),
      column("Subcategory", "subcategory", "String"),
      column("Brand", "brand", "String"),
      column("List Price EUR", "list_price_eur", "Double", { formatString: "€#,0.00", summarizeBy: "None" }),
      column("Standard Cost EUR", "standard_cost_eur", "Double", { formatString: "€#,0.00", summarizeBy: "None" }),
      column("Base Return Probability", "base_return_probability", "Double", { formatString: "0.0%", summarizeBy: "None" }),
      column("Supplier Lead Time Days", "supplier_lead_time_days", "Int64", { summarizeBy: "None" }),
    ],
    "Product master with category hierarchy, reference price, cost, and supply attributes.",
  ),
  postgresTable(
    "Customer",
    "dim_customer",
    [
      column("Customer Key", "customer_key", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Customer ID", "customer_id", "String"),
      column("Acquisition Date", "acquisition_date", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Home Market Key", "home_market_key", "Int64", { summarizeBy: "None" }),
      column("Acquisition Channel Key", "acquisition_channel_key", "Int64", { summarizeBy: "None" }),
      column("Customer Segment", "customer_segment", "String"),
      column("Loyalty Tier", "loyalty_tier", "String"),
      column("Marketing Consent", "marketing_consent", "Boolean"),
    ],
    "Pseudonymous generated customer dimension for retention and segment analysis.",
  ),
  postgresTable(
    "Order Profitability",
    "fct_order_item_profitability",
    [
      column("Order Item ID", "order_item_id", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Order ID", "order_id", "Int64", { summarizeBy: "None" }),
      column("Customer Key", "customer_key", "Int64", { summarizeBy: "None" }),
      column("Product Key", "product_key", "Int64", { summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("Channel Key", "channel_key", "Int64", { summarizeBy: "None" }),
      column("Order Date", "order_date", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Quantity", "quantity", "Int64"),
      column("Units Returned", "units_returned", "Int64"),
      column("Gross Revenue EUR", "gross_revenue_eur", "Double", { formatString: "€#,0.00" }),
      column("Discount EUR", "discount_eur", "Double", { formatString: "€#,0.00" }),
      column("Refund EUR", "refund_eur", "Double", { formatString: "€#,0.00" }),
      column("Net Revenue EUR", "net_revenue_eur", "Double", { formatString: "€#,0.00" }),
      column("COGS EUR", "cogs_eur", "Double", { formatString: "€#,0.00" }),
      column("Recovered COGS EUR", "recovered_cogs_eur", "Double", { formatString: "€#,0.00" }),
      column("Return Handling Cost EUR", "handling_cost_eur", "Double", { formatString: "€#,0.00" }),
      column("Fulfillment Cost EUR", "allocated_shipping_cost_eur", "Double", { formatString: "€#,0.00" }),
      column("Marketing Spend EUR", "allocated_marketing_eur", "Double", { formatString: "€#,0.00" }),
      column("Contribution Margin EUR", "contribution_margin_eur", "Double", { formatString: "€#,0.00" }),
    ],
    "Atomic order-item finance fact. All profitability measures reconcile at this grain.",
  ),
  postgresTable(
    "Sessions",
    "fct_sessions",
    [
      column("Session ID", "session_id", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Session Timestamp", "session_ts", "DateTime", { formatString: "yyyy-mm-dd hh:mm", summarizeBy: "None" }),
      column("Date Key", "date_key", "Int64", { summarizeBy: "None" }),
      column("Customer Key", "customer_key", "Int64", { summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("Channel Key", "channel_key", "Int64", { summarizeBy: "None" }),
      column("Device Type", "device_type", "String"),
      column("Page Load MS", "page_load_ms", "Int64"),
      column("Product Views", "product_views", "Int64"),
      column("Added To Cart", "added_to_cart", "Boolean"),
      column("Checkout Started", "checkout_started", "Boolean"),
      column("Converted Order ID", "converted_order_id", "Int64", { summarizeBy: "None" }),
      column("Converted Session", "converted_session", "Int64"),
    ],
    "One row per digital session, including funnel steps, device, performance, and conversion outcome.",
  ),
  postgresTable(
    "Monthly Executive",
    "mart_monthly_executive",
    [
      column("Month Start", "month_start", "DateTime", { isKey: true, isUnique: true, formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Orders", "orders", "Int64"),
      column("Purchasing Customers", "purchasing_customers", "Int64"),
      column("Units Sold", "units_sold", "Int64"),
      column("Units Returned", "units_returned", "Int64"),
      column("Net Revenue EUR", "net_revenue_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin EUR", "contribution_margin_eur", "Double", { formatString: "€#,0" }),
      column("Marketing Spend EUR", "marketing_spend_eur", "Double", { formatString: "€#,0" }),
      column("Sessions", "sessions", "Int64"),
      column("Converted Sessions", "converted_sessions", "Int64"),
      column("Average Page Load MS", "average_page_load_ms", "Double", { formatString: "#,0" }),
      column("Fulfilled Orders", "fulfilled_orders", "Int64"),
      column("On Time Orders", "on_time_orders", "Int64"),
      column("Inventory Snapshots", "inventory_snapshots", "Int64"),
      column("Stockout Snapshots", "stockout_snapshots", "Int64"),
      column("Estimated Lost Units", "estimated_lost_units", "Int64"),
      column("Net Revenue Target EUR", "net_revenue_target_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin Target EUR", "contribution_margin_target_eur", "Double", { formatString: "€#,0" }),
      column("Orders Target", "orders_target", "Int64"),
    ],
    "Monthly governed scorecard used for trends and management target tracking.",
  ),
  postgresTable(
    "Target Variance",
    "mart_target_variance",
    [
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("Channel Key", "channel_key", "Int64", { summarizeBy: "None" }),
      column("Actual Orders", "actual_orders", "Int64"),
      column("Orders Target", "orders_target", "Int64"),
      column("Actual Net Revenue EUR", "actual_net_revenue_eur", "Double", { formatString: "€#,0" }),
      column("Net Revenue Target EUR", "net_revenue_target_eur", "Double", { formatString: "€#,0" }),
      column("Net Revenue Variance EUR", "net_revenue_variance_eur", "Double", { formatString: "€#,0" }),
      column("Actual Contribution Margin EUR", "actual_contribution_margin_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin Target EUR", "contribution_margin_target_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin Variance EUR", "contribution_margin_variance_eur", "Double", { formatString: "€#,0" }),
    ],
    "Monthly market-channel actual-versus-plan fact.",
  ),
  postgresTable(
    "Channel Profitability",
    "mart_channel_profitability",
    [
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("Channel Key", "channel_key", "Int64", { summarizeBy: "None" }),
      column("Orders", "orders", "Int64"),
      column("Purchasing Customers", "purchasing_customers", "Int64"),
      column("Net Revenue EUR", "net_revenue_eur", "Double", { formatString: "€#,0" }),
      column("Marketing Spend EUR", "marketing_spend_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin EUR", "contribution_margin_eur", "Double", { formatString: "€#,0" }),
    ],
    "Monthly market-channel revenue, media, and contribution fact.",
  ),
  postgresTable(
    "Customer Cohorts",
    "mart_customer_cohorts",
    [
      column("Cohort Month", "cohort_month", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Month Index", "month_index", "Int64", { summarizeBy: "None" }),
      column("Active Customers", "active_customers", "Int64"),
      column("Cohort Size", "cohort_size", "Int64"),
      column("Retention Rate", "retention_rate", "Double", { formatString: "0.0%", summarizeBy: "None" }),
    ],
    "First-purchase cohort retention through month twelve.",
  ),
  postgresTable(
    "Funnel",
    "mart_funnel",
    [
      column("Stage Order", "stage_order", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Stage", "stage", "String"),
      column("Sessions", "sessions", "Int64"),
    ],
    "Ordered commerce funnel stages and unique session counts.",
  ),
  postgresTable(
    "Inventory",
    "fct_inventory",
    [
      column("Inventory Snapshot ID", "inventory_snapshot_id", "Int64", { isKey: true, isUnique: true, summarizeBy: "None" }),
      column("Snapshot Date", "snapshot_date", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Product Key", "product_key", "Int64", { summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("On Hand Units", "on_hand_units", "Int64"),
      column("Reorder Point Units", "reorder_point_units", "Int64"),
      column("Inbound Units", "inbound_units", "Int64"),
      column("Stockout Flag", "stockout_flag", "Boolean"),
      column("Estimated Lost Units", "estimated_lost_units", "Int64"),
      column("Estimated Lost Revenue EUR", "estimated_lost_revenue_eur", "Double", { formatString: "€#,0" }),
    ],
    "Product-market-month inventory state and estimated stockout opportunity.",
  ),
  postgresTable(
    "Operations",
    "mart_operations",
    [
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Market Key", "market_key", "Int64", { summarizeBy: "None" }),
      column("Fulfillment Hub", "fulfillment_hub", "String"),
      column("Carrier", "carrier", "String"),
      column("Fulfilled Orders", "fulfilled_orders", "Int64"),
      column("On Time Orders", "on_time_orders", "Int64"),
      column("Average Transit Days", "average_transit_days", "Double", { formatString: "0.0", summarizeBy: "None" }),
      column("Shipping Cost EUR", "shipping_cost_eur", "Double", { formatString: "€#,0" }),
    ],
    "Monthly market-hub-carrier service and shipping economics.",
  ),
  postgresTable(
    "Product Returns",
    "mart_product_returns",
    [
      column("Month Start", "month_start", "DateTime", { formatString: "yyyy-mm-dd", summarizeBy: "None" }),
      column("Market Code", "market_code", "String"),
      column("Category", "category", "String"),
      column("Subcategory", "subcategory", "String"),
      column("Units Sold", "units_sold", "Int64"),
      column("Units Returned", "units_returned", "Int64"),
      column("Refunds EUR", "refunds_eur", "Double", { formatString: "€#,0" }),
      column("Handling Cost EUR", "handling_cost_eur", "Double", { formatString: "€#,0" }),
      column("Recovered COGS EUR", "recovered_cogs_eur", "Double", { formatString: "€#,0" }),
      column("Contribution Margin EUR", "contribution_margin_eur", "Double", { formatString: "€#,0" }),
    ],
    "Monthly return economics by market and product hierarchy.",
  ),
  {
    name: "KPI Measures",
    description: "Central governed DAX measure table.",
    daxExpression: 'DATATABLE("Metric Key", INTEGER, {{1}})',
  },
];

const relationships = [
  ["Order Profitability", "Order Date", "Date", "Date"],
  ["Order Profitability", "Market Key", "Market", "Market Key"],
  ["Order Profitability", "Channel Key", "Channel", "Channel Key"],
  ["Order Profitability", "Product Key", "Product", "Product Key"],
  ["Order Profitability", "Customer Key", "Customer", "Customer Key"],
  ["Sessions", "Date Key", "Date", "Date Key"],
  ["Sessions", "Market Key", "Market", "Market Key"],
  ["Sessions", "Channel Key", "Channel", "Channel Key"],
  ["Sessions", "Customer Key", "Customer", "Customer Key"],
  ["Monthly Executive", "Month Start", "Date", "Date"],
  ["Target Variance", "Month Start", "Date", "Date"],
  ["Target Variance", "Market Key", "Market", "Market Key"],
  ["Target Variance", "Channel Key", "Channel", "Channel Key"],
  ["Channel Profitability", "Month Start", "Date", "Date"],
  ["Channel Profitability", "Market Key", "Market", "Market Key"],
  ["Channel Profitability", "Channel Key", "Channel", "Channel Key"],
  ["Customer Cohorts", "Cohort Month", "Date", "Date"],
  ["Inventory", "Snapshot Date", "Date", "Date"],
  ["Inventory", "Market Key", "Market", "Market Key"],
  ["Inventory", "Product Key", "Product", "Product Key"],
  ["Operations", "Month Start", "Date", "Date"],
  ["Operations", "Market Key", "Market", "Market Key"],
  ["Product Returns", "Month Start", "Date", "Date"],
].map(([fromTable, fromColumn, toTable, toColumn], index) => ({
  name: `Relationship ${String(index + 1).padStart(2, "0")}`,
  fromTable,
  fromColumn,
  fromCardinality: "Many",
  toTable,
  toColumn,
  toCardinality: "One",
  crossFilteringBehavior: "OneDirection",
  isActive: true,
}));

const measures = [
  ["Gross Revenue", "SUM('Order Profitability'[Gross Revenue EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Discounts", "SUM('Order Profitability'[Discount EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Refunds", "SUM('Order Profitability'[Refund EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Net Revenue", "SUM('Order Profitability'[Net Revenue EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["COGS", "SUM('Order Profitability'[COGS EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Marketing Spend", "SUM('Order Profitability'[Marketing Spend EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Fulfillment Cost", "SUM('Order Profitability'[Fulfillment Cost EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Return Handling Cost", "SUM('Order Profitability'[Return Handling Cost EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Recovered COGS", "SUM('Order Profitability'[Recovered COGS EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Contribution Margin", "SUM('Order Profitability'[Contribution Margin EUR])", "€#,0;[Red]-€#,0", "Finance"],
  ["Contribution Margin Rate", "DIVIDE([Contribution Margin], [Net Revenue])", "0.0%;[Red]-0.0%", "Finance"],
  ["Orders", "DISTINCTCOUNT('Order Profitability'[Order ID])", "#,0", "Commerce"],
  ["Purchasing Customers", "DISTINCTCOUNT('Order Profitability'[Customer Key])", "#,0", "Commerce"],
  ["Units Sold", "SUM('Order Profitability'[Quantity])", "#,0", "Commerce"],
  ["Units Returned", "SUM('Order Profitability'[Units Returned])", "#,0", "Commerce"],
  ["Return Rate", "DIVIDE([Units Returned], [Units Sold])", "0.0%", "Commerce"],
  ["Average Order Value", "DIVIDE([Net Revenue], [Orders])", "€#,0.00", "Commerce"],
  ["Attributed ROAS", "DIVIDE([Net Revenue], [Marketing Spend])", "0.00x", "Commerce"],
  ["Sessions", "DISTINCTCOUNT('Sessions'[Session ID])", "#,0", "Funnel"],
  ["Converted Sessions", "SUM('Sessions'[Converted Session])", "#,0", "Funnel"],
  ["Conversion Rate", "DIVIDE([Converted Sessions], [Sessions])", "0.0%", "Funnel"],
  ["Added To Cart Sessions", "CALCULATE([Sessions], 'Sessions'[Added To Cart] = TRUE())", "#,0", "Funnel"],
  ["Checkout Sessions", "CALCULATE([Sessions], 'Sessions'[Checkout Started] = TRUE())", "#,0", "Funnel"],
  ["Add To Cart Rate", "DIVIDE([Added To Cart Sessions], [Sessions])", "0.0%", "Funnel"],
  ["Checkout Completion Rate", "DIVIDE([Converted Sessions], [Checkout Sessions])", "0.0%", "Funnel"],
  ["Average Page Load MS", "AVERAGE('Sessions'[Page Load MS])", "#,0", "Product"],
  ["Fulfilled Orders", "SUM('Operations'[Fulfilled Orders])", "#,0", "Operations"],
  ["On Time Orders", "SUM('Operations'[On Time Orders])", "#,0", "Operations"],
  ["On Time Delivery Rate", "DIVIDE([On Time Orders], [Fulfilled Orders])", "0.0%", "Operations"],
  ["Shipping Cost", "SUM('Operations'[Shipping Cost EUR])", "€#,0", "Operations"],
  ["Shipping Cost Per Order", "DIVIDE([Shipping Cost], [Fulfilled Orders])", "€#,0.00", "Operations"],
  ["Inventory Snapshots", "COUNTROWS('Inventory')", "#,0", "Inventory"],
  ["Stockout Snapshots", "CALCULATE(COUNTROWS('Inventory'), 'Inventory'[Stockout Flag] = TRUE())", "#,0", "Inventory"],
  ["Stockout Rate", "DIVIDE([Stockout Snapshots], [Inventory Snapshots])", "0.0%", "Inventory"],
  ["Estimated Lost Units", "SUM('Inventory'[Estimated Lost Units])", "#,0", "Inventory"],
  ["Estimated Lost Revenue", "SUM('Inventory'[Estimated Lost Revenue EUR])", "€#,0", "Inventory"],
  ["Net Revenue Target", "SUM('Target Variance'[Net Revenue Target EUR])", "€#,0", "Targets"],
  ["Net Revenue Variance", "SUM('Target Variance'[Net Revenue Variance EUR])", "€#,0;[Red]-€#,0", "Targets"],
  ["Revenue Target Attainment", "DIVIDE(SUM('Target Variance'[Actual Net Revenue EUR]), [Net Revenue Target])", "0.0%", "Targets"],
  ["Contribution Margin Target", "SUM('Target Variance'[Contribution Margin Target EUR])", "€#,0", "Targets"],
  ["Contribution Margin Variance", "SUM('Target Variance'[Contribution Margin Variance EUR])", "€#,0;[Red]-€#,0", "Targets"],
  ["Prior Quarter Net Revenue", "CALCULATE([Net Revenue], DATEADD('Date'[Date], -1, QUARTER))", "€#,0", "Time Intelligence"],
  ["Net Revenue QoQ", "DIVIDE([Net Revenue] - [Prior Quarter Net Revenue], [Prior Quarter Net Revenue])", "0.0%;[Red]-0.0%", "Time Intelligence"],
  ["Prior Quarter Contribution Margin", "CALCULATE([Contribution Margin], DATEADD('Date'[Date], -1, QUARTER))", "€#,0", "Time Intelligence"],
  ["Contribution Margin QoQ Delta", "[Contribution Margin] - [Prior Quarter Contribution Margin]", "€#,0;[Red]-€#,0", "Time Intelligence"],
  ["Prior Quarter Margin Rate", "CALCULATE([Contribution Margin Rate], DATEADD('Date'[Date], -1, QUARTER))", "0.0%", "Time Intelligence"],
  ["Margin Rate QoQ Delta PP", "100 * ([Contribution Margin Rate] - [Prior Quarter Margin Rate])", "0.0 pp;[Red]-0.0 pp", "Time Intelligence"],
  ["Cohort Active Customers", "SUM('Customer Cohorts'[Active Customers])", "#,0", "Retention"],
  ["Cohort Size", "SUM('Customer Cohorts'[Cohort Size])", "#,0", "Retention"],
  ["Cohort Retention Rate", "DIVIDE([Cohort Active Customers], [Cohort Size])", "0.0%", "Retention"],
  ["Repeat Purchase Rate", "VAR CustomerOrders = SUMMARIZE('Order Profitability', 'Order Profitability'[Customer Key], \"Order Count\", DISTINCTCOUNT('Order Profitability'[Order ID])) RETURN DIVIDE(COUNTROWS(FILTER(CustomerOrders, [Order Count] >= 2)), COUNTROWS(CustomerOrders))", "0.0%", "Retention"],
  ["Funnel Sessions", "SUM('Funnel'[Sessions])", "#,0", "Funnel"],
].map(([name, expression, formatString, displayFolder]) => ({
  tableName: "KPI Measures",
  name,
  expression,
  formatString,
  displayFolder,
  description: `Governed ${name.toLowerCase()} measure; use this measure instead of implicit aggregation.`,
}));

await fs.mkdir(modelRoot, { recursive: true });
await fs.rm(definitionRoot, { recursive: true, force: true });
await client.connect(transport);
try {
  const database = await call(
    "database_operations",
    {
      operation: "Create",
      connectionName: "CommercePulseOffline",
      createDefinition: {
        name: "CommercePulse Europe",
        modelName: "CommercePulse Europe",
        isOffline: true,
        compatibilityLevel: 1702,
        description: "Governed semantic model for synthetic European omnichannel commerce analytics.",
      },
    },
    "create offline semantic model",
  );
  const connectionName = database.connectionName ?? "CommercePulseOffline";
  await call(
    "named_expression_operations",
    {
      operation: "CreateParameter",
      connectionName,
      definitions: [
        { name: "Server", expression: "localhost", kind: "M", description: "PostgreSQL server parameter." },
        { name: "Database", expression: "commercepulse", kind: "M", description: "PostgreSQL database parameter." },
      ],
      options: { continueOnError: false, useTransaction: true },
    },
    "create Power Query parameters",
  );
  await call(
    "table_operations",
    {
      operation: "Create",
      connectionName,
      definitions: tables,
      options: { continueOnError: false, useTransaction: true },
    },
    `create ${tables.length} semantic tables`,
  );
  await call(
    "table_operations",
    {
      operation: "MarkAsDateTable",
      connectionName,
      markAsDateTableDefinitions: [{ tableName: "Date", dateColumnName: "Date" }],
    },
    "mark conformed Date table",
  );
  await call(
    "relationship_operations",
    {
      operation: "Create",
      connectionName,
      definitions: relationships,
      options: { continueOnError: false, useTransaction: true },
    },
    `create ${relationships.length} relationships`,
  );
  await call(
    "measure_operations",
    {
      operation: "Create",
      connectionName,
      definitions: measures,
      options: { continueOnError: false, useTransaction: true },
    },
    `create ${measures.length} DAX measures`,
  );
  await call(
    "model_operations",
    {
      operation: "Update",
      connectionName,
      definition: {
        discourageImplicitMeasures: true,
        defaultPowerBIDataSourceVersion: "powerBI_V3",
        sourceQueryCulture: "en-US",
      },
    },
    "apply model governance settings",
  );
  await call(
    "database_operations",
    {
      operation: "ExportToTmdlFolder",
      connectionName,
      tmdlFolderPath: definitionRoot,
    },
    "export validated TMDL",
  );
} finally {
  await client.close();
}

const pbism = {
  $schema:
    "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  version: "4.2",
  settings: { qnaEnabled: true },
};
await fs.writeFile(path.join(modelRoot, "definition.pbism"), `${JSON.stringify(pbism, null, 2)}\n`);
process.stdout.write(`${definitionRoot}\n`);
