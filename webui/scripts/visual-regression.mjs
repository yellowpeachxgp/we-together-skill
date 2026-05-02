import { access, mkdir, mkdtemp, writeFile, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const port = Number(process.env.WEBUI_VISUAL_PORT || 5174);
const baseUrl = process.env.WEBUI_VISUAL_URL || `http://127.0.0.1:${port}/`;
const bridgePort = Number(process.env.WEBUI_LOCAL_BRIDGE_PORT || 7782);
const bridgeUrl = process.env.WEBUI_LOCAL_BRIDGE_URL || `http://127.0.0.1:${bridgePort}`;
const bridgeStatusUrl = new URL("/api/runtime/status", bridgeUrl).toString();
const outputDir = resolve(repoRoot, "output/playwright");
const specPath = resolve(root, "scripts/.visual-regression.spec.mjs");
let visualRoot = process.env.WEBUI_VISUAL_ROOT || "";

async function isReachable(url) {
  try {
    const response = await fetch(url, { method: "HEAD" });
    return response.ok;
  } catch {
    return false;
  }
}

function run(command, args, options = {}) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(command, args, {
      cwd: options.cwd || root,
      env: { ...process.env, ...(options.env || {}) },
      stdio: options.stdio || "inherit"
    });
    child.on("error", rejectRun);
    child.on("exit", (code) => {
      if (code === 0) resolveRun();
      else rejectRun(new Error(`${command} ${args.join(" ")} exited with ${code}`));
    });
  });
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function pythonExecutable() {
  if (process.env.WEBUI_PYTHON) return process.env.WEBUI_PYTHON;
  const venvPython = resolve(repoRoot, ".venv/bin/python");
  return (await pathExists(venvPython)) ? venvPython : "python3";
}

