import type { ComponentType } from "react";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Flame } from "lucide-react";

import { useAppState } from "@/app/app-state";
import { PageHeader } from "@/components/layout/page-header";
import { StudySession } from "@/components/study/study-session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getReviewPlan } from "@/lib/api";

export function ReviewPage() {
  const { userId } = useAppState();
  const [isSessionOpen, setIsSessionOpen] = useState(false);
  const reviewQuery = useQuery({
    queryKey: ["reviewPlan", userId],
    queryFn: () => getReviewPlan(userId),
  });

  const reviewPlan = reviewQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="复习"
        title="今日复习"
        description="复习页不再只是列表，而是一条真正可执行的会话流。先看到今天的任务量，再决定是否立即进入复习。"
        badge={`${reviewPlan?.due_today ?? 0} 张待复习`}
      />

      {!isSessionOpen ? (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <ReviewMetric label="今日到期" value={reviewPlan?.due_today ?? 0} icon={CalendarClock} />
            <ReviewMetric label="已经逾期" value={reviewPlan?.overdue ?? 0} icon={Flame} accent />
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div className="space-y-2">
                <Badge>今日队列</Badge>
                <CardTitle className="text-2xl">待复习卡片</CardTitle>
              </div>
              <Button
                onClick={() => setIsSessionOpen(true)}
                disabled={!reviewPlan || reviewPlan.cards.length === 0}
              >
                开始复习
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {!reviewPlan || reviewPlan.cards.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-border/80 bg-white/60 p-6 text-sm text-muted-foreground">
                  今天没有待复习卡片，系统会在你下一次答题后更新新的调度计划。
                </div>
              ) : null}

              {reviewPlan?.cards.slice(0, 10).map((card) => (
                <div key={card.card_id} className="rounded-[24px] border border-white/75 bg-white/70 px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="primary">{card.type.toUpperCase()}</Badge>
                    <Badge>{card.difficulty}</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-foreground">{card.stem}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      ) : (
        <StudySession
          sessionId={`review-${userId}`}
          title="今日复习会话"
          subtitle="提交答案后会直接触发评测与下一次 SM-2 调度。"
          userId={userId}
          cards={reviewPlan?.cards ?? []}
          completionMessage="今天的待复习卡片已经处理完。回到明天时，这里会是新的节奏。"
        />
      )}
    </div>
  );
}

function ReviewMetric({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
  accent?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-6">
        <div className="space-y-2">
          <p className="eyebrow">{label}</p>
          <p className="text-4xl font-semibold tracking-[-0.04em]">{value}</p>
        </div>
        <div className={`flex h-14 w-14 items-center justify-center rounded-[22px] ${accent ? "bg-danger/10 text-danger" : "bg-primary/10 text-primary"}`}>
          <Icon className="h-6 w-6" />
        </div>
      </CardContent>
    </Card>
  );
}
