import { expect, test } from "@playwright/test";

test("creates an application through the local Web workspace", async ({
  page,
  request,
}) => {
  const health = await request.get("http://127.0.0.1:9998/api/v1/health");
  expect(await health.json()).toMatchObject({ status: "ok" });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /求职不是信息堆积/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "进入主工作台" }).click();
  await expect(page.getByRole("heading", { name: "申请总览" })).toBeVisible();
  await page.getByRole("link", { name: "申请追踪" }).click();

  const company = `E2E Company ${Date.now()}`;
  await page.getByLabel("公司").fill(company);
  await page.getByLabel("职位").fill("Release Engineer");
  await page.getByRole("button", { name: "新增" }).click();

  await expect(page.getByRole("heading", { name: company })).toBeVisible();
  await expect(page.getByText("Release Engineer", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "公开信息 Summary" }),
  ).toBeVisible();
});
