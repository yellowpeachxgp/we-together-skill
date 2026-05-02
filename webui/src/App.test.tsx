import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

beforeEach(() => {
  localStorage.setItem("we_together_demo_mode", "1");
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("WeTogether WebUI", () => {
  it("renders the graph workspace shell with liquid glass navigation", () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: /本地图谱工作台/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^图谱$/i })).toHaveClass("is-active");
    expect(screen.getByText(/Liquid Glass/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/搜索/i)).toBeInTheDocument();
  });

  it("switches between flat and glass themes without hiding operational context", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^Flat$/i }));

    expect(document.documentElement).toHaveAttribute("data-theme", "flat");
    expect(screen.getByText(/Events/i)).toBeInTheDocument();
    expect(screen.getByText(/Patches/i)).toBeInTheDocument();
    expect(screen.getByText(/Snapshots/i)).toBeInTheDocument();
  });

  it("surfaces operator summary and the compact activity dock", () => {
    render(<App />);

    const summary = screen.getByRole("region", { name: /图谱摘要/i });
    const dock = screen.getByRole("region", { name: /运行记录/i });

    expect(within(summary).getByText("People")).toBeInTheDocument();
    expect(within(summary).getByText("8")).toBeInTheDocument();
    expect(within(dock).getByText(/Events/i)).toBeInTheDocument();
    expect(within(dock).getByText(/4 records/i)).toBeInTheDocument();
  });

  it("updates the inspector when a graph node is selected", async () => {
    render(<App />);

    const user = userEvent.setup();
    const canvas = screen.getByRole("region", { name: /图谱画布/i });
    await user.click(within(canvas).getByRole("button", { name: /^Bob$/i }));

    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    expect(within(inspector).getByRole("heading", { name: /详情检查器/i })).toBeInTheDocument();
    expect(within(inspector).getAllByText("person_bob").length).toBeGreaterThan(0);
    expect(within(inspector).getByRole("button", { name: /编辑/i })).toBeInTheDocument();
  });

  it("supports graph viewport controls and edge inspection", async () => {
    render(<App />);

    const user = userEvent.setup();
    const canvas = screen.getByRole("region", { name: /图谱画布/i });

    await user.click(within(canvas).getByRole("button", { name: /放大图谱/i }));
    expect(within(canvas).getByText("125%")).toBeInTheDocument();

    await user.hover(within(canvas).getByRole("button", { name: /^Alice$/i }));
    expect(within(canvas).getByRole("button", { name: /关系 edge_ab/i })).toHaveClass("is-highlighted");

    await user.click(within(canvas).getByRole("button", { name: /关系 edge_ab/i }));
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    expect(within(inspector).getAllByText(/edge_ab/i).length).toBeGreaterThan(0);

    await user.click(within(canvas).getByRole("button", { name: /适合视图/i }));
    expect(within(canvas).getByText("100%")).toBeInTheDocument();
  });

  it("links activity records to the inspector and related graph nodes", async () => {
    render(<App />);

    const user = userEvent.setup();
    const dock = screen.getByRole("region", { name: /运行记录/i });
    await user.click(within(dock).getByRole("button", { name: /持续指导 Carol 的职业路径/i }));

    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    expect(within(inspector).getAllByText(/Activity Events/i).length).toBeGreaterThan(0);
    expect(within(inspector).getAllByText(/evt_830f92e0de3a47/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Carol$/i })).toHaveClass("is-related");
  });

  it("pins, compares, and keeps recent inspector history", async () => {
    render(<App />);

    const user = userEvent.setup();
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });

    await user.click(within(inspector).getByRole("button", { name: /固定当前/i }));
    await user.click(screen.getByRole("button", { name: /^Bob$/i }));
    await user.click(within(inspector).getByRole("button", { name: /对比固定/i }));

    expect(within(inspector).getAllByText(/Compare/i).length).toBeGreaterThan(0);
    expect(within(inspector).getAllByText(/Alice/i).length).toBeGreaterThan(0);
    expect(within(inspector).getAllByText(/Bob/i).length).toBeGreaterThan(0);
    expect(within(inspector).getByRole("region", { name: /最近查看/i })).toBeInTheDocument();
  });

  it("shows operational empty states and mobile drawer controls", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/搜索/i), "no-matching-node");

    expect(screen.getByText(/没有匹配节点/i)).toBeInTheDocument();
    expect(screen.getByText(/Local skill bridge 默认通道/i)).toBeInTheDocument();

    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    await user.click(within(inspector).getByRole("button", { name: /收起检查器/i }));
    expect(inspector).toHaveAttribute("data-open", "false");
  });

  it("summarizes active filters and clears the graph scope", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/搜索/i), "memory");

    const status = screen.getByRole("region", { name: /过滤状态/i });
    expect(within(status).getByText(/2 \/ 8 nodes/i)).toBeInTheDocument();
    expect(within(status).getByText(/Query memory/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/^Type$/i), "person");
    expect(within(status).getByText(/Type person/i)).toBeInTheDocument();

    await user.click(within(status).getByRole("button", { name: /清除过滤/i }));
    expect(screen.getByLabelText(/搜索/i)).toHaveValue("");
    expect(screen.getByLabelText(/^Type$/i)).toHaveValue("all");
    expect(within(status).getByText(/8 \/ 8 nodes/i)).toBeInTheDocument();
  });

  it("focuses the graph to the selected node neighborhood and clears it", async () => {
    render(<App />);

    const user = userEvent.setup();
    const canvas = screen.getByRole("region", { name: /图谱画布/i });
    await user.click(within(canvas).getByRole("button", { name: /^Alice$/i }));
    await user.click(within(canvas).getByRole("button", { name: /聚焦邻域/i }));

    const status = screen.getByRole("region", { name: /过滤状态/i });
    expect(within(status).getByText(/Focus Alice/i)).toBeInTheDocument();
    expect(within(status).getByText(/5 \/ 8 nodes/i)).toBeInTheDocument();
    expect(within(canvas).getByRole("button", { name: /^Alice$/i })).toBeInTheDocument();
    expect(within(canvas).getByRole("button", { name: /^Bob$/i })).toBeInTheDocument();
    expect(within(canvas).queryByRole("button", { name: /^Dan$/i })).not.toBeInTheDocument();

    await user.click(within(status).getByRole("button", { name: /清除过滤/i }));
    expect(within(status).getByText(/8 \/ 8 nodes/i)).toBeInTheDocument();
  });

  it("focuses the current node directly from the inspector", async () => {
    render(<App />);

    const user = userEvent.setup();
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    await user.click(within(inspector).getByRole("button", { name: /聚焦当前/i }));

    const status = screen.getByRole("region", { name: /过滤状态/i });
    expect(within(status).getByText(/Focus Alice/i)).toBeInTheDocument();
    expect(within(status).getByText(/5 \/ 8 nodes/i)).toBeInTheDocument();
  });

  it("resets the viewport scroll when switching work surfaces", async () => {
    render(<App />);
    const scrollTo = vi.mocked(window.scrollTo);
    scrollTo.mockClear();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^复核$/i }));

    await waitFor(() => {
      expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0 });
    });
  });

  it("navigates direct graph neighbors from the inspector", async () => {
    render(<App />);

    const user = userEvent.setup();
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });

    const context = within(inspector).getByRole("region", { name: /检查器上下文/i });
    expect(within(context).getByText(/Node/i)).toBeInTheDocument();
    expect(within(context).getByText(/4 links/i)).toBeInTheDocument();
    expect(within(context).getByText(/1 recent/i)).toBeInTheDocument();

    const related = within(inspector).getByRole("region", { name: /关联节点/i });
    await user.click(within(related).getByRole("button", { name: /Bob relation/i }));

    expect(within(inspector).getAllByText(/person_bob/i).length).toBeGreaterThan(0);
  });

  it("focuses activity lanes without losing the dock", async () => {
    render(<App />);

    const user = userEvent.setup();
    const dock = screen.getByRole("region", { name: /运行记录/i });

    await user.click(within(dock).getByRole("button", { name: /^Patches$/i }));
    expect(within(dock).getByText(/patch_0727/i)).toBeInTheDocument();
    expect(within(dock).queryByText(/持续指导 Carol 的职业路径/i)).not.toBeInTheDocument();

    await user.click(within(dock).getByRole("button", { name: /^All$/i }));
    expect(within(dock).getByText(/持续指导 Carol 的职业路径/i)).toBeInTheDocument();
  });

  it("supports keyboard shortcuts for search, escape, and fit view", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("/");
    const search = screen.getByLabelText(/搜索/i);
    expect(search).toHaveFocus();

    await user.keyboard("Bob");
    expect(search).toHaveValue("Bob");

    await user.keyboard("{Escape}");
    expect(search).toHaveValue("");

    const canvas = screen.getByRole("region", { name: /图谱画布/i });
    await user.click(within(canvas).getByRole("button", { name: /放大图谱/i }));
    expect(within(canvas).getByText("125%")).toBeInTheDocument();

    await user.keyboard("f");
    expect(within(canvas).getByText("100%")).toBeInTheDocument();
  });

  it("copies the current inspector payload as JSON", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: { writeText }
    });
    expect(window.navigator.clipboard.writeText).toBe(writeText);
    render(<App />);

    const dock = screen.getByRole("region", { name: /运行记录/i });
    await user.click(within(dock).getByRole("button", { name: /持续指导 Carol 的职业路径/i }));

    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    await user.click(within(inspector).getByRole("button", { name: /复制 JSON/i }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(String(writeText.mock.calls[0][0])).toContain("evt_830f92e0de3a47");
    expect(within(inspector).getByText(/已复制/i)).toBeInTheDocument();
  });

  it("opens a command palette and selects graph nodes from it", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");

    const palette = screen.getByRole("dialog", { name: /命令面板/i });
    expect(within(palette).getByLabelText(/命令搜索/i)).toHaveFocus();

    await user.type(within(palette).getByLabelText(/命令搜索/i), "Carol");
    await user.click(within(palette).getByRole("button", { name: /Carol person/i }));

    expect(screen.queryByRole("dialog", { name: /命令面板/i })).not.toBeInTheDocument();
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    expect(within(inspector).getAllByText(/person_carol/i).length).toBeGreaterThan(0);
  });

  it("uses the command palette to jump to review", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");
    const palette = screen.getByRole("dialog", { name: /命令面板/i });

    await user.click(within(palette).getByRole("button", { name: /Operator Review view/i }));
    expect(screen.getByRole("heading", { name: /Operator Review/i })).toBeInTheDocument();
  });

  it("runs the first command palette result with enter", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");
    const palette = screen.getByRole("dialog", { name: /命令面板/i });

    await user.type(within(palette).getByLabelText(/命令搜索/i), "Bob");
    await user.keyboard("{Enter}");

    expect(screen.queryByRole("dialog", { name: /命令面板/i })).not.toBeInTheDocument();
    const inspector = screen.getByRole("complementary", { name: /详情检查器/i });
    expect(within(inspector).getAllByText(/person_bob/i).length).toBeGreaterThan(0);
  });

  it("uses arrow keys to activate the highlighted command palette result", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");
    const palette = screen.getByRole("dialog", { name: /命令面板/i });

    await user.keyboard("{ArrowDown}{ArrowDown}");
    expect(within(palette).getByRole("button", { name: /Scene 对话 view/i })).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Enter}");
    expect(screen.queryByRole("dialog", { name: /命令面板/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Scene 对话/i })).toBeInTheDocument();
  });

  it("uses the command palette to focus the current node neighborhood", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");
    const palette = screen.getByRole("dialog", { name: /命令面板/i });

    await user.type(within(palette).getByLabelText(/命令搜索/i), "Focus Alice");
    await user.keyboard("{Enter}");

    const status = screen.getByRole("region", { name: /过滤状态/i });
    expect(within(status).getByText(/Focus Alice/i)).toBeInTheDocument();
    expect(within(status).getByText(/5 \/ 8 nodes/i)).toBeInTheDocument();
  });

  it("runs chat turns through the local skill bridge by default without a WebUI token", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      if (url === "/api/runtime/status") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false }
          })
        } as Response;
      }
      if (url === "/api/summary") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { source: "local_skill", person_count: 8, relation_count: 9, memory_count: 3, open_local_branch_count: 0 }
          })
        } as Response;
      }
      if (url === "/api/scenes") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: {
              source: "local_skill",
              scenes: [{ scene_id: "scene_workroom", scene_summary: "产品例会与关系复盘", scene_type: "work_discussion", participant_count: 3 }]
            }
          })
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ok: true,
          data: {
            mode: "local_skill",
            provider: "mock",
            adapter: "claude",
            text: "local skill reply",
            event_id: "evt_local",
            retrieval_package: { scene_id: "scene_workroom" }
          }
        })
      } as Response;
    });

    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
    await user.click(screen.getByRole("button", { name: /运行 turn/i }));

    await waitFor(() => {
      expect(screen.getByText(/local skill reply/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/事件：evt_local/i)).toBeInTheDocument();
    expect(screen.getAllByText(/通道：local_skill · mock/i).some((node) => node.className === "response-box")).toBe(true);
    const chatCall = fetchMock.mock.calls.find(([url]) => url === "/api/chat/run-turn");
    expect(chatCall).toEqual([
      "/api/chat/run-turn",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ scene_id: "scene_workroom", input: "你好" })
      })
    ]);
    const [, init] = chatCall || [];
    expect(JSON.stringify(init?.headers || {})).not.toContain("Authorization");
  });

  it("uses the first local bridge scene as the no-token default chat scene", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      if (url === "/api/runtime/status") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false }
          })
        } as Response;
      }
      if (url === "/api/summary") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { source: "local_skill", person_count: 2, relation_count: 1, memory_count: 1, open_local_branch_count: 0 }
          })
        } as Response;
      }
      if (url === "/api/scenes") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: {
              source: "local_skill",
              scenes: [{ scene_id: "scene_real", scene_summary: "真实本地场景", scene_type: "work_discussion", participant_count: 2 }]
            }
          })
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          ok: true,
          data: {
            mode: "local_skill",
            provider: "mock",
            adapter: "claude",
            text: "real scene reply",
            event_id: "evt_real",
            retrieval_package: { scene_id: "scene_real" }
          }
        })
      } as Response;
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/真实本地场景/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
    await user.click(screen.getByRole("button", { name: /运行 turn/i }));

    await waitFor(() => {
      expect(screen.getByText(/real scene reply/i)).toBeInTheDocument();
    });
    const chatCall = fetchMock.mock.calls.find(([url]) => url === "/api/chat/run-turn");
    expect(chatCall?.[1]?.body).toBe(JSON.stringify({ scene_id: "scene_real", input: "你好" }));
  });

  it("does not send chat when the local runtime has no scenes", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      if (url === "/api/runtime/status") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false }
          })
        } as Response;
      }
      if (url === "/api/summary") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { source: "local_skill", db_exists: true, person_count: 0, relation_count: 0, memory_count: 0, open_local_branch_count: 0 }
          })
        } as Response;
      }
      if (url === "/api/scenes") {
        return {
          ok: true,
          json: async () => ({ ok: true, data: { source: "local_skill", scenes: [] } })
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({ ok: true, data: { text: "unexpected" } })
      } as Response;
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Local runtime 暂无 scenes/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
    await user.click(screen.getByRole("button", { name: /运行 turn/i }));

    expect(screen.getAllByText(/请先运行 bootstrap .* seed-demo/i).some((node) => node.className === "response-box")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/chat/run-turn")).toBe(false);
  });

  it("loads real local bridge runtime status for the default channel", async () => {
    localStorage.removeItem("we_together_demo_mode");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => ({
      ok: true,
      json: async () => ({
        ok: true,
        data: url === "/api/scenes"
          ? { source: "local_skill", scenes: [] }
          : url === "/api/summary"
            ? { source: "local_skill", person_count: 0, relation_count: 0, memory_count: 0, open_local_branch_count: 0 }
            : { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false }
      })
    } as Response));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Local skill bridge · mock · claude/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/local_skill · mock · claude/i)).toBeInTheDocument();
  });

  it("loads the complete local bridge cockpit dataset without falling back to demo graph data", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const dataByUrl: Record<string, unknown> = {
        "/api/runtime/status": { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false },
        "/api/summary": { source: "local_skill", person_count: 1, relation_count: 0, memory_count: 1, open_local_branch_count: 1 },
        "/api/scenes": {
          source: "local_skill",
          scenes: [{ scene_id: "scene_local", scene_summary: "真实 cockpit scene", scene_type: "work_discussion", participant_count: 1 }]
        },
        "/api/graph": {
          source: "local_skill",
          nodes: [
            { id: "person_local", label: "Local Operator", type: "person", scene_id: "scene_local", active_in_scene: true, data: { primary_name: "Local Operator" } },
            { id: "memory_local", label: "真实导入记忆", type: "memory", active_in_scene: true, data: { summary: "真实导入记忆" } }
          ],
          edges: [{ id: "edge_local_memory", source: "person_local", target: "memory_local", label: "remembers", type: "memory_owner" }]
        },
        "/api/events?limit=20": { source: "local_skill", events: [{ event_id: "evt_local", summary: "真实事件流" }] },
        "/api/patches": { source: "local_skill", patches: [{ patch_id: "patch_local", operation: "create_memory", status: "applied" }] },
        "/api/snapshots?limit=20": { source: "local_skill", snapshots: [{ snapshot_id: "snap_local", summary: "真实快照" }] },
        "/api/world": { source: "local_skill", objects: [{ object_id: "obj_local", name: "真实对象", status: "active" }], places: [], projects: [] },
        "/api/branches?status=open": {
          source: "local_skill",
          branches: [{
            branch_id: "branch_local",
            reason: "真实 operator gate",
            candidates: [{ candidate_id: "cand_local", label: "本地修补", confidence: 0.7, payload_json: { effect_patches: [] } }]
          }]
        }
      };
      return {
        ok: true,
        json: async () => ({ ok: true, data: dataByUrl[String(url)] ?? dataByUrl["/api/runtime/status"] })
      } as Response;
    });

    render(<App />);

    await waitFor(() => expect(screen.getAllByText(/Local Operator/i).length).toBeGreaterThan(0));
    expect(within(screen.getByRole("region", { name: /图谱画布/i })).queryByRole("button", { name: /^Alice$/i })).not.toBeInTheDocument();
    expect(screen.getByText(/真实事件流/i)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^世界$/i }));
    expect(screen.getByText(/真实对象/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^复核$/i }));
    expect(screen.getByText(/branch_local/i)).toBeInTheDocument();
    expect(screen.getAllByText(/本地修补/i).length).toBeGreaterThan(0);

    const urls = fetchMock.mock.calls.map(([calledUrl]) => String(calledUrl));
    expect(urls).toEqual(expect.arrayContaining([
      "/api/graph",
      "/api/events?limit=20",
      "/api/patches",
      "/api/snapshots?limit=20",
      "/api/world",
      "/api/branches?status=open"
    ]));
  });

  it("can seed, import narration, and resolve branches through the local bridge without Authorization", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      const dataByUrl: Record<string, unknown> = {
        "/api/runtime/status": { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false },
        "/api/summary": { source: "local_skill", person_count: 0, relation_count: 0, memory_count: 0, open_local_branch_count: 1 },
        "/api/scenes": { source: "local_skill", scenes: [] },
        "/api/graph": { source: "local_skill", nodes: [], edges: [] },
        "/api/events?limit=20": { source: "local_skill", events: [] },
        "/api/patches": { source: "local_skill", patches: [] },
        "/api/snapshots?limit=20": { source: "local_skill", snapshots: [] },
        "/api/world": { source: "local_skill", objects: [], places: [], projects: [] },
        "/api/branches?status=open": {
          source: "local_skill",
          branches: [{
            branch_id: "branch_local",
            reason: "operator gate",
            candidates: [{ candidate_id: "cand_local", label: "保留", confidence: 0.4, payload_json: { effect_patches: [] } }]
          }]
        }
      };
      if (url === "/api/seed-demo") {
        return { ok: true, json: async () => ({ ok: true, data: { source: "local_skill", seed: { scenes: { work: "scene_seeded" } } } }) } as Response;
      }
      if (url === "/api/import/narration") {
        expect(init?.body).toBe(JSON.stringify({ text: "小明和小红是朋友。", source_name: "webui-narration" }));
        return { ok: true, json: async () => ({ ok: true, data: { source: "local_skill", result: { event_id: "evt_import" } } }) } as Response;
      }
      if (url === "/api/branches/branch_local/resolve") {
        return { ok: true, json: async () => ({ ok: true, data: { source: "local_skill", branch_id: "branch_local", selected_candidate_id: "cand_local" } }) } as Response;
      }
      return {
        ok: true,
        json: async () => ({ ok: true, data: dataByUrl[String(url)] ?? dataByUrl["/api/runtime/status"] })
      } as Response;
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText(/Local runtime 暂无 scenes/i)).toBeInTheDocument());

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Seed demo/i }));
    await waitFor(() => expect(screen.getAllByText(/scene_seeded/i).length).toBeGreaterThan(0));

    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Narration import/i), "小明和小红是朋友。");
    await user.click(screen.getByRole("button", { name: /导入 narration/i }));
    await waitFor(() => expect(screen.getAllByText(/evt_import/i).length).toBeGreaterThan(0));

    await user.click(screen.getByRole("button", { name: /^复核$/i }));
    const queue = screen.getAllByRole("region", { name: /复核队列/i })[0];
    await user.click(within(queue).getByRole("button", { name: /应用候选/i }));
    await user.click(within(queue).getByRole("button", { name: /确认应用/i }));
    await waitFor(() => expect(screen.getByText(/"selected_candidate_id": "cand_local"/i)).toBeInTheDocument());

    const localPostCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(localPostCalls.map(([calledUrl]) => String(calledUrl))).toEqual(expect.arrayContaining([
      "/api/seed-demo",
      "/api/import/narration",
      "/api/branches/branch_local/resolve"
    ]));
    for (const [, init] of localPostCalls) {
      expect(JSON.stringify(init?.headers || {})).not.toContain("Authorization");
    }
    const resolveCall = localPostCalls.find(([calledUrl]) => calledUrl === "/api/branches/branch_local/resolve");
    expect(JSON.parse(String(resolveCall?.[1]?.body))).toMatchObject({
      candidate_id: "cand_local",
      reason: "operator approved via WebUI"
    });
  });

  it("passes the operator note to local branch resolution", async () => {
    localStorage.removeItem("we_together_demo_mode");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      const dataByUrl: Record<string, unknown> = {
        "/api/runtime/status": { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false },
        "/api/summary": { source: "local_skill", person_count: 0, relation_count: 0, memory_count: 0, open_local_branch_count: 1 },
        "/api/scenes": { source: "local_skill", scenes: [] },
        "/api/graph": { source: "local_skill", nodes: [], edges: [] },
        "/api/events?limit=20": { source: "local_skill", events: [] },
        "/api/patches": { source: "local_skill", patches: [] },
        "/api/snapshots?limit=20": { source: "local_skill", snapshots: [] },
        "/api/world": { source: "local_skill", objects: [], places: [], projects: [], agent_drives: [], autonomous_actions: [] },
        "/api/branches?status=open": {
          source: "local_skill",
          branches: [{
            branch_id: "branch_note",
            reason: "operator gate",
            candidates: [{ candidate_id: "cand_note", label: "应用人工复核", confidence: 0.8, payload_json: { effect_patches: [] } }]
          }]
        }
      };
      if (url === "/api/branches/branch_note/resolve") {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            data: { source: "local_skill", branch_id: "branch_note", selected_candidate_id: "cand_note", received: JSON.parse(String(init?.body)) }
          })
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({ ok: true, data: dataByUrl[String(url)] ?? dataByUrl["/api/runtime/status"] })
      } as Response;
    });

    render(<App />);
    await waitFor(() => expect(screen.getAllByText(/Local skill bridge/i).length).toBeGreaterThan(0));

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^复核$/i }));
    const queue = screen.getAllByRole("region", { name: /复核队列/i })[0];
    await user.type(within(queue).getByLabelText(/复核说明/i), "人工复核说明进入审计链");
    await user.click(within(queue).getByRole("button", { name: /应用候选/i }));
    await user.click(within(queue).getByRole("button", { name: /确认应用/i }));

    await waitFor(() => expect(screen.getAllByText(/人工复核说明进入审计链/i).length).toBeGreaterThan(1));
    const resolveCall = fetchMock.mock.calls.find(([calledUrl]) => calledUrl === "/api/branches/branch_note/resolve");
    expect(JSON.parse(String(resolveCall?.[1]?.body))).toMatchObject({
      candidate_id: "cand_note",
      reason: "人工复核说明进入审计链"
    });
  });

  it("explains an empty operator review queue", async () => {
    localStorage.removeItem("we_together_demo_mode");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const dataByUrl: Record<string, unknown> = {
        "/api/runtime/status": { mode: "local_skill", provider: "mock", adapter: "claude", token_required: false },
        "/api/summary": { source: "local_skill", person_count: 0, relation_count: 0, memory_count: 0, open_local_branch_count: 0 },
        "/api/scenes": { source: "local_skill", scenes: [] },
        "/api/graph": { source: "local_skill", nodes: [], edges: [] },
        "/api/events?limit=20": { source: "local_skill", events: [] },
        "/api/patches": { source: "local_skill", patches: [] },
        "/api/snapshots?limit=20": { source: "local_skill", snapshots: [] },
        "/api/world": { source: "local_skill", objects: [], places: [], projects: [], agent_drives: [], autonomous_actions: [] },
        "/api/branches?status=open": { source: "local_skill", branches: [] }
      };
      return {
        ok: true,
        json: async () => ({ ok: true, data: dataByUrl[String(url)] ?? dataByUrl["/api/runtime/status"] })
      } as Response;
    });

    render(<App />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^复核$/i }));

    const queue = screen.getAllByRole("region", { name: /复核队列/i })[0];
    await waitFor(() => expect(within(queue).getByText(/当前没有待处理 local branch/i)).toBeInTheDocument());
    expect(within(queue).getByText(/0 open branches/i)).toBeInTheDocument();
  });

  it("explains local bridge availability instead of asking for a token when the default chat channel is down", async () => {
    localStorage.removeItem("we_together_demo_mode");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("bridge offline"));
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Local skill bridge offline/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /^Alice$/i })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: /过滤状态/i })).toHaveTextContent("0 / 0 nodes");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
    await user.click(screen.getByRole("button", { name: /运行 turn/i }));

    await waitFor(() => {
      expect(screen.getByText(/Local skill bridge unavailable/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/远程 token 只用于高级部署模式/i)).toBeInTheDocument();
    expect(screen.queryByText(/连接 WebUI token 后会调用真实/i)).not.toBeInTheDocument();
  });

  it("reports remote API errors separately when an advanced token is configured", async () => {
    localStorage.removeItem("we_together_demo_mode");
    sessionStorage.setItem("we_together_webui_token", "remote-token");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("401 unauthorized"));
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^对话$/i }));
    await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
    await user.click(screen.getByRole("button", { name: /运行 turn/i }));

    await waitFor(() => {
      expect(screen.getByText(/Remote API unavailable/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Local skill bridge unavailable/i)).not.toBeInTheDocument();
  });

  it("uses the command palette to clear active graph filters", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/搜索/i), "memory");
    expect(screen.getByRole("region", { name: /过滤状态/i })).toHaveTextContent("2 / 8 nodes");

    await user.click(screen.getByRole("button", { name: /命令 Ctrl K/i }));
    const palette = screen.getByRole("dialog", { name: /命令面板/i });
    await user.type(within(palette).getByLabelText(/命令搜索/i), "Clear filters");
    await user.keyboard("{Enter}");

    expect(screen.queryByRole("dialog", { name: /命令面板/i })).not.toBeInTheDocument();
    const status = screen.getByRole("region", { name: /过滤状态/i });
    expect(within(status).getByText(/8 \/ 8 nodes/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/搜索/i)).toHaveValue("");
  });

  it("turns operator review into a triage queue with decision preview", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^复核$/i }));

    const queue = screen.getAllByRole("region", { name: /复核队列/i })[0];
    expect(within(queue).getByText(/Open branches/i)).toBeInTheDocument();
    expect(within(queue).getByLabelText(/2 candidates/i)).toBeInTheDocument();

    await user.click(within(queue).getByRole("button", { name: /执行 unmerge/i }));
    await user.type(within(queue).getByLabelText(/复核说明/i), "人工复核通过");

    const preview = within(queue).getByRole("region", { name: /决策预览/i });
    expect(preview).toBeInTheDocument();
    expect(within(preview).getByText(/cand_unmerge/i)).toBeInTheDocument();
    expect(within(preview).getByText(/人工复核通过/i)).toBeInTheDocument();
  });

  it("requires confirmation and exposes candidate risk before applying review decisions", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^复核$/i }));

    const queue = screen.getAllByRole("region", { name: /复核队列/i })[0];
    await user.click(within(queue).getByRole("button", { name: /执行 unmerge/i }));

    const risk = within(queue).getByRole("region", { name: /复核风险/i });
    expect(within(risk).getByText(/High risk/i)).toBeInTheDocument();
    expect(within(risk).getByText(/Operator gated/i)).toBeInTheDocument();

    const impact = within(queue).getByRole("region", { name: /候选影响/i });
    expect(within(impact).getByText(/unmerge_person/i)).toBeInTheDocument();
    expect(within(impact).getByText(/1 patch/i)).toBeInTheDocument();

    await user.click(within(queue).getByRole("button", { name: /^应用候选$/i }));
    expect(within(queue).getByRole("button", { name: /^确认应用$/i })).toBeInTheDocument();
    expect(screen.queryByText(/"selected": "cand_unmerge"/i)).not.toBeInTheDocument();

    await user.click(within(queue).getByRole("button", { name: /^确认应用$/i }));
    expect(screen.getByText(/"selected": "cand_unmerge"/i)).toBeInTheDocument();
  });

  it("shows runtime telemetry on the metrics view", async () => {
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^指标$/i }));

    const telemetry = screen.getByRole("region", { name: /运行遥测/i });
    expect(within(telemetry).getByText(/Graph load/i)).toBeInTheDocument();
    expect(within(telemetry).getByText(/Event flow/i)).toBeInTheDocument();
    expect(within(telemetry).getByText(/Branch pressure/i)).toBeInTheDocument();
    expect(within(telemetry).getAllByText(/Local runtime/i).length).toBeGreaterThan(0);
  });
});
