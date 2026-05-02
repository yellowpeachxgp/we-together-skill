import { Check, Clipboard, GitBranch, History, Maximize2, PanelRight, Pin, Sparkles, X } from "lucide-react";
import type { CSSProperties } from "react";

type InspectorNodeType = "person" | "relation" | "memory" | "group" | "scene" | "state" | "object" | "place" | "project";

type InspectorGraphNode = {
  id: string;
  label: string;
  type: InspectorNodeType;
  scene_id?: string;
  active_in_scene?: boolean;
  data?: Record<string, unknown>;
};

type InspectorGraphEdge = {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
};

type InspectorPositionedEdge = InspectorGraphEdge & {
  sourcePosition?: { x: number; y: number };
  targetPosition?: { x: number; y: number };
};

type InspectorActivitySelection = {
  laneTitle: string;
  id: string;
  item: Record<string, unknown>;
  relatedNodeIds: string[];
};

type InspectorRecentItem = {
  kind: string;
  id: string;
  label: string;
};

type InspectorRelatedNode = {
  node: InspectorGraphNode;
  edge: InspectorGraphEdge;
};

type InspectorTypeMeta = Record<InspectorNodeType, { label: string; color: string; glow: string }>;

type InspectorPanelProps = {
  open: boolean;
  selected?: InspectorGraphNode;
  selectedEdge: InspectorPositionedEdge | null;
  selectedActivity: InspectorActivitySelection | null;
  compareMode: boolean;
  pinnedNode: InspectorGraphNode | null;
  compareNode: InspectorGraphNode | null;
  copiedInspector: boolean;
  recentItems: InspectorRecentItem[];
  allNodes: InspectorGraphNode[];
  inspectorRows: Record<string, unknown>;
  inspectorMode: string;
  inspectorLinkCount: number;
  selectedRelatedNodes: InspectorRelatedNode[];
  isEditing: boolean;
  editValue: string;
  lastResult: Record<string, unknown> | null;
  typeMeta: InspectorTypeMeta;
  onOpenChange: (open: boolean) => void;
  onCopyPayload: () => void | Promise<void>;
  onFocusCurrent: () => void;
  onPinCurrent: () => void;
  onCompareCurrent: () => void;
  onExitCompare: () => void;
  onReturnToCurrent: () => void | Promise<void>;
  onSelectNode: (node: InspectorGraphNode) => void | Promise<void>;
  onEdit: () => void;
  onSave: () => void | Promise<void>;
  onCancelEdit: () => void;
  onEditValueChange: (value: string) => void;
};

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function getActivitySummary(item: Record<string, unknown>): string {
  return asText(item.summary || item.operation || item.status);
}

