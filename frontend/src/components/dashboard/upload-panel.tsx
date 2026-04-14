import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileText,
  FileUp,
  Layers3,
  LoaderCircle,
  Orbit,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useAppState } from "@/app/app-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { buildDocument, ingestDocument } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  BuildDifficulty,
  BuildRequest,
  BuildStrategy,
  BuildSummary,
  CardType,
  Difficulty,
} from "@/types/api";

type UploadPhase = "idle" | "uploading" | "building" | "done";

const CARD_TYPE_ORDER: CardType[] = ["knowledge", "cloze", "mcq", "short"];
const QUICK_COUNTS = [8, 12, 20, 30];

const defaultBuildOptions: BuildRequest = {
  enable_kg: true,
  enable_consistency_check: true,
  target_card_count: 12,
  build_strategy: "balanced",
  card_types: [...CARD_TYPE_ORDER],
  difficulty: "mixed",
};

const buildStrategyOptions: Array<{
  value: BuildStrategy;
  label: string;
  description: string;
}> = [
  { value: "balanced", label: "均衡构建", description: "题型更均衡，适合大多数资料。" },
  { value: "memory", label: "记忆优先", description: "更偏重知识卡与填空题，适合先打基础。" },
  { value: "challenge", label: "挑战训练", description: "更偏重选择题与简答题，适合检验理解。" },
];

const difficultyOptions: Array<{
  value: BuildDifficulty;
  label: string;
  description: string;
}> = [
  { value: "mixed", label: "混合", description: "自动混合不同难度，节奏更自然。" },
  { value: "L", label: "偏基础", description: "优先保留更容易回忆的卡片。" },
  { value: "M", label: "偏标准", description: "保持中等难度，适合日常训练。" },
  { value: "H", label: "偏进阶", description: "优先保留更有挑战性的卡片。" },
];

const cardTypeOptions: Array<{
  value: CardType;
  label: string;
  description: string;
}> = [
  { value: "knowledge", label: "知识卡", description: "适合快速建立核心概念。" },
  { value: "cloze", label: "填空卡", description: "适合强化关键词回忆。" },
  { value: "mcq", label: "选择题", description: "适合理解辨析与排除训练。" },
  { value: "short", label: "简答题", description: "适合检查表达与迁移能力。" },
];

const typeLabelMap: Record<CardType, string> = {
  knowledge: "知识卡",
  cloze: "填空卡",
  mcq: "选择题",
  short: "简答题",
};

const difficultyLabelMap: Record<BuildDifficulty, string> = {
  mixed: "混合难度",
  L: "偏基础",
  M: "偏标准",
  H: "偏进阶",
};

function clampCardCount(value: number) {
  if (!Number.isFinite(value)) {
    return defaultBuildOptions.target_card_count;
  }
  return Math.min(60, Math.max(4, Math.round(value)));
}

function getStrategyLabel(value: BuildStrategy) {
  return buildStrategyOptions.find((item) => item.value === value)?.label ?? value;
}

