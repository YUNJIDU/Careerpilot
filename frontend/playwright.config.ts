import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const python = existsSync("../.venv/Scripts/python.exe")
  ? '"../.venv/Scripts/python.exe"'
  : "python";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:9999",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        `${python} -m uvicorn careerpilot.api:create_app --factory --app-dir ../backend/src --host 127.0.0.1 --port 9998`,
      url: "http://127.0.0.1:9998/api/v1/health",
      reuseExistingServer: !process.env.CI,
      env: {
        CAREERPILOT_DATA_DIR: "../data/e2e",
        CAREERPILOT_FRONTEND_ORIGIN: "http://127.0.0.1:9999",
      },
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:9999",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
