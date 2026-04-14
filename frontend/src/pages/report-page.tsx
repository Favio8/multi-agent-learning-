import { useQuery } from "@tanstack/react-query";

import { useAppState } from "@/app/app-state";
import { ReportCharts } from "@/components/charts/report-charts";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getAllProgress, getReport } from "@/lib/api";

function clampPercentage(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function ReportPage() {
  const { userId } = useAppState();
  const reportQuery = useQuery({
    queryKey: ["report", userId],
    queryFn: () => getReport(userId),
  });
  const progressQuery = useQuery({
    queryKey: ["progress", userId],
    queryFn: () => getAllProgress(userId),
  });

  const report = reportQuery.data;
  const progress = progressQuery.data?.progress ?? [];
  const accuracy = clampPercentage((report?.accuracy ?? 0) * 100);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Report"
        title="学习表现报告"
        description="先看整体表现，再看每份文档的推进情况和错误分布。"
        badge={`${report?.total_reviews ?? 0} reviews`}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="总答题数" value={report?.total_reviews ?? 0} />
        <MetricCard label="正确数量" value={report?.correct_count ?? 0} />
        <MetricCard label="正确率" value={`${accuracy}%`} />
        <MetricCard label="平均耗时" value={`${((report?.avg_latency_ms ?? 0) / 1000).toFixed(1)}s`} />
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="history">历史</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {report ? <ReportCharts report={report} progress={progress} /> : null}
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="space-y-3 p-6">
              {progress.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-border/80 bg-white/60 p-6 text-sm text-muted-foreground">
                  还没有学习历史。等你开始学习后，这里会展示每份文档的持久化进度。
                </div>
              ) : null}

              {progress.map((item) => {
                const totalCards = Math.max(0, item.total_cards);
                const currentCard = Math.min(Math.max(0, item.current_card_idx), totalCards);
                const completion = totalCards > 0 ? clampPercentage((currentCard / totalCards) * 100) : 0;

                return (
                  <div
                    key={item.doc_id}
                    className="rounded-[24px] border border-white/75 bg-white/70 px-4 py-4"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-base font-semibold tracking-[-0.02em]">
                          {item.doc_title ?? item.doc_id}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {(item.doc_type?.toUpperCase() ?? "TEXT")} · {currentCard}/{totalCards} · {completion}%
                        </p>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        最后学习 {new Date(item.last_updated).toLocaleString()}
                      </p>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="space-y-2 p-6">
        <p className="eyebrow">{label}</p>
        <p className="text-4xl font-semibold tracking-[-0.04em]">{value}</p>
      </CardContent>
    </Card>
  );
}
