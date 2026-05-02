import {
  Activity,
  Boxes,
  BrainCircuit,
  CircleDot,
  Command,
  GitBranch,
  GlassWater,
  Layers3,
  Lock,
  Maximize2,
  MessageSquareText,
  Minus,
  MoonStar,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  SunMedium,
  X
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { CommandPalette } from "./components/CommandPalette";
import type { CommandItem } from "./components/CommandPalette";
import { InspectorPanel } from "./components/InspectorPanel";
import { ReviewPanel } from "./components/ReviewPanel";
import type { Branch, BranchCandidate } from "./components/ReviewPanel";

type ThemeMode = "glass" | "flat";
type ViewMode = "graph" | "chat" | "world" | "review" | "metrics";
type NodeType = "person" | "relation" | "memory" | "group" | "scene" | "state" | "object" | "place" | "project";

type GraphNode = {
  id: string;
  label: string;
  type: NodeType;
  scene_id?: string;
  active_in_scene?: boolean;
  data?: Record<string, unknown>;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
};

type Scene = {
  scene_id: string;
  scene_summary?: string;
  scene_type?: string;
  participant_count?: number;
};

type PositionedEdge = GraphEdge & {
  sourcePosition?: { x: number; y: number };
  targetPosition?: { x: number; y: number };
};

type ActivitySelection = {
  laneTitle: string;
  id: string;
  item: Record<string, unknown>;
  relatedNodeIds: string[];
};

type RecentItem = {
  kind: string;
  id: string;
  label: string;
};

type FilterChip = {
  label: string;
  value: string;
};

type SummaryValue = number | string | boolean;

type RelatedNode = {
  node: GraphNode;
  edge: GraphEdge;
};

type ActivityLaneFilter = "all" | "events" | "patches" | "snapshots";

type WorkspaceData = {
  summary?: Record<string, SummaryValue>;
  scenes: Scene[];
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  events: Array<Record<string, unknown>>;
  patches: Array<Record<string, unknown>>;
  snapshots: Array<Record<string, unknown>>;
  branches: Branch[];
  world: {
    objects: Array<Record<string, unknown>>;
    places: Array<Record<string, unknown>>;
    projects: Array<Record<string, unknown>>;
    agent_drives: Array<Record<string, unknown>>;
    autonomous_actions: Array<Record<string, unknown>>;
  };
};

type RuntimeStatus = {
  mode?: string;
  provider?: string;
  adapter?: string;
  tenant_id?: string;
  token_required?: boolean;
};

const emptyWorld = { objects: [], places: [], projects: [], agent_drives: [], autonomous_actions: [] };

const emptyWorkspaceData: WorkspaceData = {
  summary: {
    person_count: 0,
    relation_count: 0,
    memory_count: 0,
    event_count: 0,
    open_local_branch_count: 0
  },
  scenes: [],
  graphNodes: [],
  graphEdges: [],
  events: [],
  patches: [],
  snapshots: [],
  branches: [],
  world: emptyWorld
};

const demoData: WorkspaceData = {
  summary: {
    person_count: 8,
    relation_count: 9,
    memory_count: 3,
    event_count: 4,
    open_local_branch_count: 1
  },
  scenes: [
    {
      scene_id: "scene_workroom",
      scene_summary: "产品例会与关系复盘",
      scene_type: "work_discussion",
      participant_count: 5
    },
    {
      scene_id: "scene_private",
      scene_summary: "小范围情绪回声",
      scene_type: "private_chat",
      participant_count: 2
    }
  ],
  graphNodes: [
    {
      id: "person_0b32fe26fc64",
      label: "Alice",
      type: "person",
      scene_id: "scene_workroom",
      active_in_scene: true,
      data: {
        primary_name: "Alice",
        status: "active",
        persona_summary: "理性领导者",
        style_summary: "简洁果断",
        boundary_summary: "保护个人时间",
        confidence: 0.9
      }
    },
    {
      id: "person_bob",
      label: "Bob",
      type: "person",
      scene_id: "scene_workroom",
      active_in_scene: true,
      data: { primary_name: "Bob", status: "active", persona_summary: "协调者", confidence: 0.84 }
    },
    {
      id: "person_carol",
      label: "Carol",
      type: "person",
      scene_id: "scene_workroom",
      active_in_scene: true,
      data: { primary_name: "Carol", status: "active", persona_summary: "导师型角色", confidence: 0.81 }
    },
    {
      id: "person_dan",
      label: "Dan",
      type: "person",
      scene_id: "scene_private",
      data: { primary_name: "Dan", status: "active", confidence: 0.77 }
    },
    {
      id: "person_eve",
      label: "Eve",
      type: "person",
      scene_id: "scene_workroom",
      data: { primary_name: "Eve", status: "active", confidence: 0.72 }
    },
    {
      id: "memory_launch",
      label: "Alice/Eve/Frank 的大学聚会",
      type: "memory",
      active_in_scene: true,
      data: { memory_type: "shared_memory", summary: "三人在大学聚会后形成稳定协作记忆" }
    },
    {
      id: "memory_dan",
      label: "Alice 和 Dan 的寻回之夜",
      type: "memory",
      data: { memory_type: "relationship_memory", summary: "一次延迟复盘改变了双方关系判断" }
    },
    {
      id: "group_core",
      label: "CoreEng",
      type: "group",
      active_in_scene: true,
      data: { group_type: "work", status: "active" }
    }
  ],
  graphEdges: [
    { id: "edge_ab", source: "person_0b32fe26fc64", target: "person_bob", label: "ice_bob_colleague", type: "relation" },
    { id: "edge_ac", source: "person_0b32fe26fc64", target: "person_carol", label: "mentor", type: "relation" },
    { id: "edge_bg", source: "person_bob", target: "group_core", label: "member" },
    { id: "edge_ag", source: "person_0b32fe26fc64", target: "group_core", label: "lead" },
    { id: "edge_am", source: "person_0b32fe26fc64", target: "memory_launch", label: "remembers" },
    { id: "edge_em", source: "person_eve", target: "memory_launch", label: "remembers" },
    { id: "edge_dm", source: "person_dan", target: "memory_dan", label: "remembers" },
    { id: "edge_cm", source: "person_carol", target: "memory_dan", label: "reviewed" }
  ],
  events: [
    { event_id: "evt_830f92e0de3a47", summary: "持续指导 Carol 的职业路径" },
    { event_id: "evt_d9c42dd7e7494f", summary: "一起照顾生病的母亲" },
    { event_id: "evt_37a7b613a41c47", summary: "大学毕业十年聚会" },
    { event_id: "evt_83895150f04340", summary: "一起搬进新家" }
  ],
  patches: [
    { patch_id: "patch_0727", operation: "create_memory", status: "applied" },
    { patch_id: "patch_d475", operation: "create_memory", status: "applied" },
    { patch_id: "patch_66db", operation: "update_state", status: "applied" }
  ],
  snapshots: [
    { snapshot_id: "snap_421", summary: "after narration import" },
    { snapshot_id: "snap_558", summary: "after dialogue turn" }
  ],
  branches: [
    {
      branch_id: "branch_unmerge_review",
      reason: "operator gate: merged person contradiction review",
      candidates: [
        { candidate_id: "cand_keep", label: "保留 merged 状态", confidence: 0.34 },
        {
          candidate_id: "cand_unmerge",
          label: "执行 unmerge",
          confidence: 0.66,
          payload_json: {
            effect_patches: [
              {
                operation: "unmerge_person",
                target_type: "person",
                target_id: "person_0b32fe26fc64"
              }
            ],
            evidence_ids: ["evt_830f92e0de3a47"]
          }
        }
      ]
    }
  ],
  world: {
    objects: [
      { object_id: "obj_shared_doc", name: "关系复盘文档", kind: "document", status: "active" }
    ],
    places: [
      { place_id: "place_studio", name: "工作室", place_type: "room", status: "active" }
    ],
    projects: [
      { project_id: "project_memory_mesh", name: "Memory Mesh", status: "active" }
    ],
    agent_drives: [],
    autonomous_actions: []
  }
};

function demoModeEnabled(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem("we_together_demo_mode") === "1"
    || new URLSearchParams(window.location.search).get("demo") === "1";
}

const navItems: Array<{ id: ViewMode; label: string; icon: typeof Layers3 }> = [
  { id: "graph", label: "图谱", icon: Layers3 },
  { id: "chat", label: "对话", icon: MessageSquareText },
  { id: "world", label: "世界", icon: Boxes },
  { id: "review", label: "复核", icon: ShieldCheck },
  { id: "metrics", label: "指标", icon: Activity }
];

const typeMeta: Record<NodeType, { label: string; color: string; glow: string }> = {
  person: { label: "person", color: "#69d7ff", glow: "rgba(105, 215, 255, .3)" },
  relation: { label: "relation", color: "#78d7c1", glow: "rgba(120, 215, 193, .25)" },
  memory: { label: "memory", color: "#f4c96b", glow: "rgba(244, 201, 107, .28)" },
  group: { label: "group", color: "#8ee6a8", glow: "rgba(142, 230, 168, .24)" },
  scene: { label: "scene", color: "#b8a3ff", glow: "rgba(184, 163, 255, .24)" },
  state: { label: "state", color: "#ff9f8a", glow: "rgba(255, 159, 138, .24)" },
  object: { label: "object", color: "#9de1ff", glow: "rgba(157, 225, 255, .22)" },
  place: { label: "place", color: "#a9e88f", glow: "rgba(169, 232, 143, .22)" },
  project: { label: "project", color: "#ffcf8a", glow: "rgba(255, 207, 138, .24)" }
};

class ApiClient {
  token?: string;

  constructor(token?: string) {
    this.token = token || undefined;
  }

  async request<T>(url: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((init.headers as Record<string, string> | undefined) || {})
    };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const response = await fetch(url, {
      ...init,
      headers
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.error?.message || response.statusText || `HTTP ${response.status}`);
    }
    return payload.data;
  }
}

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function compactId(id: string): string {
  return id.length > 18 ? `${id.slice(0, 10)}...${id.slice(-4)}` : id;
}

function isFormInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
}

function fullRecordText(record: Record<string, unknown>): string {
  return Object.values(record).map(asText).join(" ");
}

function getActivityRecordId(item: Record<string, unknown>, idKey: string, fallback: number): string {
  return String(item[idKey] || fallback);
}

function getActivitySummary(item: Record<string, unknown>): string {
  return asText(item.summary || item.operation || item.status);
}

function inferRelatedNodeIds(record: Record<string, unknown>, nodes: GraphNode[]): string[] {
  const haystack = fullRecordText(record).toLowerCase();
  return nodes
    .filter((node) => haystack.includes(node.label.toLowerCase()) || haystack.includes(node.id.toLowerCase()))
    .map((node) => node.id);
}

function getDirectNeighborIds(nodeId: string, edges: GraphEdge[]): Set<string> {
  const ids = new Set<string>([nodeId]);
  edges.forEach((edge) => {
    if (edge.source === nodeId) ids.add(edge.target);
    if (edge.target === nodeId) ids.add(edge.source);
  });
  return ids;
}

function getRelatedNodes(node: GraphNode | null | undefined, nodes: GraphNode[], edges: GraphEdge[]): RelatedNode[] {
  if (!node) return [];
  const byId = new Map(nodes.map((item) => [item.id, item]));
  const related = new Map<string, RelatedNode>();
  edges.forEach((edge) => {
    const relatedId = edge.source === node.id ? edge.target : edge.target === node.id ? edge.source : "";
    if (!relatedId || related.has(relatedId)) return;
    const relatedNode = byId.get(relatedId);
    if (relatedNode) related.set(relatedId, { node: relatedNode, edge });
  });
  return [...related.values()];
}

function getNodePosition(index: number, total: number, type: NodeType): { x: number; y: number } {
  if (type === "memory") {
    return { x: 42 + (index % 2) * 30, y: 74 };
  }
  if (type === "group") {
    return { x: 18, y: 74 };
  }
  const usable = Math.max(1, total - 1);
  return {
    x: 12 + (index % 5) * (76 / usable),
    y: 28 + Math.floor(index / 5) * 25
  };
}

function buildLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const personCount = Math.max(1, nodes.filter((node) => node.type === "person").length);
  let personIndex = 0;
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((node, index) => {
    const position = getNodePosition(node.type === "person" ? personIndex++ : index, personCount, node.type);
    positions.set(node.id, position);
  });
  return {
    positionedNodes: nodes.map((node) => ({ ...node, position: positions.get(node.id) || { x: 50, y: 50 } })),
    positionedEdges: edges
      .map((edge) => ({
        ...edge,
        sourcePosition: positions.get(edge.source),
        targetPosition: positions.get(edge.target)
      }))
      .filter((edge) => edge.sourcePosition && edge.targetPosition)
  };
}

function normalizeData(data: WorkspaceData): WorkspaceData {
  return {
    ...emptyWorkspaceData,
    ...data,
    world: {
      ...emptyWorld,
      ...(data.world || {})
    }
  };
}

