import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAppState } from "@/app/app-state";
import { PageHeader } from "@/components/layout/page-header";
import { StudySession } from "@/components/study/study-session";
import { Card, CardContent } from "@/components/ui/card";
import { getAllProgress, getCards, listDocuments, saveProgress } from "@/lib/api";

export function StudyPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { userId, activeDocId, setActiveDocId } = useAppState();

  const progressQuery = useQuery({
    queryKey: ["progress", userId],
    queryFn: () => getAllProgress(userId),
  });

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const progress = progressQuery.data?.progress ?? [];
  const documents = documentsQuery.data ?? [];
  const queryDocId = searchParams.get("docId");
  const resolvedDocId = queryDocId ?? activeDocId ?? progress[0]?.doc_id ?? documents[0]?.doc_id ?? null;

  useEffect(() => {
    if (resolvedDocId && resolvedDocId !== activeDocId) {
      setActiveDocId(resolvedDocId);
    }
  }, [activeDocId, resolvedDocId, setActiveDocId]);

  const cardsQuery = useQuery({
    queryKey: ["cards", resolvedDocId],
    queryFn: () => getCards(resolvedDocId!),
    enabled: Boolean(resolvedDocId),
  });

  const currentDocument = documents.find((item) => item.doc_id === resolvedDocId);
  const currentProgress = progress.find((item) => item.doc_id === resolvedDocId);
  const cards = cardsQuery.data?.cards ?? [];
  const totalCards =
    cardsQuery.data?.total ??
    currentProgress?.total_cards ??
    currentDocument?.cards_count ??
    cards.length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Study"
        title="专注学习模式"
        description="这里保留答题、反馈和进度持久化，把注意力尽量放回到卡片本身。"
        badge={currentDocument?.title}
      />

      {!resolvedDocId ? (
        <Card>
          <CardContent className="p-8 text-sm text-muted-foreground">
            还没有可学习的文档。先回到概览页上传一份资料。
          </CardContent>
        </Card>
      ) : null}

      {resolvedDocId ? (
        <StudySession
          sessionId={resolvedDocId}
          title={currentDocument?.title ?? "学习会话"}
          subtitle={`文档类型 ${currentDocument?.source_type?.toUpperCase() ?? "TEXT"} · ${totalCards} 张卡片`}
          userId={userId}
          cards={cards}
          initialIndex={currentProgress?.current_card_idx ?? 0}
          completionMessage="当前文档的学习队列已经完成。你可以重新开始，或者回到概览页处理下一份资料。"
          onPersistProgress={async (nextIndex, currentTotalCards) => {
            await saveProgress({
              user_id: userId,
              doc_id: resolvedDocId,
              current_card_idx: nextIndex,
              total_cards: currentTotalCards,
            });
          }}
        />
      ) : null}

      {!resolvedDocId ? null : (
        <div className="flex justify-end">
          <button
            className="text-sm font-medium text-primary"
            onClick={() => navigate("/")}
            type="button"
          >
            返回概览
          </button>
        </div>
      )}
    </div>
  );
}