export function UploadPanel() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveDocId } = useAppState();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [summary, setSummary] = useState<BuildSummary | null>(null);
  const [buildOptions, setBuildOptions] = useState<BuildRequest>(defaultBuildOptions);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const isBusy = phase === "uploading" || phase === "building";

  useEffect(() => {
    if (!isSettingsOpen) {
      return;
    }

    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousBodyPaddingRight = document.body.style.paddingRight;

    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    return () => {
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.body.style.overflow = previousBodyOverflow;
      document.body.style.paddingRight = previousBodyPaddingRight;
    };
  }, [isSettingsOpen]);

  useEffect(() => {
    if (!isSettingsOpen || isBusy) {
      return;
    }

    function handleKeydown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsSettingsOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [isBusy, isSettingsOpen]);

  function resetBuildState() {
    setSummary(null);
    setPhase((current) => (current === "done" ? "idle" : current));
  }

  function updateBuildOptions(patch: Partial<BuildRequest>) {
    if (isBusy) {
      return;
    }

    resetBuildState();
    setBuildOptions((current) => ({ ...current, ...patch }));
  }

  function toggleCardType(cardType: CardType) {
    if (isBusy) {
      return;
    }

    resetBuildState();
    setBuildOptions((current) => {
      const nextTypes = current.card_types.includes(cardType)
        ? current.card_types.filter((item) => item !== cardType)
        : [...current.card_types, cardType].sort(
            (left, right) => CARD_TYPE_ORDER.indexOf(left) - CARD_TYPE_ORDER.indexOf(right),
          );

      return {
        ...current,
        card_types: nextTypes,
      };
    });
  }

  function openSettings() {
    if (isBusy) {
      return;
    }

    if (!selectedFile) {
      toast.error("请先选择可解析文件，如 PDF、TXT、Markdown、Office 或结构化文本文件。");
      return;
    }

    setIsSettingsOpen(true);
  }

  function closeSettings() {
    if (isBusy) {
      return;
    }

    setIsSettingsOpen(false);
  }

  async function handleConfirmBuild() {
    if (!selectedFile) {
      toast.error("请先选择可解析文件，如 PDF、TXT、Markdown、Office 或结构化文本文件。");
      return;
    }

    if (buildOptions.card_types.length === 0) {
      toast.error("至少选择一种卡片类型。");
      return;
    }

    try {
      setPhase("uploading");
      const ingestResult = await ingestDocument(selectedFile);

      setPhase("building");
      const buildResult = await buildDocument(ingestResult.doc_id, buildOptions);
      setSummary(buildResult.summary);
      setActiveDocId(buildResult.doc_id);
      setPhase("done");
      setIsSettingsOpen(false);

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["documents"] }),
        queryClient.invalidateQueries({ queryKey: ["progress"] }),
        queryClient.invalidateQueries({ queryKey: ["reviewPlan"] }),
        queryClient.invalidateQueries({ queryKey: ["cards", buildResult.doc_id] }),
      ]);

      toast.success("构建完成，可以直接开始学习了。");
    } catch (error) {
      const message = error instanceof Error ? error.message : "构建失败";
      toast.error(message);
      setPhase("idle");
    }
  }

  const phases = [
    { key: "uploading", label: "上传资料", description: "保存原始文件并创建文档记录。" },
    { key: "building", label: "开始构建", description: "解析内容、抽取概念并生成学习卡片。" },
    { key: "done", label: "构建完成", description: "卡片已经可用，可以进入学习页面。" },
  ] as const;

  return (
    <>
      <Card className="overflow-hidden">
        <CardHeader className="space-y-4">
          <Badge variant="primary" className="w-fit">
            文档构建
          </Badge>
          <div className="space-y-2">
            <CardTitle className="text-2xl">上传资料并生成学习卡片</CardTitle>
            <CardDescription className="max-w-2xl leading-7">
              点击“开始构建”后再设置卡片数量、题型、策略和难度，让首页保持干净，也让操作更聚焦。
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <label
            className={cn(
              "flex flex-col gap-4 rounded-[28px] border border-dashed border-border/80 bg-white/65 p-6 transition-colors",
              isBusy ? "cursor-not-allowed opacity-75" : "cursor-pointer hover:bg-white/80",
            )}
          >
            <div className="flex items-center gap-3 text-sm font-medium text-foreground">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <FileUp className="h-5 w-5" />
              </div>
              选择 PDF / Markdown / Office / 文本文件
            </div>
            <input
              className="hidden"
              type="file"
              accept=".pdf,.txt,.html,.htm,.md,.markdown,.csv,.json,.xml,.docx,.pptx,.xlsx,.xls"
              disabled={isBusy}
              onChange={(event) => {
                resetBuildState();
                setIsSettingsOpen(false);
                setSelectedFile(event.target.files?.[0] ?? null);
              }}
            />
            <div className="space-y-1">
              <p className="text-base font-medium">
                {selectedFile ? selectedFile.name : "拖拽到这里，或点击选择文件"}
              </p>
              <p className="text-sm text-muted-foreground">
                {selectedFile
                  ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`
                  : "推荐上传结构清晰的教材、文章、课堂笔记或整理后的文档。"}
              </p>
            </div>
          </label>

          <div className="rounded-[28px] border border-white/70 bg-white/72 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-base font-semibold">构建预设</p>
                <p className="text-sm text-muted-foreground">
                  点击开始构建后，会弹出设置窗口，你可以在里面完成本次构建参数的确认。
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SelectionTag>{buildOptions.target_card_count} 张</SelectionTag>
                <SelectionTag>{getStrategyLabel(buildOptions.build_strategy)}</SelectionTag>
                <SelectionTag>{difficultyLabelMap[buildOptions.difficulty]}</SelectionTag>
                <SelectionTag>{buildOptions.card_types.length} 种题型</SelectionTag>
              </div>
            </div>
          </div>

          <div className="grid gap-3">
            {phases.map((item) => {
              const isActive = phase === item.key;
              const isComplete = phase === "done" || (phase === "building" && item.key === "uploading");

              return (
                <div
                  key={item.key}
                  className="flex items-start gap-4 rounded-[22px] border border-white/70 bg-white/65 px-4 py-4"
                >
                  <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-full bg-background">
                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    ) : isActive ? (
                      <LoaderCircle className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                      <Orbit className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-foreground">{item.label}</p>
                    <p className="text-sm leading-6 text-muted-foreground">{item.description}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {summary ? (
            <div className="space-y-4 rounded-[28px] border border-white/70 bg-white/72 p-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <Metric label="分段数" value={summary.total_sections} />
                <Metric label="概念数" value={summary.total_concepts} />
                <Metric label="卡片数" value={summary.total_cards} />
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <SummaryBlock title="本次设置">
                  <SummaryRow label="目标数量" value={`${summary.build_options.target_card_count} 张`} />
                  <SummaryRow label="构建策略" value={getStrategyLabel(summary.build_options.build_strategy)} />
                  <SummaryRow label="难度倾向" value={difficultyLabelMap[summary.build_options.difficulty]} />
                </SummaryBlock>

                <SummaryBlock title="实际题型分布">
                  {CARD_TYPE_ORDER.map((cardType) => (
                    <SummaryRow key={cardType} label={typeLabelMap[cardType]} value={summary.by_type[cardType]} />
                  ))}
                </SummaryBlock>

                <SummaryBlock title="实际难度分布">
                  {(["L", "M", "H"] as Difficulty[]).map((difficulty) => (
                    <SummaryRow
                      key={difficulty}
                      label={difficultyLabelMap[difficulty]}
                      value={summary.by_difficulty[difficulty]}
                    />
                  ))}
                </SummaryBlock>
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button size="lg" onClick={openSettings} disabled={isBusy}>
              {isBusy ? "构建中..." : "开始构建"}
            </Button>
            {summary ? (
              <Button size="lg" variant="secondary" onClick={() => navigate("/study")}>
                打开学习界面
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <SettingsDialog
        buildOptions={buildOptions}
        isBusy={isBusy}
        isOpen={isSettingsOpen}
        selectedFile={selectedFile}
        onClose={closeSettings}
        onConfirm={handleConfirmBuild}
        onUpdateOptions={updateBuildOptions}
        onToggleCardType={toggleCardType}
      />
    </>
  );
}

function SettingsDialog({
  buildOptions,
  isBusy,
  isOpen,
  selectedFile,
  onClose,
  onConfirm,
  onUpdateOptions,
  onToggleCardType,
}: {
  buildOptions: BuildRequest;
  isBusy: boolean;
  isOpen: boolean;
  selectedFile: File | null;
  onClose: () => void;
  onConfirm: () => void;
  onUpdateOptions: (patch: Partial<BuildRequest>) => void;
  onToggleCardType: (cardType: CardType) => void;
}) {
  if (!isOpen || typeof document === "undefined") {
    return null;
  }

  const overlayStyle: CSSProperties = {
    position: "fixed",
    inset: 0,
    zIndex: 1000,
    background: "rgba(15, 23, 42, 0.45)",
    backdropFilter: "blur(8px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "16px",
  };

  const panelStyle: CSSProperties = {
    width: "min(960px, calc(100vw - 32px))",
    maxHeight: "min(840px, calc(100vh - 32px))",
    background: "#ffffff",
    borderRadius: "30px",
    border: "1px solid rgba(226, 232, 240, 0.95)",
    boxShadow: "0 40px 120px rgba(15, 23, 42, 0.18)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  };

  return createPortal(
    <div style={overlayStyle} onClick={onClose}>
      <div style={panelStyle} onClick={(event) => event.stopPropagation()}>
        <div className="shrink-0 border-b border-slate-200/70 bg-white px-5 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="primary">构建设置</Badge>
                <Badge variant="default">开始前确认</Badge>
              </div>
              <div>
                <p className="text-2xl font-semibold tracking-[-0.04em] text-slate-950">设置这次卡片构建方式</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  先定规模，再定训练方向和卡片范围，最后确认开始构建。
                </p>
              </div>
            </div>

            <button
              type="button"
              aria-label="关闭"
              disabled={isBusy}
              onClick={onClose}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-500 transition hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[linear-gradient(180deg,#fbfcff_0%,#f4f7fb_100%)] overscroll-contain">
          <div className="space-y-6 p-5 sm:p-6">
            <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
              <div className="overflow-hidden rounded-[28px] bg-[linear-gradient(180deg,#0f172a_0%,#1e293b_100%)] p-5 text-white shadow-[0_24px_60px_rgba(15,23,42,0.22)]">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-white/55">Build Preview</p>
                    <p className="mt-4 text-5xl font-semibold tracking-[-0.06em]">
                      {buildOptions.target_card_count}
                    </p>
                    <p className="mt-1 text-sm text-white/70">目标卡片数量</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-3 text-white/82">
                    <Sparkles className="h-5 w-5" />
                  </div>
                </div>
                <div className="mt-6 flex flex-wrap gap-2">
                  <PreviewPill>{getStrategyLabel(buildOptions.build_strategy)}</PreviewPill>
                  <PreviewPill>{difficultyLabelMap[buildOptions.difficulty]}</PreviewPill>
                  <PreviewPill>{buildOptions.card_types.length} 种题型</PreviewPill>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <InfoCard icon={<FileText className="h-5 w-5" />} title="当前文件" content={selectedFile?.name ?? "未选择文件"} />
                <InfoCard icon={<ShieldCheck className="h-5 w-5" />} title="质量保护" content="知识图谱与一致性检查已开启" />
                <InfoCard icon={<Layers3 className="h-5 w-5" />} title="难度倾向" content={difficultyLabelMap[buildOptions.difficulty]} />
                <InfoCard icon={<Sparkles className="h-5 w-5" />} title="构建策略" content={getStrategyLabel(buildOptions.build_strategy)} />
              </div>
            </div>

            <SectionBlock
              title="卡片数量"
              description="先定好这次构建的规模。数量更少会更聚焦，数量更大则适合一次性整理资料。"
            >
              <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
                <Input
                  type="number"
                  min={4}
                  max={60}
                  disabled={isBusy}
                  value={buildOptions.target_card_count}
                  onChange={(event) =>
                    onUpdateOptions({
                      target_card_count: clampCardCount(Number(event.target.value)),
                    })
                  }
                />
                <div className="flex flex-wrap gap-2">
                  {QUICK_COUNTS.map((count) => (
                    <QuickCountButton
                      key={count}
                      active={buildOptions.target_card_count === count}
                      disabled={isBusy}
                      onClick={() => onUpdateOptions({ target_card_count: count })}
                    >
                      {count} 张
                    </QuickCountButton>
                  ))}
                </div>
              </div>
            </SectionBlock>

            <SectionBlock title="构建策略" description="改变卡片类型的整体配比方向。">
              <div className="grid gap-3 md:grid-cols-3">
                {buildStrategyOptions.map((option) => (
                  <OptionCard
                    key={option.value}
                    active={buildOptions.build_strategy === option.value}
                    disabled={isBusy}
                    label={option.label}
                    description={option.description}
                    onClick={() => onUpdateOptions({ build_strategy: option.value })}
                  />
                ))}
              </div>
            </SectionBlock>

            <SectionBlock title="难度倾向" description="决定最终保留的卡片更偏基础、标准还是进阶。">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {difficultyOptions.map((option) => (
                  <OptionCard
                    key={option.value}
                    active={buildOptions.difficulty === option.value}
                    disabled={isBusy}
                    label={option.label}
                    description={option.description}
                    onClick={() => onUpdateOptions({ difficulty: option.value })}
                  />
                ))}
              </div>
            </SectionBlock>

            <SectionBlock title="卡片类型" description="至少保留一种类型，支持多选。">
              <div className="mb-4 flex flex-wrap gap-2">
                {buildOptions.card_types.map((cardType) => (
                  <SelectionTag key={cardType}>{typeLabelMap[cardType]}</SelectionTag>
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {cardTypeOptions.map((option) => (
                  <OptionCard
                    key={option.value}
                    active={buildOptions.card_types.includes(option.value)}
                    disabled={isBusy}
                    label={option.label}
                    description={option.description}
                    onClick={() => onToggleCardType(option.value)}
                  />
                ))}
              </div>
            </SectionBlock>
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200/70 bg-white px-5 py-4 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">确认后开始构建</p>
              <p className="text-sm text-muted-foreground">
                当前将生成 {buildOptions.target_card_count} 张卡片，覆盖 {buildOptions.card_types.length} 种题型。
              </p>
            </div>
            <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
              <Button variant="secondary" onClick={onClose} disabled={isBusy}>
                取消
              </Button>
              <Button onClick={onConfirm} disabled={isBusy} className="sm:min-w-[168px]">
                {isBusy ? "构建中..." : "确认并开始构建"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function SectionBlock({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4 rounded-[28px] border border-white/85 bg-white/78 p-4 shadow-[0_10px_30px_rgba(15,23,42,0.04)] sm:p-5">
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {children}
    </section>
  );
}

function OptionCard({
  active,
  disabled,
  label,
  description,
  onClick,
}: {
  active: boolean;
  disabled?: boolean;
  label: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-[24px] border px-4 py-4 text-left transition-all disabled:cursor-not-allowed disabled:opacity-55",
        active
          ? "border-primary/25 bg-[linear-gradient(180deg,rgba(0,113,227,0.11)_0%,rgba(255,255,255,0.92)_100%)] shadow-[0_14px_30px_rgba(0,113,227,0.10)]"
          : "border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.94)_0%,rgba(248,250,252,0.90)_100%)] hover:border-primary/15 hover:bg-white",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        <div
          className={cn(
            "mt-0.5 h-3 w-3 rounded-full transition-colors",
            active ? "bg-primary shadow-[0_0_0_4px_rgba(0,113,227,0.12)]" : "bg-slate-200",
          )}
        />
      </div>
    </button>
  );
}

function QuickCountButton({
  active,
  disabled,
  children,
  onClick,
}: {
  active: boolean;
  disabled?: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-full border px-4 py-2 text-sm transition-all disabled:cursor-not-allowed disabled:opacity-55",
        active
          ? "border-primary/25 bg-primary/10 text-primary"
          : "border-white/85 bg-white/90 text-muted-foreground hover:bg-white",
      )}
    >
      {children}
    </button>
  );
}

function InfoCard({
  icon,
  title,
  content,
}: {
  icon: ReactNode;
  title: string;
  content: ReactNode;
}) {
  return (
    <div className="rounded-[24px] border border-white/85 bg-white/78 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="mt-1 break-words text-sm leading-6 text-muted-foreground">{content}</p>
        </div>
      </div>
    </div>
  );
}

function SelectionTag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-white/85 bg-white/88 px-3 py-1 text-xs font-medium text-foreground">
      {children}
    </span>
  );
}

function PreviewPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-medium text-white/85 backdrop-blur-sm">
      {children}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-2 rounded-[22px] bg-background/65 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="text-3xl font-semibold tracking-[-0.04em]">{value}</p>
    </div>
  );
}

function SummaryBlock({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-3 rounded-[22px] bg-background/65 p-4">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between rounded-2xl bg-white/70 px-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}
