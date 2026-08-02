import { expect, test } from "@playwright/test";

test("keeps an Agent write behind approval and restores it after reload", async ({
  page,
  request,
}) => {
  const key = Date.now();
  const created = await request.post("http://127.0.0.1:9998/api/v1/applications", {
    data: {
      company: `Stage 6 E2E ${key}`,
      role: "Controlled Agent Engineer",
      idempotency_key: `stage6-e2e-app-${key}`,
    },
  });
  expect(created.ok()).toBeTruthy();
  const application = await created.json();
  const runId = `10000000-0000-4000-8000-${String(key).slice(-12).padStart(12, "0")}`;
  const toolCallId = "20000000-0000-4000-8000-000000000001";
  const approvalId = "30000000-0000-4000-8000-000000000001";
  const createdAt = new Date().toISOString();
  let run: Record<string, unknown> | null = null;

  const waitingRun = () => ({
    run_id: runId,
    application_id: application.application_id,
    request_text: "把待核实问题追加到岗位备注",
    model_name: "e2e-model",
    status: "waiting_approval",
    current_step: "waiting_approval",
    limits: { max_steps: 8, max_model_calls: 6, max_tool_calls: 8, max_write_approvals: 2, max_elapsed_seconds: 180 },
    usage: { steps: 2, model_calls: 2, tool_calls: 2, write_approvals: 1, elapsed_ms: 40 },
    final_output: null,
    error_code: null,
    error_message_safe: null,
    tool_calls: [
      { tool_call_id: "20000000-0000-4000-8000-000000000000", sequence: 1, tool_name: "application.read", tool_version: "1.0", risk_level: "read", arguments: {}, status: "succeeded", reason: "读取当前岗位", result_refs: [`application:${application.application_id}:v1`], result_summary_safe: "读取岗位快照 v1。", error_code: null, created_at: createdAt, finished_at: createdAt },
      { tool_call_id: toolCallId, sequence: 2, tool_name: "application.append_note", tool_version: "1.0", risk_level: "write_approval", arguments: { text: "待核实：SQL 使用范围", expected_version: 1, source_ids: [`application:${application.application_id}:v1`] }, status: "waiting_approval", reason: "用户明确要求写入备注", result_refs: [], result_summary_safe: null, error_code: null, created_at: createdAt, finished_at: null },
    ],
    approvals: [{ approval_id: approvalId, tool_call_id: toolCallId, status: "pending", request_summary: `岗位：${application.company} / ${application.role}\n当前版本：1\n当前备注：（空）\n将追加：待核实：SQL 使用范围`, application_version: 1, decision_note: null, requested_at: createdAt, decided_at: null }],
    created_at: createdAt,
    finished_at: null,
  });

  await page.route(`**/api/v1/applications/${application.application_id}/agent-runs`, async (route) => {
    if (route.request().method() === "POST") run = waitingRun();
    await route.fulfill({ json: route.request().method() === "POST" ? run : (run ? [run] : []) });
  });
  await page.route(`**/api/v1/agent-runs/${runId}/approvals/${approvalId}`, async (route) => {
    const waiting = waitingRun();
    run = {
      ...waiting,
      status: "succeeded",
      current_step: "completed",
      usage: { ...waiting.usage, steps: 3, model_calls: 3, elapsed_ms: 60 },
      approvals: [{ ...waiting.approvals[0], status: "approved", decided_at: new Date().toISOString() }],
      tool_calls: waiting.tool_calls.map((item) => item.tool_call_id === toolCallId ? { ...item, status: "succeeded", result_refs: [`application:${application.application_id}:v2`], result_summary_safe: "已批准并追加岗位备注；岗位版本更新为 2。", finished_at: new Date().toISOString() } : item),
      final_output: { action: "final", summary: "待核实问题已在批准后写入。", facts: [{ statement: "岗位备注已更新", source_id: `application:${application.application_id}:v2`, locator: "Tracker snapshot v2" }], unknowns: [], next_questions: ["是否还要补充证据？"] },
      finished_at: new Date().toISOString(),
    };
    await route.fulfill({ json: run });
  });

  await page.goto(`/#/applications/${application.application_id}`);
  await page.getByRole("link", { name: "Agent 协助" }).click();
  await expect(page.getByRole("heading", { name: "Agent 协助" })).toBeVisible();
  const start = page.getByRole("button", { name: "启动 Agent" });
  await expect(start).toBeDisabled();
  await page.getByLabel("任务").fill("把待核实问题追加到岗位备注");
  await page.getByLabel("我了解并确认本次 Agent 模型调用").check();
  await start.click();
  await expect(page.getByRole("heading", { name: "等待人工审批" })).toBeVisible();
  await expect(page.getByText("批准前不会修改岗位数据", { exact: false })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "等待人工审批" })).toBeVisible();
  await page.getByRole("button", { name: "批准写入" }).click();
  await expect(page.getByRole("heading", { name: "最终结果" })).toBeVisible();
  await expect(page.getByText("待核实问题已在批准后写入。", { exact: true })).toBeVisible();
  await expect(page.getByText("岗位备注已更新", { exact: true })).toBeVisible();
});