function App() {
  const useDemoData = demoModeEnabled();
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem("we_together_theme");
    return stored === "flat" ? "flat" : "glass";
  });
  const [view, setView] = useState<ViewMode>("graph");
  const [token, setToken] = useState(() => sessionStorage.getItem("we_together_webui_token") || "");
  const [tokenDraft, setTokenDraft] = useState(token);
  const [client, setClient] = useState<ApiClient | null>(() => (token ? new ApiClient(token) : null));
  const [sceneId, setSceneId] = useState("");
  const [nodeType, setNodeType] = useState<"all" | NodeType>("all");
  const [query, setQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const commandInputRef = useRef<HTMLInputElement | null>(null);
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [data, setData] = useState<WorkspaceData>(() => (useDemoData ? demoData : emptyWorkspaceData));
  const [selected, setSelected] = useState<GraphNode | undefined>(() => (useDemoData ? demoData.graphNodes[0] : undefined));
  const [selectedEdge, setSelectedEdge] = useState<PositionedEdge | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<ActivitySelection | null>(null);
  const [fitSignal, setFitSignal] = useState(0);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [pinnedNode, setPinnedNode] = useState<GraphNode | null>(null);
  const [compareNode, setCompareNode] = useState<GraphNode | null>(null);
  const [copiedInspector, setCopiedInspector] = useState(false);
  const [recentItems, setRecentItems] = useState<RecentItem[]>(() => (
    useDemoData ? [{ kind: "node", id: demoData.graphNodes[0].id, label: demoData.graphNodes[0].label }] : []
  ));
  const [inspectorOpen, setInspectorOpen] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
    return !window.matchMedia("(max-width: 840px)").matches;
  });
  const [entityDetail, setEntityDetail] = useState<Record<string, unknown> | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatOutput, setChatOutput] = useState("等待一次 scene-grounded response。");
  const [retrievalPackage, setRetrievalPackage] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [runtimeStatusError, setRuntimeStatusError] = useState("");
  const [localRuntimeLoaded, setLocalRuntimeLoaded] = useState(false);
  const [runtimeActionResult, setRuntimeActionResult] = useState<Record<string, unknown> | null>(null);
  const [narrationInput, setNarrationInput] = useState("");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("we_together_theme", theme);
  }, [theme]);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0 });
  }, [view]);

  function pushRecent(item: RecentItem) {
    setRecentItems((current) => [item, ...current.filter((entry) => entry.id !== item.id)].slice(0, 5));
  }

  async function loadData(activeClient = client) {
    if (!activeClient) {
      if (useDemoData) {
        setData(demoData);
        setSelected((current) => demoData.graphNodes.find((node) => node.id === current?.id) || demoData.graphNodes[0]);
        setLocalRuntimeLoaded(false);
        return;
      }
      setLoading(true);
      try {
        const localClient = new ApiClient();
        const [summary, scenes, graph, events, patches, snapshots, world, branches] = await Promise.all([
          localClient.request<Record<string, number | string | boolean>>("/api/summary"),
          localClient.request<{ scenes: Scene[] }>("/api/scenes"),
          localClient.request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
            sceneId ? `/api/graph?scene_id=${encodeURIComponent(sceneId)}` : "/api/graph"
          ),
          localClient.request<{ events: Array<Record<string, unknown>> }>("/api/events?limit=20"),
          localClient.request<{ patches: Array<Record<string, unknown>> }>("/api/patches"),
          localClient.request<{ snapshots: Array<Record<string, unknown>> }>("/api/snapshots?limit=20"),
          localClient.request<WorkspaceData["world"]>(
            sceneId ? `/api/world?scene_id=${encodeURIComponent(sceneId)}` : "/api/world"
          ),
          localClient.request<{ branches: Branch[] }>("/api/branches?status=open")
        ]);
        const next = normalizeData({
          summary,
          scenes: scenes.scenes || [],
          graphNodes: graph.nodes || [],
          graphEdges: graph.edges || [],
          events: events.events || [],
          patches: patches.patches || [],
          snapshots: snapshots.snapshots || [],
          world: world || emptyWorld,
          branches: branches.branches || []
        });
        setData(next);
        setSelected((current) => next.graphNodes.find((node) => node.id === current?.id) || next.graphNodes[0]);
        setLocalRuntimeLoaded(true);
      } catch {
        setData(emptyWorkspaceData);
        setSelected(emptyWorkspaceData.graphNodes[0]);
        setLocalRuntimeLoaded(false);
      } finally {
        setLoading(false);
      }
      return;
    }
    setLoading(true);
    setError("");
    try {
      await activeClient.request("/api/bootstrap");
      const [summary, scenes, graph, events, patches, snapshots, world, branches] = await Promise.all([
        activeClient.request<Record<string, SummaryValue>>("/api/summary"),
        activeClient.request<{ scenes: Scene[] }>("/api/scenes"),
        activeClient.request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
          sceneId ? `/api/graph?scene_id=${encodeURIComponent(sceneId)}` : "/api/graph"
        ),
        activeClient.request<{ events: Array<Record<string, unknown>> }>("/api/events?limit=20"),
        activeClient.request<{ patches: Array<Record<string, unknown>> }>("/api/patches"),
        activeClient.request<{ snapshots: Array<Record<string, unknown>> }>("/api/snapshots?limit=20"),
        activeClient.request<WorkspaceData["world"]>(
          sceneId ? `/api/world?scene_id=${encodeURIComponent(sceneId)}` : "/api/world"
        ),
        activeClient.request<{ branches: Branch[] }>("/api/branches?status=open")
      ]);
      const next = normalizeData({
        summary,
        scenes: scenes.scenes || [],
        graphNodes: graph.nodes || [],
        graphEdges: graph.edges || [],
        events: events.events || [],
        patches: patches.patches || [],
        snapshots: snapshots.snapshots || [],
        world: world || emptyWorld,
        branches: branches.branches || []
      });
      setData(next);
      setSelected((current) => next.graphNodes.find((node) => node.id === current?.id) || next.graphNodes[0] || demoData.graphNodes[0]);
      setLocalRuntimeLoaded(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, sceneId]);

  useEffect(() => {
    if (client) {
      setRuntimeStatus(null);
      setRuntimeStatusError("");
      return;
    }
    if (useDemoData) {
      setRuntimeStatus(null);
      setRuntimeStatusError("");
      return;
    }
    let cancelled = false;
    void new ApiClient().request<RuntimeStatus>("/api/runtime/status")
      .then((status) => {
        if (cancelled) return;
        setRuntimeStatus(status);
        setRuntimeStatusError("");
      })
      .catch((err) => {
        if (cancelled) return;
        setRuntimeStatus(null);
        setRuntimeStatusError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [client, useDemoData]);

  const focusNode = data.graphNodes.find((node) => node.id === focusNodeId);
  const focusNeighborIds = useMemo(() => (
    focusNodeId ? getDirectNeighborIds(focusNodeId, data.graphEdges) : null
  ), [data.graphEdges, focusNodeId]);

  const filteredNodes = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return data.graphNodes.filter((node) => {
      const matchesQuery = normalizedQuery
        ? `${node.label} ${node.id} ${node.type}`.toLowerCase().includes(normalizedQuery)
        : true;
      const matchesType = nodeType === "all" || node.type === nodeType;
      const matchesScene = !sceneId || node.scene_id === sceneId || node.active_in_scene;
      const matchesFocus = focusNeighborIds ? focusNeighborIds.has(node.id) : true;
      return matchesQuery && matchesType && matchesScene && matchesFocus;
    });
  }, [data.graphNodes, focusNeighborIds, nodeType, query, sceneId]);

  const filteredEdges = useMemo(() => {
    const visibleIds = new Set(filteredNodes.map((node) => node.id));
    return data.graphEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  }, [data.graphEdges, filteredNodes]);

  const layout = useMemo(() => buildLayout(filteredNodes, filteredEdges), [filteredNodes, filteredEdges]);
  const activeScene = data.scenes.find((scene) => scene.scene_id === sceneId);
  const filterChips: FilterChip[] = [
    ...(sceneId ? [{ label: "Scene", value: activeScene?.scene_summary || sceneId }] : []),
    ...(nodeType !== "all" ? [{ label: "Type", value: nodeType }] : []),
    ...(focusNode ? [{ label: "Focus", value: focusNode.label }] : []),
    ...(query.trim() ? [{ label: "Query", value: query.trim() }] : [])
  ];
  const hasActiveFilters = filterChips.length > 0;
  const runtimeProvider = asText(runtimeStatus?.provider || "unknown");
  const runtimeAdapter = asText(runtimeStatus?.adapter || "unknown");
  const channelLabel = client
    ? "Remote API"
    : runtimeStatus
      ? `Local skill bridge · ${runtimeProvider} · ${runtimeAdapter}`
      : runtimeStatusError
        ? "Local skill bridge offline"
        : "Local skill bridge";
  const localChannelDetail = runtimeStatus
    ? `${asText(runtimeStatus.mode || "local_skill")} · ${runtimeProvider} · ${runtimeAdapter}`
    : runtimeStatusError
      ? `待连接 · ${runtimeStatusError}`
      : "检测本地 bridge...";
  const metricsApiMode = client
    ? "Remote API"
    : runtimeStatus
      ? `Local runtime · ${runtimeProvider}`
      : runtimeStatusError
        ? "Local runtime offline"
        : "Local runtime";

  function clearFilters() {
    setSceneId("");
    setNodeType("all");
    setFocusNodeId(null);
    setQuery("");
  }

  function openCommandPalette() {
    setCommandOpen(true);
    setCommandQuery("");
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openCommandPalette();
        return;
      }
      if (event.key === "/" && !isFormInput(event.target)) {
        event.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      if (event.key === "Escape") {
        if (commandOpen) {
          event.preventDefault();
          setCommandOpen(false);
          return;
        }
        if (query) {
          event.preventDefault();
          setQuery("");
          return;
        }
        if (inspectorOpen) {
          event.preventDefault();
          setInspectorOpen(false);
        }
        return;
      }
      if (event.key.toLowerCase() === "f" && view === "graph" && !isFormInput(event.target)) {
        event.preventDefault();
        setFitSignal((value) => value + 1);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandOpen, inspectorOpen, query, view]);

  useEffect(() => {
    if (!commandOpen) return;
    commandInputRef.current?.focus();
  }, [commandOpen]);

  useEffect(() => {
    setCopiedInspector(false);
  }, [selected?.id, selectedEdge?.id, selectedActivity?.id, compareNode?.id]);

  async function handleTokenSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextToken = tokenDraft.trim();
    if (!nextToken) {
      sessionStorage.removeItem("we_together_webui_token");
      setToken("");
      setClient(null);
      setData(emptyWorkspaceData);
      return;
    }
    sessionStorage.setItem("we_together_webui_token", nextToken);
    setToken(nextToken);
    setClient(new ApiClient(nextToken));
  }

  async function selectNode(node: GraphNode) {
    setSelected(node);
    setSelectedEdge(null);
    setSelectedActivity(null);
    setCompareNode(null);
    setInspectorOpen(true);
    pushRecent({ kind: "node", id: node.id, label: node.label });
    setEntityDetail(null);
    setIsEditing(false);
    const defaultLabel = String(node.data?.primary_name || node.data?.summary || node.label || "");
    setEditValue(defaultLabel);
    if (!client) return;
    try {
      const detail = await client.request<Record<string, unknown>>(`/api/entities/${node.type}/${node.id}`);
      setEntityDetail(detail);
      const entity = detail.entity as Record<string, unknown> | undefined;
      setEditValue(String(entity?.primary_name || entity?.name || entity?.summary || node.label || ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function selectEdge(edge: PositionedEdge) {
    setSelectedEdge(edge);
    setSelectedActivity(null);
    setCompareNode(null);
    setInspectorOpen(true);
    pushRecent({ kind: "edge", id: edge.id, label: edge.label || edge.id });
  }

  function selectActivity(activity: ActivitySelection) {
    setSelectedActivity(activity);
    setSelectedEdge(null);
    setCompareNode(null);
    setInspectorOpen(true);
    pushRecent({ kind: activity.laneTitle.toLowerCase(), id: activity.id, label: getActivitySummary(activity.item) });
  }

  function focusSelectedNode() {
    if (!selected) return;
    setView("graph");
    setFocusNodeId(selected.id);
    setFitSignal((value) => value + 1);
  }

  async function saveEntity() {
    if (!client || !selected) return;
    const field = selected.type === "person" ? "primary_name" : "summary";
    const result = await client.request<Record<string, unknown>>(`/api/entities/${selected.type}/${selected.id}`, {
      method: "PATCH",
      body: JSON.stringify({ fields: { [field]: editValue } })
    });
    setLastResult(result);
    setIsEditing(false);
    await loadData();
  }

  async function runTurn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!chatInput.trim()) return;
    const activeScene = sceneId || data.scenes[0]?.scene_id;
    if (!activeScene) {
      if (client && error) {
        const message = `Remote API unavailable: ${error}\n\n请检查远程 API endpoint/token；本地默认通道可清空 token 后走 Local skill bridge。`;
        setChatOutput(message);
        setRetrievalPackage({ mode: "remote_api_unavailable", reason: error });
        return;
      }
      if (!client && !localRuntimeLoaded) {
        const reason = runtimeStatusError || "local bridge did not respond";
        const message = `Local skill bridge unavailable: ${reason}\n\n请通过 we-together webui 或 npm run dev 启动本地 bridge；远程 token 只用于高级部署模式。`;
        setError("");
        setChatOutput(message);
        setRetrievalPackage({ mode: "local_skill_unavailable", reason });
        return;
      }
      const message = client
        ? "需要至少一个 scene 才能运行对话。"
        : "Local runtime has no scenes yet.\n\n请先运行 bootstrap + seed-demo，或导入材料创建 scene 后再运行 turn。";
      setError(client ? message : "");
      setChatOutput(message);
      setRetrievalPackage({ mode: client ? "remote_api_no_scene" : "local_skill_no_scenes" });
      return;
    }
    const chatClient = client || new ApiClient();
    try {
      const result = await chatClient.request<Record<string, unknown>>("/api/chat/run-turn", {
        method: "POST",
        body: JSON.stringify({ scene_id: activeScene, input: chatInput })
      });
      setChatOutput(
        `${asText(result.text)}\n\n事件：${asText(result.event_id)}\n通道：${asText(result.mode || "remote_api")} · ${asText(result.provider || "unknown")}`
      );
      setRetrievalPackage((result.retrieval_package as Record<string, unknown>) || null);
      setChatInput("");
      await loadData();
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      if (client) {
        setChatOutput(
          `Remote API unavailable: ${reason}\n\n请检查远程 API endpoint/token；本地默认通道可清空 token 后走 Local skill bridge。`
        );
        setRetrievalPackage({ mode: "remote_api_unavailable", scene_id: activeScene, reason });
      } else {
        setChatOutput(
          `Local skill bridge unavailable: ${reason}\n\n请通过 we-together webui 或 npm run dev 启动本地 bridge；远程 token 只用于高级部署模式。`
        );
        setRetrievalPackage({ mode: "local_skill_unavailable", scene_id: activeScene, reason });
      }
    }
  }

  async function runLocalRuntimeAction(action: "bootstrap" | "seed-demo") {
    if (client) return;
    setLoading(true);
    setError("");
    try {
      const result = await new ApiClient().request<Record<string, unknown>>(`/api/${action}`, { method: "POST" });
      setRuntimeActionResult(result);
      setLastResult(result);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function importNarration() {
    if (!narrationInput.trim()) return;
    const actionClient = client || new ApiClient();
    setLoading(true);
    setError("");
    try {
      const result = await actionClient.request<Record<string, unknown>>("/api/import/narration", {
        method: "POST",
        body: JSON.stringify({ text: narrationInput.trim(), source_name: "webui-narration" })
      });
      setRuntimeActionResult(result);
      setLastResult(result);
      setNarrationInput("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function resolveBranch(branch: Branch, candidate: BranchCandidate, note = "") {
    const reason = note.trim() || "operator approved via WebUI";
    if (!client && !localRuntimeLoaded) {
      setLastResult({ mode: "demo", branch_id: branch.branch_id, selected: candidate.candidate_id, reason });
      return;
    }
    const actionClient = client || new ApiClient();
    try {
      const result = await actionClient.request<Record<string, unknown>>(`/api/branches/${branch.branch_id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ candidate_id: candidate.candidate_id, reason })
      });
      setLastResult(result);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const summary = data.summary || {};
  const selectedEntity = entityDetail?.entity as Record<string, unknown> | undefined;
  const selectedEdgeSource = selectedEdge ? data.graphNodes.find((node) => node.id === selectedEdge.source) : undefined;
  const selectedEdgeTarget = selectedEdge ? data.graphNodes.find((node) => node.id === selectedEdge.target) : undefined;
  const compareMode = Boolean(pinnedNode && compareNode);
  const inspectorRows = selectedActivity
    ? selectedActivity.item
    : selectedEdge
      ? {
          source: selectedEdgeSource?.label || selectedEdge.source,
          target: selectedEdgeTarget?.label || selectedEdge.target,
          relation: selectedEdge.label || "-",
          type: selectedEdge.type || "edge"
        }
      : selectedEntity || selected?.data || {};
  const activityRelatedIds = selectedActivity?.relatedNodeIds || [];
  const edgeRelatedIds = selectedEdge ? [selectedEdge.source, selectedEdge.target] : [];
  const hoverRelatedEdgeIds = hoveredNodeId
    ? layout.positionedEdges.filter((edge) => edge.source === hoveredNodeId || edge.target === hoveredNodeId).map((edge) => edge.id)
    : [];
  const highlightedNodeIds = new Set([...activityRelatedIds, ...edgeRelatedIds]);
  const highlightedEdgeIds = new Set([...(selectedEdge ? [selectedEdge.id] : []), ...hoverRelatedEdgeIds]);
  const selectedRelatedNodes = selectedEdge || selectedActivity || compareMode
    ? []
    : selected ? getRelatedNodes(selected, data.graphNodes, data.graphEdges) : [];
  const inspectorMode = compareMode ? "Compare" : selectedActivity ? selectedActivity.laneTitle : selectedEdge ? "Edge" : "Node";
  const inspectorLinkCount = selectedActivity
    ? activityRelatedIds.length
    : selectedEdge
      ? edgeRelatedIds.length
      : compareMode
        ? 2
        : selectedRelatedNodes.length;
  const inspectorPayload = compareMode
    ? { kind: "compare", pinned: pinnedNode, compare: compareNode }
    : selectedActivity
      ? { kind: "activity", lane: selectedActivity.laneTitle, id: selectedActivity.id, item: selectedActivity.item, relatedNodeIds: selectedActivity.relatedNodeIds }
      : selectedEdge
        ? { kind: "edge", edge: selectedEdge, source: selectedEdgeSource || selectedEdge.source, target: selectedEdgeTarget || selectedEdge.target }
        : selected
          ? { kind: "node", node: selected, detail: selectedEntity || null }
          : { kind: "empty", detail: null };

  async function copyInspectorPayload() {
    const text = JSON.stringify(inspectorPayload, null, 2);
    try {
      const clipboard = typeof window === "undefined" ? undefined : window.navigator.clipboard;
      if (!clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await clipboard.writeText(text);
    } catch (err) {
      setLastResult({
        copied: false,
        reason: err instanceof Error ? err.message : String(err),
        payload: inspectorPayload
      });
    }
    setCopiedInspector(true);
    window.setTimeout(() => setCopiedInspector(false), 1400);
  }

  const viewCommandLabels: Record<ViewMode, string> = {
    graph: "图谱总览",
    chat: "Scene 对话",
    world: "World 面板",
    review: "Operator Review",
    metrics: "Metrics"
  };
  const commandItems: CommandItem[] = [
    ...(hasActiveFilters ? [{
      id: "action-clear-filters",
      group: "Actions",
      label: "Clear filters",
      meta: "scope",
      keywords: "Clear filters reset scope 清除 过滤 scope",
      run: clearFilters
    }] : []),
    ...(selected ? [{
      id: `focus-${selected.id}`,
      group: "Actions",
      label: `Focus ${selected.label}`,
      meta: "lens",
      keywords: `Focus ${selected.label} ${selected.id} 聚焦 邻域 focus lens`,
      run: focusSelectedNode
    }] : []),
    ...navItems.map((item) => ({
      id: `view-${item.id}`,
      group: "Views",
      label: viewCommandLabels[item.id],
      meta: "view",
      keywords: `${item.label} ${viewCommandLabels[item.id]} ${item.id}`,
      run: () => {
        setView(item.id);
      }
    })),
    ...data.graphNodes.map((node) => ({
      id: `node-${node.id}`,
      group: "Nodes",
      label: node.label,
      meta: node.type,
      keywords: `${node.label} ${node.id} ${node.type}`,
      run: async () => {
        setView("graph");
        await selectNode(node);
      }
    }))
  ];
  const normalizedCommandQuery = commandQuery.trim().toLowerCase();
  const visibleCommands = commandItems
    .filter((item) => normalizedCommandQuery ? item.keywords.toLowerCase().includes(normalizedCommandQuery) : true)
    .slice(0, 10);

  function activateCommand(item: CommandItem) {
    setCommandOpen(false);
    setCommandQuery("");
    void item.run();
  }

  return (
    <main className="app-shell">
      <aside className="sidebar glass-panel" aria-label="主导航">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            <BrainCircuit size={22} />
          </div>
          <div>
            <p className="eyebrow">we-together</p>
            <h1>本地图谱工作台</h1>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-button ${view === item.id ? "is-active" : ""}`}
                onClick={() => setView(item.id)}
                type="button"
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-actions">
          <button className="tool-button" type="button" onClick={openCommandPalette}>
            <Command size={16} />
            命令
          </button>
          <button className="tool-button" type="button" onClick={() => void loadData()}>
            <RefreshCw size={16} />
            刷新
          </button>
          <button
            className="tool-button"
            type="button"
            onClick={() => {
              sessionStorage.removeItem("we_together_webui_token");
              setToken("");
              setTokenDraft("");
              setClient(null);
              setData(emptyWorkspaceData);
            }}
          >
            <Lock size={16} />
            锁定
          </button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="page-title">
            <p className="eyebrow">Phase 73 Console</p>
            <h2>{view === "graph" ? "图谱总览" : view === "chat" ? "Scene 对话" : view === "world" ? "World 面板" : view === "review" ? "Operator Review" : "Metrics"}</h2>
            <SummaryStrip summary={summary} />
          </div>
          <div className="topbar-controls">
            <button className="command-button" type="button" aria-keyshortcuts="Control+K Meta+K" onClick={openCommandPalette}>
              <Command size={15} />
              命令
              <kbd>Ctrl K</kbd>
            </button>
            <div className="theme-toggle" aria-label="主题">
              <button className={theme === "glass" ? "is-active" : ""} type="button" onClick={() => setTheme("glass")}>
                <GlassWater size={15} />
                Liquid Glass
              </button>
              <button className={theme === "flat" ? "is-active" : ""} type="button" onClick={() => setTheme("flat")}>
                <SunMedium size={15} />
                Flat
              </button>
            </div>
            <form className="token-form" onSubmit={handleTokenSubmit}>
              <label>
                <span>Remote API token</span>
                <input
                  value={tokenDraft}
                  onChange={(event) => setTokenDraft(event.target.value)}
                  placeholder={token ? "远程 API 已连接" : "可选高级模式"}
                  type="password"
                  autoComplete="new-password"
                />
              </label>
              <button type="submit">
                <ShieldCheck size={15} />
                连接
              </button>
            </form>
          </div>
        </header>

        <section className="control-ribbon glass-panel" aria-label="过滤器">
          <label>
            <span>Scene</span>
            <select value={sceneId} onChange={(event) => setSceneId(event.target.value)}>
              <option value="">全部</option>
              {data.scenes.map((scene) => (
                <option key={scene.scene_id} value={scene.scene_id}>
                  {scene.scene_summary || scene.scene_id}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Type</span>
            <select value={nodeType} onChange={(event) => setNodeType(event.target.value as "all" | NodeType)}>
              <option value="all">全部</option>
              <option value="person">人物</option>
              <option value="memory">记忆</option>
              <option value="group">群组</option>
              <option value="scene">场景</option>
              <option value="state">状态</option>
              <option value="relation">关系</option>
              <option value="object">物件</option>
              <option value="place">地点</option>
              <option value="project">项目</option>
            </select>
          </label>
          <label className="search-field">
            <span>搜索</span>
            <Search size={16} aria-hidden="true" />
            <input
              ref={searchInputRef}
              aria-label="搜索"
              aria-keyshortcuts="/"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="node / id / type"
            />
          </label>
          <div className="status-pill">
            <CircleDot size={14} />
            {channelLabel}
          </div>
        </section>

        <FilterStatusBar
          filteredCount={filteredNodes.length}
          totalCount={data.graphNodes.length}
          chips={filterChips}
          hasActiveFilters={hasActiveFilters}
          onClear={clearFilters}
        />

        {!client ? <div className="permission-line">Local skill bridge 默认通道：{localChannelDetail}；Remote API token 仅用于高级部署模式。</div> : null}
        {!client && localRuntimeLoaded && data.scenes.length === 0 ? (
          <div className="permission-line">Local runtime 暂无 scenes；请先运行 bootstrap + seed-demo，或导入材料创建 scene。</div>
        ) : null}
        {!client ? (
          <LocalRuntimeActions
            result={runtimeActionResult}
            onBootstrap={() => void runLocalRuntimeAction("bootstrap")}
            onSeedDemo={() => void runLocalRuntimeAction("seed-demo")}
          />
        ) : null}
        {error ? <div className="error-line">{error}</div> : null}
        {loading ? (
          <div className="loading-line">
            <span className="loading-bar" />
            正在读取图谱...
          </div>
        ) : null}

        {view === "graph" ? (
          <GraphWorkspace
            layout={layout}
            selectedId={selected?.id}
            selectedLabel={selected?.label}
            onSelect={(node) => void selectNode(node)}
            selectedEdgeId={selectedEdge?.id}
            highlightedNodeIds={highlightedNodeIds}
            highlightedEdgeIds={highlightedEdgeIds}
            focusActive={Boolean(focusNodeId)}
            fitSignal={fitSignal}
            onFocusSelected={focusSelectedNode}
            onHoverNode={setHoveredNodeId}
            onSelectEdge={selectEdge}
            events={data.events}
            patches={data.patches}
            snapshots={data.snapshots}
            onSelectActivity={selectActivity}
            selectedActivityId={selectedActivity?.id}
          />
        ) : null}
        {view === "chat" ? (
          <ChatPanel
            scenes={data.scenes}
            output={chatOutput}
            packageJson={retrievalPackage}
            value={chatInput}
            narrationValue={narrationInput}
            onChange={setChatInput}
            onNarrationChange={setNarrationInput}
            onSubmit={runTurn}
            onImportNarration={() => void importNarration()}
          />
        ) : null}
        {view === "world" ? <WorldPanel world={data.world} /> : null}
        {view === "review" ? <ReviewPanel branches={data.branches} onResolve={(branch, candidate, note) => void resolveBranch(branch, candidate, note)} /> : null}
        {view === "metrics" ? <MetricsPanel summary={summary} events={data.events} patches={data.patches} apiMode={metricsApiMode} /> : null}
      </section>

      {commandOpen ? (
        <CommandPalette
          inputRef={commandInputRef}
          query={commandQuery}
          items={visibleCommands}
          onQueryChange={setCommandQuery}
          onActivate={activateCommand}
          onClose={() => setCommandOpen(false)}
        />
      ) : null}

      <InspectorPanel
        open={inspectorOpen}
        selected={selected}
        selectedEdge={selectedEdge}
        selectedActivity={selectedActivity}
        compareMode={compareMode}
        pinnedNode={pinnedNode}
        compareNode={compareNode}
        copiedInspector={copiedInspector}
        recentItems={recentItems}
        allNodes={data.graphNodes}
        inspectorRows={inspectorRows}
        inspectorMode={inspectorMode}
        inspectorLinkCount={inspectorLinkCount}
        selectedRelatedNodes={selectedRelatedNodes}
        isEditing={isEditing}
        editValue={editValue}
        lastResult={lastResult}
        typeMeta={typeMeta}
        onOpenChange={setInspectorOpen}
        onCopyPayload={copyInspectorPayload}
        onFocusCurrent={focusSelectedNode}
        onPinCurrent={() => selected && setPinnedNode(selected)}
        onCompareCurrent={() => pinnedNode && selected && setCompareNode(selected)}
        onExitCompare={() => setCompareNode(null)}
        onReturnToCurrent={() => selected && selectNode(selected)}
        onSelectNode={selectNode}
        onEdit={() => setIsEditing(true)}
        onSave={saveEntity}
        onCancelEdit={() => setIsEditing(false)}
        onEditValueChange={setEditValue}
      />
    </main>
  );
}

function SummaryStrip({ summary }: { summary: Record<string, SummaryValue> }) {
  const items: Array<[string, number]> = [
    ["People", Number(summary.person_count || 0)],
    ["Relations", Number(summary.relation_count || 0)],
    ["Memories", Number(summary.memory_count || 0)],
    ["Branches", Number(summary.open_local_branch_count || 0)]
  ];
  return (
    <section className="summary-strip" aria-label="图谱摘要">
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function FilterStatusBar({
  filteredCount,
  totalCount,
  chips,
  hasActiveFilters,
  onClear
}: {
  filteredCount: number;
  totalCount: number;
  chips: FilterChip[];
  hasActiveFilters: boolean;
  onClear: () => void;
}) {
  return (
    <section className="filter-status" aria-label="过滤状态">
      <div className="filter-count">
        <strong>{filteredCount} / {totalCount} nodes</strong>
        <span>{hasActiveFilters ? "Filtered scope" : "Full scope"}</span>
      </div>
      <div className="filter-chip-row">
        {chips.length ? (
          chips.map((chip) => (
            <span className="filter-chip" key={`${chip.label}-${chip.value}`}>
              {chip.label} {chip.value}
            </span>
          ))
        ) : (
          <span className="filter-chip is-muted">All scenes · all types</span>
        )}
      </div>
      <button className="filter-reset" type="button" disabled={!hasActiveFilters} onClick={onClear}>
        <X size={13} />
        清除过滤
      </button>
    </section>
  );
}

function LocalRuntimeActions({
  result,
  onBootstrap,
  onSeedDemo
}: {
  result: Record<string, unknown> | null;
  onBootstrap: () => void;
  onSeedDemo: () => void;
}) {
  return (
    <section className="local-action-strip glass-panel" aria-label="本地运行时动作">
      <div>
        <span>Local runtime</span>
        <strong>当前 CLI 通道</strong>
        <small>初始化和 demo seed 会写入本地 tenant SQLite；provider token 仍由 CLI 环境持有。</small>
      </div>
      <div className="local-action-buttons">
        <button type="button" onClick={onBootstrap}>
          <ShieldCheck size={15} />
          Bootstrap
        </button>
        <button type="button" onClick={onSeedDemo}>
          <Sparkles size={15} />
          Seed demo
        </button>
      </div>
      {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}

function GraphWorkspace({
  layout,
  selectedId,
  selectedLabel,
  onSelect,
  selectedEdgeId,
  highlightedNodeIds,
  highlightedEdgeIds,
  focusActive,
  fitSignal,
  onFocusSelected,
  onHoverNode,
  onSelectEdge,
  events,
  patches,
  snapshots,
  onSelectActivity,
  selectedActivityId
}: {
  layout: ReturnType<typeof buildLayout>;
  selectedId?: string;
  selectedLabel?: string;
  onSelect: (node: GraphNode) => void;
  selectedEdgeId?: string;
  highlightedNodeIds: Set<string>;
  highlightedEdgeIds: Set<string>;
  focusActive: boolean;
  fitSignal: number;
  onFocusSelected: () => void;
  onHoverNode: (nodeId: string | null) => void;
  onSelectEdge: (edge: PositionedEdge) => void;
  events: Array<Record<string, unknown>>;
  patches: Array<Record<string, unknown>>;
  snapshots: Array<Record<string, unknown>>;
  onSelectActivity: (activity: ActivitySelection) => void;
  selectedActivityId?: string;
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const zoomLabel = `${Math.round(zoom * 100)}%`;

  function fitView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  useEffect(() => {
    if (fitSignal > 0) fitView();
  }, [fitSignal]);

  function startPan(event: ReactPointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("button")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragStart({ x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y });
  }

  function movePan(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragStart) return;
    setPan({
      x: dragStart.panX + event.clientX - dragStart.x,
      y: dragStart.panY + event.clientY - dragStart.y
    });
  }

  return (
    <section className="graph-workspace">
      <div
        className="graph-canvas glass-panel"
        role="region"
        aria-label="图谱画布"
        onPointerDown={startPan}
        onPointerMove={movePan}
        onPointerUp={() => setDragStart(null)}
        onPointerCancel={() => setDragStart(null)}
      >
        <div className="canvas-toolbar">
          <span>Graph</span>
          <strong>{layout.positionedNodes.length} nodes</strong>
          <strong>{layout.positionedEdges.length} links</strong>
          <strong>{zoomLabel}</strong>
          <button
            className={`focus-lens-button ${focusActive ? "is-active" : ""}`}
            type="button"
            aria-pressed={focusActive}
            aria-label={`聚焦邻域${selectedLabel ? ` ${selectedLabel}` : ""}`}
            onClick={onFocusSelected}
          >
            <Maximize2 size={13} />
            聚焦邻域
          </button>
          <div className="canvas-controls" aria-label="图谱视图控制">
            <button type="button" aria-label="缩小图谱" onClick={() => setZoom((value) => Math.max(0.75, value - 0.25))}>
              <Minus size={13} />
            </button>
            <button type="button" aria-label="放大图谱" onClick={() => setZoom((value) => Math.min(1.75, value + 0.25))}>
              <Plus size={13} />
            </button>
            <button type="button" aria-label="适合视图" onClick={fitView}>
              <Maximize2 size={13} />
            </button>
          </div>
        </div>
        {layout.positionedNodes.length === 0 ? (
          <div className="empty-state">
            <strong>没有匹配节点</strong>
            <span>调整 Scene、Type 或搜索条件后继续查看图谱。</span>
          </div>
        ) : null}
        <div
          className="canvas-content"
          style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
        >
          <svg className="edge-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {layout.positionedEdges.map((edge) => {
              const source = edge.sourcePosition!;
              const target = edge.targetPosition!;
              const midX = (source.x + target.x) / 2;
              const midY = (source.y + target.y) / 2 - 10;
              return (
                <g key={edge.id}>
                  <path
                    d={`M ${source.x} ${source.y} Q ${midX} ${midY} ${target.x} ${target.y}`}
                    className={`${edge.type === "relation" ? "edge relation-edge" : "edge"} ${highlightedEdgeIds.has(edge.id) ? "is-highlighted" : ""}`}
                  />
                  {edge.label ? (
                    <text x={midX} y={midY} className="edge-label">
                      {compactId(edge.label)}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </svg>
          <div className="canvas-grid" aria-hidden="true" />
          {layout.positionedEdges.map((edge) => {
            const source = edge.sourcePosition!;
            const target = edge.targetPosition!;
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2 - 10;
            return (
              <button
                aria-label={`关系 ${edge.id} ${edge.label || ""}`}
                className={`edge-hitbox ${selectedEdgeId === edge.id ? "is-selected" : ""} ${highlightedEdgeIds.has(edge.id) ? "is-highlighted" : ""}`}
                key={`button-${edge.id}`}
                onClick={() => onSelectEdge(edge)}
                style={{ left: `${midX}%`, top: `${midY}%` }}
                type="button"
              >
                <span>{compactId(edge.label || edge.id)}</span>
              </button>
            );
          })}
          {layout.positionedNodes.map((node) => (
            <button
              aria-label={node.label}
              className={`graph-node node-${node.type} ${node.id === selectedId ? "is-selected" : ""} ${highlightedNodeIds.has(node.id) ? "is-related" : ""}`}
              key={node.id}
              onClick={() => onSelect(node)}
              onMouseEnter={() => onHoverNode(node.id)}
              onMouseLeave={() => onHoverNode(null)}
              style={{
                left: `${node.position.x}%`,
                top: `${node.position.y}%`,
                "--node-color": typeMeta[node.type].color,
                "--node-glow": typeMeta[node.type].glow
              } as CSSProperties}
              type="button"
            >
              <span>{node.label}</span>
              <small>{typeMeta[node.type].label}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="node-strip" aria-label="图谱节点">
        {layout.positionedNodes.length === 0 ? (
          <div className="strip-empty">没有节点可显示</div>
        ) : null}
        {layout.positionedNodes.map((node) => (
          <button
            aria-label={`节点索引 ${node.type} ${node.label}`}
            className={`${node.id === selectedId ? "is-selected" : ""} ${highlightedNodeIds.has(node.id) ? "is-related" : ""}`}
            key={node.id}
            onClick={() => onSelect(node)}
            type="button"
          >
            <span style={{ color: typeMeta[node.type].color }}>{node.type}</span>
            <strong>{node.label}</strong>
            <small>{compactId(node.id)}</small>
          </button>
        ))}
      </div>

      <ActivityDock
        events={events}
        patches={patches}
        snapshots={snapshots}
        nodes={layout.positionedNodes}
        onSelectActivity={onSelectActivity}
        selectedActivityId={selectedActivityId}
      />
    </section>
  );
}

function ActivityDock({
  events,
  patches,
  snapshots,
  nodes,
  onSelectActivity,
  selectedActivityId
}: {
  events: Array<Record<string, unknown>>;
  patches: Array<Record<string, unknown>>;
  snapshots: Array<Record<string, unknown>>;
  nodes: GraphNode[];
  onSelectActivity: (activity: ActivitySelection) => void;
  selectedActivityId?: string;
}) {
  const [activeLane, setActiveLane] = useState<ActivityLaneFilter>("all");
  const lanes = [
    { key: "events" as const, title: "Events", items: events, idKey: "event_id", tone: "cyan" },
    { key: "patches" as const, title: "Patches", items: patches, idKey: "patch_id", tone: "amber" },
    { key: "snapshots" as const, title: "Snapshots", items: snapshots, idKey: "snapshot_id", tone: "green" }
  ];
  const visibleLanes = activeLane === "all" ? lanes : lanes.filter((lane) => lane.key === activeLane);
  const totalRecords = events.length + patches.length + snapshots.length;
  const tabs: Array<{ key: ActivityLaneFilter; label: string; shortLabel: string }> = [
    { key: "all", label: "All", shortLabel: "All" },
    { key: "events", label: "Events", shortLabel: "Event" },
    { key: "patches", label: "Patches", shortLabel: "Patch" },
    { key: "snapshots", label: "Snapshots", shortLabel: "Snap" }
  ];

  return (
    <section className="activity-dock glass-panel" aria-label="运行记录">
      <header className="activity-dock-head">
        <div>
          <span>Activity</span>
          <strong>{totalRecords} records</strong>
        </div>
        <div className="lane-tabs" aria-label="运行记录 Lane">
          {tabs.map((tab) => (
            <button
              aria-label={tab.label}
              aria-pressed={activeLane === tab.key}
              className={activeLane === tab.key ? "is-active" : ""}
              key={tab.key}
              type="button"
              onClick={() => setActiveLane(tab.key)}
            >
              {tab.shortLabel}
            </button>
          ))}
        </div>
      </header>
      <div className={`activity-lanes ${activeLane !== "all" ? "is-focused" : ""}`}>
        {visibleLanes.map((lane) => (
          <section className={`activity-lane tone-${lane.tone}`} key={lane.title} aria-label={lane.title}>
            <header>
              <h3>{lane.title}</h3>
              <span>{lane.items.length} records</span>
            </header>
            <div className="activity-list">
              {lane.items.slice(0, 4).map((item, index) => (
                <button
                  className={`activity-item ${selectedActivityId === getActivityRecordId(item, lane.idKey, index) ? "is-selected" : ""}`}
                  key={`${lane.title}-${index}`}
                  type="button"
                  onClick={() => {
                    const id = getActivityRecordId(item, lane.idKey, index);
                    onSelectActivity({
                      laneTitle: lane.title,
                      id,
                      item,
                      relatedNodeIds: inferRelatedNodeIds(item, nodes)
                    });
                  }}
                >
                  <strong>{compactId(getActivityRecordId(item, lane.idKey, index))}</strong>
                  <span>{getActivitySummary(item)}</span>
                </button>
              ))}
              {lane.items.length === 0 ? <p className="activity-empty">No records</p> : null}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

function ChatPanel({
  scenes,
  output,
  packageJson,
  value,
  narrationValue,
  onChange,
  onNarrationChange,
  onSubmit,
  onImportNarration
}: {
  scenes: Scene[];
  output: string;
  packageJson: Record<string, unknown> | null;
  value: string;
  narrationValue: string;
  onChange: (value: string) => void;
  onNarrationChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onImportNarration: () => void;
}) {
  return (
    <section className="panel-page">
      <form className="composer glass-panel" onSubmit={onSubmit}>
        <label>
          <span>Scene-grounded input</span>
          <textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder="对当前 scene 说一句话..." />
        </label>
        <button type="submit">
          <Send size={16} />
          运行 turn
        </button>
      </form>
      <section className="narration-import glass-panel">
        <label>
          <span>Narration import</span>
          <textarea value={narrationValue} onChange={(event) => onNarrationChange(event.target.value)} placeholder="导入一段口述材料，生成事件、人物、关系、记忆和 snapshot。" />
        </label>
        <button type="button" disabled={!narrationValue.trim()} onClick={onImportNarration}>
          <Plus size={16} />
          导入 narration
        </button>
      </section>
      <div className="split-panel">
        <section className="glass-panel">
          <h3>Response</h3>
          <pre className="response-box">{output}</pre>
        </section>
        <section className="glass-panel">
          <h3>Scenes</h3>
          {scenes.map((scene) => (
            <p className="list-row" key={scene.scene_id}>
              <strong>{scene.scene_summary || scene.scene_id}</strong>
              <span>{scene.participant_count || 0} participants</span>
            </p>
          ))}
        </section>
      </div>
      <section className="glass-panel">
        <h3>retrieval_package</h3>
        <pre className="json-box">{packageJson ? JSON.stringify(packageJson, null, 2) : "等待 chat turn 返回检索包。"}</pre>
      </section>
    </section>
  );
}

function WorldPanel({ world }: { world: WorkspaceData["world"] }) {
  const groups = [
    { title: "Objects", items: world.objects, key: "object_id" },
    { title: "Places", items: world.places, key: "place_id" },
    { title: "Projects", items: world.projects, key: "project_id" },
    { title: "Agent drives", items: world.agent_drives, key: "drive_id" },
    { title: "Autonomous actions", items: world.autonomous_actions, key: "action_id" }
  ];
  return (
    <section className="world-grid">
      {groups.map((group) => (
        <section className="glass-panel" key={group.title}>
          <h3>{group.title}</h3>
          {group.items.map((item, index) => (
            <p className="list-row" key={String(item[group.key] || index)}>
              <strong>{asText(item.name || item.drive_type || item.action_type || item[group.key])}</strong>
              <span>{asText(item.status || item.kind || item.scope || item.priority || item.intensity || item.person_id)}</span>
            </p>
          ))}
        </section>
      ))}
    </section>
  );
}

function MetricsPanel({
  summary,
  events,
  patches,
  apiMode
}: {
  summary: Record<string, SummaryValue>;
  events: Array<Record<string, unknown>>;
  patches: Array<Record<string, unknown>>;
  apiMode: string;
}) {
  const people = Number(summary.person_count || 0);
  const relations = Number(summary.relation_count || 0);
  const memories = Number(summary.memory_count || 0);
  const branches = Number(summary.open_local_branch_count || 0);
  const rows = [
    { label: "Graph load", value: people + relations + memories, max: 28, status: `${people} people · ${relations} relations · ${memories} memories` },
    { label: "Event flow", value: events.length, max: 8, status: "recent event stream" },
    { label: "Branch pressure", value: branches, max: 4, status: branches ? "operator gate active" : "clear" },
    { label: "Patch health", value: patches.length, max: 8, status: "applied patch lane" }
  ];
  return (
    <section className="telemetry-panel glass-panel" aria-label="运行遥测">
      <header>
        <div>
          <p className="eyebrow">Runtime telemetry</p>
          <h3>运行遥测</h3>
        </div>
        <span className="status-pill">
          <CircleDot size={14} />
          {apiMode}
        </span>
      </header>
      <div className="telemetry-list">
        {rows.map((row) => (
          <div className="telemetry-row" key={row.label}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
            <div className="telemetry-bar" aria-hidden="true">
              <i style={{ width: `${Math.min(100, Math.round((row.value / row.max) * 100))}%` }} />
            </div>
            <small>{row.status}</small>
          </div>
        ))}
      </div>
      <div className="health-list">
        <span>
          <ShieldCheck size={15} />
          Local runtime
        </span>
        <span>
          <GitBranch size={15} />
          Event-first writes
        </span>
        <span>
          <MoonStar size={15} />
          Snapshot-aware
        </span>
      </div>
    </section>
  );
}

export default App;
