import type { ComponentType } from "react";

import { useQuery } from "@tanstack/react-query";
import { BookCopy, ChartNoAxesColumn, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAppState } from "@/app/app-state";
import { RecentDocuments } from "@/components/dashboard/recent-documents";
import { UploadPanel } from "@/components/dashboard/upload-panel";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAllProgress, getReport, getReviewPlan, listDocuments } from "@/lib/api";

export function DashboardPage() {
  const navigate = useNavigate();
  const { userId } = useAppState();
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });
  const progressQuery = useQuery({
    queryKey: ["progress", userId],
    queryFn: () => getAllProgress(userId),
  });
  const reviewPlanQuery = useQuery({
    queryKey: ["reviewPlan", userId],
    queryFn: () => getReviewPlan(userId),
  });
  const reportQuery = useQuery({
    queryKey: ["report", userId],
    queryFn: () => getReport(userId),
  });

  const documents = documentsQuery.data ?? [];
  const progress = progressQuery.data?.progress ?? [];
  const reviewPlan = reviewPlanQuery.data;
  const report = reportQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="概览"
        title="今天从哪里开始"
        description="上传新资料，继续上次进度，或者直接进入今天的复习。界面尽量不解释自己，而是把注意力还给学习任务本身。"
      />

      <div className="grid gap-6 xl:grid-cols-[1.35fr,0.65fr]">
        <UploadPanel />

        <div className="grid gap-4">
          <OverviewMetric
            icon={BookCopy}
            label="文档数量"
            value={documents.length}
            detail="所有已上传资料"
          />
          <OverviewMetric
            icon={Sparkles}
            label="今日待复习"
            value={reviewPlan?.due_today ?? 0}
            detail={`${reviewPlan?.overdue ?? 0} 张已逾期`}
            accent="primary"
            action={
              reviewPlan && reviewPlan.due_today > 0
                ? {
                    label: "开始复习",
                    onClick: () => navigate("/review"),
                  }
                : undefined
            }
          />
          <OverviewMetric
            icon={ChartNoAxesColumn}
            label="总体正确率"
            value={report?.accuracy ? `${Math.round(report.accuracy * 100)}%` : "0%"}
            detail={`${report?.total_reviews ?? 0} 次答题记录`}
          />
        </div>
      </div>

      <RecentDocuments documents={documents} progress={progress} />
    </div>
  );
}

function OverviewMetric({
  icon: Icon,
  label,
  value,
  detail,
  accent,
  action,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  detail: string;
  accent?: "primary";
  action?: { label: string; onClick: () => void };
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${accent === "primary" ? "bg-primary/10 text-primary" : "bg-white/80 text-foreground"}`}>
          <Icon className="h-5 w-5" />
        </div>
        <Badge>{label}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <CardTitle className="text-3xl">{value}</CardTitle>
        <p className="text-sm text-muted-foreground">{detail}</p>
        {action ? (
          <button className="text-sm font-medium text-primary" onClick={action.onClick} type="button">
            {action.label}
          </button>
        ) : null}
      </CardContent>
    </Card>
  );
}
