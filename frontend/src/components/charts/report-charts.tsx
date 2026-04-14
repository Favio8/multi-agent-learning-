import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LearningProgress, Report } from "@/types/api";

const colors = ["#0071E3", "#5AC8FA", "#34C759", "#FF9F0A", "#FF453A"];

function clampPercentage(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function formatErrorLabel(label: string) {
  const normalized = label.trim().toLowerCase();
  const labelMap: Record<string, string> = {
    concept_confusion: "概念混淆",
    fact_error: "事实错误",
    omission: "信息遗漏",
    incomplete: "回答不完整",
    format_error: "格式错误",
    careless: "粗心错误",
    timeout: "超时",
  };

  return labelMap[normalized] ?? label.replace(/_/g, " ");
}

export function ReportCharts({
  report,
  progress,
}: {
  report: Report;
  progress: LearningProgress[];
}) {
  const errorData = Object.entries(report.error_distribution ?? {}).map(([key, value]) => ({
    name: formatErrorLabel(key),
    value,
  }));

  const progressData = progress.map((item) => {
    const totalCards = Math.max(0, item.total_cards);
    const currentCard = Math.min(Math.max(0, item.current_card_idx), totalCards);

    return {
      name: item.doc_title ?? item.doc_id.slice(0, 8),
      completion: totalCards > 0 ? clampPercentage((currentCard / totalCards) * 100) : 0,
    };
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
      <Card>
        <CardHeader>
          <CardTitle>文档完成度</CardTitle>
        </CardHeader>
        <CardContent className="h-[320px]">
          {progressData.length === 0 ? (
            <EmptyChart description="还没有可展示的学习进度。" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={progressData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} unit="%" domain={[0, 100]} />
                <Tooltip cursor={{ fill: "rgba(0, 113, 227, 0.06)" }} />
                <Bar dataKey="completion" radius={[14, 14, 0, 0]}>
                  {progressData.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>错误分布</CardTitle>
        </CardHeader>
        <CardContent className="h-[320px]">
          {errorData.length === 0 ? (
            <EmptyChart description="目前还没有错误类型数据。" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={errorData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} />
                <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} width={120} />
                <Tooltip cursor={{ fill: "rgba(0, 113, 227, 0.06)" }} />
                <Bar dataKey="value" radius={[0, 14, 14, 0]} fill="#0071E3" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function EmptyChart({ description }: { description: string }) {
  return (
    <div className="flex h-full items-center justify-center rounded-[24px] border border-dashed border-border/80 bg-white/50 px-6 text-center text-sm text-muted-foreground">
      {description}
    </div>
  );
}
