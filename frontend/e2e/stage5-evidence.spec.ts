import { expect, test } from "@playwright/test";

test("shows versioned Stage 5 evidence with an explicit model gate", async ({
  page,
  request,
}) => {
  const key = Date.now();
  const created = await request.post("http://127.0.0.1:9998/api/v1/applications", {
    data: {
      company: `Stage 5 E2E ${key}`,
      role: "Evidence Engineer",
      idempotency_key: `stage5-e2e-app-${key}`,
    },
  });
  expect(created.ok()).toBeTruthy();
  const application = await created.json();
  const jd = await request.post(
    `http://127.0.0.1:9998/api/v1/applications/${application.application_id}/jd-versions`,
    {
      data: {
        idempotency_key: `stage5-e2e-jd-${key}`,
        raw_text: "Build reliable Python APIs.\nUse evidence-based engineering.",
      },
    },
  );
  expect(jd.ok()).toBeTruthy();

  await page.goto(`/#/applications/${application.application_id}/evidence`);
  await expect(page.getByRole("heading", { name: "证据分析" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "JD v1" })).toBeVisible();
  await expect(page.getByText("这里只整理证据，不评分、不预测录用结果。", { exact: false })).toBeVisible();

  const structure = page.getByRole("button", { name: "结构化此版本" });
  const research = page.getByRole("button", { name: "生成公司研究" });
  await expect(structure).toBeDisabled();
  await expect(research).toBeDisabled();
  await page.getByLabel("我了解并确认本页的下一次模型调用").check();
  await expect(structure).toBeEnabled();
  await expect(research).toBeEnabled();
});