export function InspectorPanel({
  open,
  selected,
  selectedEdge,
  selectedActivity,
  compareMode,
  pinnedNode,
  compareNode,
  copiedInspector,
  recentItems,
  allNodes,
  inspectorRows,
  inspectorMode,
  inspectorLinkCount,
  selectedRelatedNodes,
  isEditing,
  editValue,
  lastResult,
  typeMeta,
  onOpenChange,
  onCopyPayload,
  onFocusCurrent,
  onPinCurrent,
  onCompareCurrent,
  onExitCompare,
  onReturnToCurrent,
  onSelectNode,
  onEdit,
  onSave,
  onCancelEdit,
  onEditValueChange
}: InspectorPanelProps) {
  const isCompareMode = compareMode && Boolean(pinnedNode && compareNode);
  const comparedNodes = pinnedNode && compareNode ? [pinnedNode, compareNode] : [];
  const hasNodeSelection = Boolean(selected);
  const subjectColor = selectedActivity || selectedEdge
    ? "var(--cyan)"
    : selected
      ? typeMeta[selected.type].color
      : "var(--muted)";
  const subjectLabel = isCompareMode
    ? "Compare"
    : selectedActivity
      ? `Activity ${selectedActivity.laneTitle}`
      : selectedEdge
        ? "Relation edge"
        : selected
          ? typeMeta[selected.type].label
          : "Empty";
  const subjectTitle = isCompareMode
    ? "固定对比"
    : selectedActivity
      ? getActivitySummary(selectedActivity.item)
      : selectedEdge
        ? selectedEdge.label || selectedEdge.id
        : selected
          ? selected.label
          : "没有选中实体";
  const subjectDetail = isCompareMode
    ? `${pinnedNode!.label} -> ${compareNode!.label}`
    : selectedActivity
      ? selectedActivity.id
      : selectedEdge
        ? selectedEdge.id
        : selected
          ? selected.id
          : `${allNodes.length} nodes`;

  return (
    <>
      {!open ? (
        <button className="drawer-open" type="button" onClick={() => onOpenChange(true)}>
          <PanelRight size={16} />
          打开检查器
        </button>
      ) : null}

      <aside className="inspector glass-panel" aria-label="详情检查器" data-open={open ? "true" : "false"}>
        <div className="inspector-head">
          <div>
            <p className="eyebrow">Inspector</p>
            <h2>详情检查器</h2>
          </div>
          <button className="icon-button" type="button" aria-label="收起检查器" onClick={() => onOpenChange(false)}>
            <X size={16} />
          </button>
        </div>
        <div className="inspector-subject">
          <span
            className="type-dot"
            style={{ "--node-color": subjectColor } as CSSProperties}
          >
            {subjectLabel}
          </span>
          <strong>{subjectTitle}</strong>
          <small>{subjectDetail}</small>
        </div>

        <section className="inspector-context" aria-label="检查器上下文">
          <span>
            <small>Mode</small>
            <strong>{inspectorMode}</strong>
          </span>
          <span>
            <small>Links</small>
            <strong>{inspectorLinkCount} links</strong>
          </span>
          <span>
            <small>Recent</small>
            <strong>{recentItems.length} recent</strong>
          </span>
        </section>

        {isCompareMode ? (
          <div className="compare-grid">
            {comparedNodes.map((node) => (
              <section key={node.id}>
                <span className="type-dot" style={{ "--node-color": typeMeta[node.type].color } as CSSProperties}>
                  {typeMeta[node.type].label}
                </span>
                <strong>{node.label}</strong>
                <small>{node.id}</small>
                <p>{asText(node.data?.persona_summary || node.data?.summary || node.data?.status)}</p>
              </section>
            ))}
          </div>
        ) : (
          <dl className="detail-grid">
            <dt>ID</dt>
            <dd>{selectedActivity ? selectedActivity.id : selectedEdge ? selectedEdge.id : selected?.id || "-"}</dd>
            <dt>类型</dt>
            <dd>{selectedActivity ? "activity" : selectedEdge ? selectedEdge.type || "edge" : selected?.type || "empty"}</dd>
            {Object.entries(inspectorRows)
              .filter(([key]) => !["event_id", "patch_id", "snapshot_id", "edge_id"].includes(key))
              .slice(0, 8)
              .map(([key, value]) => (
                <div className="detail-row" key={key}>
                  <dt>{key}</dt>
                  <dd>{asText(value)}</dd>
                </div>
              ))}
          </dl>
        )}

        <div className="inspector-actions">
          <button type="button" onClick={() => void onCopyPayload()}>
            {copiedInspector ? <Check size={15} /> : <Clipboard size={15} />}
            {copiedInspector ? "已复制" : "复制 JSON"}
          </button>
          {!selectedEdge && !selectedActivity && !isCompareMode && hasNodeSelection ? (
            <>
              <button type="button" onClick={onFocusCurrent}>
                <Maximize2 size={15} />
                聚焦当前
              </button>
              <button type="button" onClick={onPinCurrent}>
                <Pin size={15} />
                固定当前
              </button>
              <button type="button" disabled={!pinnedNode} onClick={onCompareCurrent}>
                <GitBranch size={15} />
                对比固定
              </button>
            </>
          ) : null}
          {isCompareMode ? (
            <button type="button" onClick={onExitCompare}>
              <X size={15} />
              退出对比
            </button>
          ) : null}
          {(selectedEdge || selectedActivity) && !isCompareMode ? (
            <button type="button" onClick={() => void onReturnToCurrent()}>
              <PanelRight size={15} />
              回到当前节点
            </button>
          ) : null}
        </div>

        {!selectedEdge && !selectedActivity && !isCompareMode && selected && selectedRelatedNodes.length ? (
          <section className="related-list" aria-label="关联节点">
            <h3>
              <GitBranch size={14} />
              关联节点
            </h3>
            {selectedRelatedNodes.map((related) => (
              <button
                aria-label={`${related.node.label} ${related.edge.type || "edge"}`}
                key={`${selected.id}-${related.node.id}-${related.edge.id}`}
                type="button"
                onClick={() => void onSelectNode(related.node)}
              >
                <span style={{ color: typeMeta[related.node.type].color }}>{typeMeta[related.node.type].label}</span>
                <strong>{related.node.label}</strong>
                <small>{related.edge.label || related.edge.type || related.edge.id}</small>
              </button>
            ))}
          </section>
        ) : null}

        {!selectedEdge && !selectedActivity && !isCompareMode && selected ? (
          isEditing ? (
            <div className="editor">
              <label>
                <span>{selected.type === "person" ? "primary_name" : "summary"}</span>
                <input value={editValue} onChange={(event) => onEditValueChange(event.target.value)} />
              </label>
              <div className="editor-actions">
                <button type="button" onClick={() => void onSave()}>保存</button>
                <button type="button" className="quiet" onClick={onCancelEdit}>取消</button>
              </div>
            </div>
          ) : (
            <button className="primary-action" type="button" onClick={onEdit}>
              <Sparkles size={16} />
              编辑
            </button>
          )
        ) : null}

        <section className="recent-list" aria-label="最近查看">
          <h3>
            <History size={14} />
            最近查看
          </h3>
          {recentItems.map((item) => {
            const recentNode = allNodes.find((node) => node.id === item.id);
            return (
              <button key={item.id} type="button" disabled={!recentNode} onClick={() => recentNode && void onSelectNode(recentNode)}>
                <span>{item.kind}</span>
                <strong>{item.label}</strong>
              </button>
            );
          })}
        </section>
        {lastResult ? <pre className="json-box">{JSON.stringify(lastResult, null, 2)}</pre> : null}
      </aside>
    </>
  );
}
