import { ChevronRight, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

export type BranchCandidate = {
  candidate_id: string;
  label?: string;
  confidence?: number;
  payload_json?: Record<string, unknown>;
};

export type Branch = {
  branch_id: string;
  reason?: string;
  candidates: BranchCandidate[];
};

type ReviewRisk = "low" | "medium" | "high";

type CandidateImpact = {
  label: string;
  value: string;
};

type ReviewPanelProps = {
  branches: Branch[];
  onResolve: (branch: Branch, candidate: BranchCandidate, note: string) => void;
};

type ReviewBranchProps = {
  branch: Branch;
  selectedCandidate?: BranchCandidate;
  note: string;
  onNoteChange: (value: string) => void;
  onSelectCandidate: (candidate: BranchCandidate) => void;
  onResolve: (branch: Branch, candidate: BranchCandidate, note: string) => void;
};

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function getCandidateRisk(candidate?: BranchCandidate): ReviewRisk {
  if (!candidate) return "low";
  const intent = `${candidate.candidate_id} ${candidate.label || ""}`.toLowerCase();
  if (intent.includes("unmerge") || intent.includes("拆分")) return "high";
  if ((candidate.confidence || 0) >= 0.6) return "medium";
  return "low";
}

function getCandidateImpacts(candidate?: BranchCandidate): CandidateImpact[] {
  if (!candidate) return [];
  const effectPatches = candidate.payload_json?.effect_patches;
  const patches = Array.isArray(effectPatches)
    ? effectPatches.filter((patch): patch is Record<string, unknown> => Boolean(patch) && typeof patch === "object")
    : [];
  if (patches.length) {
    const firstOperation = asText(patches[0].operation || patches[0].type || "effect_patch");
    return [
      { label: "Patch count", value: `${patches.length} ${patches.length === 1 ? "patch" : "patches"}` },
      { label: "Operation", value: firstOperation },
      { label: "Target", value: asText(patches[0].target_id || patches[0].target_type || "-") }
    ];
  }
  const isUnmerge = `${candidate.candidate_id} ${candidate.label || ""}`.toLowerCase().includes("unmerge");
  return [
    { label: "Patch count", value: isUnmerge ? "1 patch" : "0 patches" },
    { label: "Operation", value: isUnmerge ? "unmerge_person" : "keep_merged" },
    { label: "Target", value: "operator branch" }
  ];
}

export function ReviewPanel({ branches, onResolve }: ReviewPanelProps) {
  const [selectedCandidates, setSelectedCandidates] = useState<Record<string, string>>({});
  const [operatorNote, setOperatorNote] = useState("");
  const totalCandidates = branches.reduce((count, branch) => count + branch.candidates.length, 0);

  function getSelectedCandidate(branch: Branch): BranchCandidate | undefined {
    const selectedId = selectedCandidates[branch.branch_id];
    return branch.candidates.find((candidate) => candidate.candidate_id === selectedId)
      || [...branch.candidates].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))[0];
  }

  return (
    <section className="review-queue" aria-label="复核队列">
      <header className="queue-head glass-panel">
        <div>
          <p className="eyebrow">Operator queue</p>
          <h3>复核队列</h3>
        </div>
        <div className="queue-stats">
          <span aria-label={`${branches.length} open branches`}>
            <strong>{branches.length}</strong>
            Open branches
          </span>
          <span aria-label={`${totalCandidates} candidates`}>
            <strong>{totalCandidates}</strong>
            Candidates
          </span>
        </div>
      </header>
      {!branches.length ? (
        <section className="review-empty glass-panel" aria-label="空复核队列">
          <span className="type-dot" style={{ "--node-color": "var(--green)" } as CSSProperties}>clear</span>
          <h3>当前没有待处理 local branch</h3>
          <p>Operator gate 只会在身份融合、unmerge 或其他高风险候选出现时进入队列。</p>
          <small>0 open branches · 0 candidates</small>
        </section>
      ) : null}
      {branches.map((branch) => (
        <ReviewBranch
          branch={branch}
          key={branch.branch_id}
          note={operatorNote}
          selectedCandidate={getSelectedCandidate(branch)}
          onNoteChange={setOperatorNote}
          onResolve={onResolve}
          onSelectCandidate={(candidate) => {
            setSelectedCandidates((current) => ({
              ...current,
              [branch.branch_id]: candidate.candidate_id
            }));
          }}
        />
      ))}
    </section>
  );
}

