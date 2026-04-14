import { ArrowUpRight, BookText, BrainCircuit, Layers3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAppState } from "@/app/app-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { DocumentSummary, LearningProgress } from "@/types/api";

interface RecentDocumentsProps {
  documents: DocumentSummary[];
  progress: LearningProgress[];
}

function clampPercentage(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function RecentDocuments({ documents, progress }: RecentDocumentsProps) {
  const navigate = useNavigate();
  const { activeDocId, setActiveDocId } = useAppState();

  const progressMap = new Map(progress.map((item) => [item.doc_id, item]));

  return (
    <Card>
      <CardHeader className="space-y-3">
        <Badge className="w-fit">文档库</Badge>
        <CardTitle className="text-2xl">最近文档</CardTitle>
        <CardDescription>这里集中展示每份资料的内容规模和学习进度，方便快速回到正在学的那一份。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {documents.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-border/80 bg-white/55 p-6 text-sm text-muted-foreground">
            还没有文档。先上传一份资料，系统会自动生成分段、概念和卡片。
          </div>
        ) : null}

        {documents.map((document) => {
          const itemProgress = progressMap.get(document.doc_id);
          const isActive = activeDocId === document.doc_id;
          const totalCards = Math.max(itemProgress?.total_cards ?? 0, document.cards_count ?? 0);
          const currentCard = Math.min(itemProgress?.current_card_idx ?? 0, totalCards);
          const completion = totalCards > 0 ? clampPercentage((currentCard / totalCards) * 100) : 0;

          return (
            <div
              key={document.doc_id}
              className={cn(
                "rounded-[24px] border px-4 py-4 transition-all",
                isActive ? "border-primary/25 bg-primary/5" : "border-white/70 bg-white/65",
              )}
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1 space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-semibold tracking-[-0.02em]">{document.title}</p>
                    <Badge variant="default">{document.source_type.toUpperCase()}</Badge>
                    {isActive ? <Badge variant="primary">当前文档</Badge> : null}
                  </div>

                  <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Layers3 className="h-4 w-4" />
                      {totalCards} 张卡片
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <BrainCircuit className="h-4 w-4" />
                      {document.concepts_count} 个概念
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <BookText className="h-4 w-4" />
                      {document.sections_count} 个分段
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
                      <span>{totalCards > 0 ? `进度 ${currentCard}/${totalCards}` : "还没有生成卡片"}</span>
                      <span>{completion}%</span>
                    </div>
                    <Progress value={completion} />
                  </div>
                </div>

                <Button
                  variant="secondary"
                  onClick={() => {
                    setActiveDocId(document.doc_id);
                    navigate(`/study?docId=${document.doc_id}`);
                  }}
                >
                  打开
                  <ArrowUpRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