async function waitForServer(url) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 15000) {
    if (await isReachable(url)) return;
    await new Promise((resolveWait) => setTimeout(resolveWait, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function prepareVisualRoot() {
  if (!visualRoot) {
    visualRoot = await mkdtemp(resolve(tmpdir(), "we-together-webui-visual-"));
  }
  const python = await pythonExecutable();
  await run(python, ["scripts/seed_demo.py", "--root", visualRoot], { cwd: repoRoot });
  const branchSeed = `
import sqlite3
import sys
from pathlib import Path

from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch

root = Path(sys.argv[1])
db_path = root / "db" / "main.sqlite3"
conn = sqlite3.connect(db_path)
row = conn.execute("SELECT person_id FROM persons WHERE primary_name='Alice' LIMIT 1").fetchone()
conn.close()
person_id = row[0] if row else "person_visual_alice"
patch = build_patch(
    source_event_id="visual_branch_seed",
    target_type="local_branch",
    target_id="branch_visual_unmerge",
    operation="create_local_branch",
    payload={
        "branch_id": "branch_visual_unmerge",
        "scope_type": "person",
        "scope_id": person_id,
        "status": "open",
        "reason": "visual operator gate",
        "created_from_event_id": "visual_branch_seed",
        "branch_candidates": [
            {
                "candidate_id": "cand_keep_visual",
                "label": "保留 merged 状态",
                "payload_json": {"effect_patches": []},
                "confidence": 0.34,
                "status": "open",
            },
            {
                "candidate_id": "cand_unmerge_visual",
                "label": "执行 unmerge",
                "payload_json": {
                    "effect_patches": [
                        {
                            "operation": "unmerge_person",
                            "target_type": "person",
                            "target_id": person_id,
                            "payload": {"source_person_id": person_id, "reviewer": "visual_check"},
                        }
                    ]
                },
                "confidence": 0.66,
                "status": "open",
            },
        ],
    },
    confidence=0.8,
    reason="visual seeded operator branch",
)
apply_patch_record(db_path=db_path, patch=patch)
`;
  await run(python, ["-c", branchSeed, visualRoot], { cwd: repoRoot });
}

function bridgeListenParts() {
  const parsed = new URL(bridgeUrl);
  return {
    host: parsed.hostname || "127.0.0.1",
    port: parsed.port || String(bridgePort)
  };
}

const spec = `
import { test, expect } from "@playwright/test";

const baseUrl = process.env.WEBUI_VISUAL_URL;
const outputDir = process.env.WEBUI_VISUAL_OUTPUT;

const cases = [
  { name: "desktop", width: 1440, height: 950 },
  { name: "mobile", width: 390, height: 844 }
];

for (const item of cases) {
  test(\`operator cockpit \${item.name}\`, async ({ page }) => {
    const consoleErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });

    await page.setViewportSize({ width: item.width, height: item.height });
    await page.goto(baseUrl);
    await page.waitForSelector(".graph-canvas");
    await expect(page.getByText(/连接 WebUI token 后会调用真实/)).toHaveCount(0);

    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      hasGraph: Boolean(document.querySelector(".graph-canvas")),
      hasInspector: Boolean(document.querySelector(".inspector"))
    }));

    expect(metrics.hasGraph).toBe(true);
    expect(metrics.hasInspector).toBe(true);
    expect(metrics.scrollWidth).toBe(metrics.innerWidth);
    expect(consoleErrors).toEqual([]);

    await page.screenshot({
      path: \`\${outputDir}/webui-operator-cockpit-\${item.name}-visual-check.png\`,
      fullPage: false
    });

    if (item.name === "desktop") {
      const canvas = page.getByRole("region", { name: /图谱画布/ });
      await canvas.getByRole("button", { name: /^Alice$/ }).click();
      const inspector = page.getByRole("complementary", { name: /详情检查器/ });
      await inspector.getByRole("button", { name: /聚焦当前/ }).click();
      await expect(page.getByText(/Focus Alice/)).toBeVisible();
      await expect(page.getByText(/Filtered scope/)).toBeVisible();
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-focus-lens.png\`,
        fullPage: false
      });
      await page.getByRole("button", { name: /清除过滤/ }).click();
      await expect(page.getByText(/Full scope/)).toBeVisible();

      await page.getByLabel(/搜索/).fill("memory");
      await expect(page.getByText(/Query memory/)).toBeVisible();
      await page.keyboard.press("Control+K");
      await page.getByLabel(/命令搜索/).fill("Clear filters");
      await expect(page.getByRole("button", { name: /Clear filters scope/ })).toBeVisible();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("dialog", { name: /命令面板/ })).toBeHidden();
      await expect(page.getByText(/Full scope/)).toBeVisible();

      await page.keyboard.press("Control+K");
      await expect(page.getByRole("dialog", { name: /命令面板/ })).toBeVisible();
      await page.mouse.move(12, 12);
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("ArrowDown");
      await expect(page.getByRole("button", { name: /Scene 对话 view/ })).toHaveAttribute("aria-selected", "true");
      await page.getByLabel(/命令搜索/).fill("Scene");
      await expect(page.getByRole("button", { name: /Scene 对话 view/ })).toHaveAttribute("aria-selected", "true");
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-command-palette-active.png\`,
        fullPage: false
      });
      await page.getByLabel(/命令搜索/).fill("Carol");
      await expect(page.getByRole("button", { name: /Carol person/ })).toBeVisible();
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-command-palette.png\`,
        fullPage: false
      });
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog", { name: /命令面板/ })).toBeHidden();

      await page.getByRole("button", { name: /持续指导 Carol 的职业路径/ }).click();
      await expect(page.getByText(/Activity Events/)).toBeVisible();
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-activity-detail.png\`,
        fullPage: false
      });

      await page.getByRole("button", { name: /^复核$/ }).click();
      await expect(page.getByRole("region", { name: /复核队列/ })).toBeVisible();
      await expect(page.locator("[aria-label='2 candidates']")).toBeVisible();
      await expect(page.getByRole("region", { name: /复核风险/ })).toBeVisible();
      await expect(page.getByText(/High risk/)).toBeVisible();
      await expect(page.getByRole("region", { name: /候选影响/ })).toBeVisible();
      await expect(page.getByText(/unmerge_person/)).toBeVisible();
      await page.getByRole("button", { name: /^应用候选$/ }).click();
      await expect(page.getByRole("button", { name: /^确认应用$/ })).toBeVisible();
      await expect.poll(async () => page.evaluate(() => window.scrollY)).toBe(0);
      await page.waitForTimeout(220);
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-review-queue.png\`,
        fullPage: false
      });

      const reviewMetrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth
      }));
      expect(reviewMetrics.scrollWidth).toBe(reviewMetrics.innerWidth);

      await page.getByRole("button", { name: /^指标$/ }).click();
      await expect(page.getByRole("region", { name: /运行遥测/ })).toBeVisible();
      await expect(page.getByText(/Graph load/)).toBeVisible();
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-desktop-telemetry.png\`,
        fullPage: false
      });

      const telemetryMetrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth
      }));
      expect(telemetryMetrics.scrollWidth).toBe(telemetryMetrics.innerWidth);

      await page.getByRole("button", { name: /^对话$/ }).click();
      await expect(page.getByRole("heading", { name: /Scene 对话/ })).toBeVisible();
      await expect(page.getByText(/Local skill bridge 默认通道/)).toBeVisible();
      await expect(page.getByText(/连接 WebUI token 后会调用真实/)).toHaveCount(0);
    }

    if (item.name === "mobile") {
      const navMetrics = await page.evaluate(() => Array.from(document.querySelectorAll(".nav-button span")).map((node) => {
        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle(node);
        return {
          text: node.textContent || "",
          height: rect.height,
          whiteSpace: style.whiteSpace
        };
      }));
      expect(navMetrics.every((entry) => entry.height <= 22 && entry.whiteSpace === "nowrap")).toBe(true);

      await page.getByRole("button", { name: /打开检查器/ }).click();
      await expect(page.locator(".inspector")).toHaveAttribute("data-open", "true");
      const inspectorContext = page.getByRole("region", { name: /检查器上下文/ });
      await expect(inspectorContext).toBeVisible();
      await expect(inspectorContext.getByText(/\\d+ links/)).toBeVisible();
      await page.waitForTimeout(240);
      await page.screenshot({
        path: \`\${outputDir}/webui-operator-cockpit-mobile-drawer-open.png\`,
        fullPage: false
      });
    }
  });
}
`;

await mkdir(outputDir, { recursive: true });
await writeFile(specPath, spec);

let bridgeServer = null;
let server = null;
try {
  await prepareVisualRoot();
  if (!(await isReachable(bridgeStatusUrl))) {
    const bridge = bridgeListenParts();
    bridgeServer = spawn(
      await pythonExecutable(),
      [
        "scripts/webui_host.py",
        "--root",
        visualRoot,
        "--host",
        bridge.host,
        "--port",
        bridge.port
      ],
      {
        cwd: repoRoot,
        env: process.env,
        stdio: "inherit"
      }
    );
    await waitForServer(bridgeStatusUrl);
  }

  if (!(await isReachable(baseUrl))) {
    server = spawn("npm", ["run", "dev:vite", "--", "--host", "127.0.0.1", "--port", String(port)], {
      cwd: root,
      env: {
        ...process.env,
        WEBUI_LOCAL_BRIDGE_URL: bridgeUrl
      },
      stdio: "inherit"
    });
    await waitForServer(baseUrl);
  }

  await run("npx", ["playwright", "test", specPath, "--reporter=list"], {
    cwd: root,
    env: {
      WEBUI_VISUAL_URL: baseUrl,
      WEBUI_VISUAL_OUTPUT: outputDir
    }
  });
} finally {
  if (server) server.kill("SIGTERM");
  if (bridgeServer) bridgeServer.kill("SIGTERM");
  await rm(specPath, { force: true });
  if (!process.env.WEBUI_VISUAL_ROOT && visualRoot) {
    await rm(visualRoot, { recursive: true, force: true });
  }
}