function ReviewBranch({
  branch,
  selectedCandidate,
  note,
  onNoteChange,
  onSelectCandidate,
  onResolve
}: ReviewBranchProps) {
  const [pendingCandidateId, setPendingCandidateId] = useState<string | null>(null);
  const risk = getCandidateRisk(selectedCandidate);
  const impacts = getCandidateImpacts(selectedCandidate);
  const riskMeta: Record<ReviewRisk, { label: string; detail: string }> = {
    low: { label: "Low risk", detail: "No graph mutation previewed" },
    medium: { label: "Medium risk", detail: "Review note recommended" },
    high: { label: "High risk", detail: "Operator gated · reversible branch" }
  };
  const isConfirming = Boolean(selectedCandidate && pendingCandidateId === selectedCandidate.candidate_id);

  useEffect(() => {
    setPendingCandidateId(null);
  }, [selectedCandidate?.candidate_id]);

  return (
    <article className="review-branch glass-panel">
      <div className="branch-copy">
        <span className="type-dot" style={{ "--node-color": "var(--amber)" } as CSSProperties}>branch</span>
        <h3>{branch.branch_id}</h3>
        <p>{branch.reason || "无 reason"}</p>
      </div>
      <div className="candidate-list">
        {branch.candidates.map((candidate) => {
          const isSelected = candidate.candidate_id === selectedCandidate?.candidate_id;
          return (
            <button
              className={isSelected ? "is-selected" : ""}
              key={candidate.candidate_id}
              type="button"
              onClick={() => onSelectCandidate(candidate)}
            >
              <span>{candidate.label || candidate.candidate_id}</span>
              <strong>{Math.round((candidate.confidence || 0) * 100)}%</strong>
              <ChevronRight size={16} />
            </button>
          );
        })}
      </div>
      <div className="review-decision">
        <section className={`risk-summary risk-${risk}`} aria-label="复核风险">
          <span>复核风险</span>
          <strong>{riskMeta[risk].label}</strong>
          <small>{riskMeta[risk].detail}</small>
        </section>
        <section className="candidate-impact" aria-label="候选影响">
          <span>候选影响</span>
          <div>
            {impacts.map((impact) => (
              <p key={`${impact.label}-${impact.value}`}>
                <small>{impact.label}</small>
                <strong>{impact.value}</strong>
              </p>
            ))}
          </div>
        </section>
        <label>
          <span>复核说明</span>
          <textarea
            value={note}
            onChange={(event) => onNoteChange(event.target.value)}
            placeholder="记录人工判断依据"
          />
        </label>
        <section className="decision-preview" aria-label="决策预览">
          <span>决策预览</span>
          <strong>{selectedCandidate?.candidate_id || "-"}</strong>
          <p>{selectedCandidate?.label || "选择一个候选后应用。"}</p>
          <small>{note || "等待复核说明"}</small>
        </section>
        <button
          className={isConfirming ? "is-confirming" : ""}
          type="button"
          disabled={!selectedCandidate}
          onClick={() => {
            if (!selectedCandidate) return;
            if (isConfirming) {
              setPendingCandidateId(null);
              onResolve(branch, selectedCandidate, note);
              return;
            }
            setPendingCandidateId(selectedCandidate.candidate_id);
            window.scrollTo({ top: 0, left: 0 });
          }}
        >
          <ShieldCheck size={15} />
          {isConfirming ? "确认应用" : "应用候选"}
        </button>
        {isConfirming ? <p className="confirm-hint">再次确认后才会调用 branch resolve。</p> : null}
      </div>
    </article>
  );
}
