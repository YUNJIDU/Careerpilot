import { expect, test } from "@playwright/test";

test("creates a reminder and a guarded prefill session", async ({ page, request }) => {
  const created = await request.post("http://127.0.0.1:9998/api/v1/applications", {
    data: {
      company: `Stage 7 E2E ${Date.now()}`,
      role: "Integration Engineer",
      idempotency_key: crypto.randomUUID(),
    },
  });
  expect(created.ok()).toBeTruthy();
  const application = await created.json();

  await page.goto("/#/integrations");
  await expect(page.getByRole("heading", { name: "外部集成" })).toBeVisible();
  await page.getByLabel("岗位").first().selectOption(application.application_id);
  await page.getByLabel("提醒内容").fill("准备 Stage 7 验收");
  const due = new Date(Date.now() + 60 * 60 * 1000);
  const local = new Date(due.getTime() - due.getTimezoneOffset() * 60000)
    .toISOString().slice(0, 16);
  await page.getByLabel("时间").fill(local);
  await page.getByRole("button", { name: "添加提醒" }).click();
  await expect(
    page.locator(".reminder-list article")
      .filter({ hasText: application.company })
      .getByText("准备 Stage 7 验收", { exact: true }),
  ).toBeVisible();

  await page.getByLabel("岗位").nth(1).selectOption(application.application_id);
  await page.getByLabel("目标表单网址").fill("https://jobs.example.com/apply");
  await page.getByLabel("姓名").fill("Stage Seven User");
  await page.getByLabel("邮箱").last().fill("stage7@example.com");
  await page.getByRole("button", { name: "创建预填会话" }).click();
  await expect(page.getByText("会话 ID", { exact: true })).toBeVisible();
  await expect(page.getByText("https://jobs.example.com", { exact: true })).toBeVisible();
});
