import { useEffect, useRef, useState } from "react";
import { startTransition } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { submitAnswer } from "@/lib/api";
import type { AnswerResponse, Card as LearningCard } from "@/types/api";

interface StudySessionProps {
  sessionId: string;
  title: string;
  subtitle: string;
  userId: string;
  cards: LearningCard[];
  initialIndex?: number;
  completionMessage: string;
  onPersistProgress?: (nextIndex: number, totalCards: number) => Promise<void> | void;
}

export function StudySession({
  sessionId,
  title,
  subtitle,
  userId,
  cards,
  initialIndex = 0,
  completionMessage,
  onPersistProgress,
}: StudySessionProps) {
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [draftAnswer, setDraftAnswer] = useState("");
  const [selectedChoice, setSelectedChoice] = useState("");
  const [feedback, setFeedback] = useState<AnswerResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showKnowledgeAnswer, setShowKnowledgeAnswer] = useState(false);
  const [knowledgeState, setKnowledgeState] = useState<boolean | null>(null);
  const answerStartedAt = useRef(Date.now());

  useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex, sessionId]);

  useEffect(() => {
    setDraftAnswer("");
    setSelectedChoice("");
    setFeedback(null);
    setShowKnowledgeAnswer(false);
    setKnowledgeState(null);
    answerStartedAt.current = Date.now();
  }, [currentIndex, sessionId]);

  const currentCard = cards[currentIndex];
  const progress = cards.length > 0 ? ((currentIndex + 1) / cards.length) * 100 : 0;

  async function goToNext() {
    const nextIndex = currentIndex + 1;

    if (onPersistProgress) {
      await onPersistProgress(nextIndex, cards.length);
    }

    startTransition(() => {
      setCurrentIndex(nextIndex);
    });
  }

  async function handleSubmit() {
    if (!currentCard || currentCard.type === "knowledge") {
      return;
    }

    const responseValue = currentCard.type === "mcq" ? selectedChoice : draftAnswer.trim();
    if (!responseValue) {
      toast.error("先填写答案。");
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await submitAnswer({
        user_id: userId,
        card_id: currentCard.card_id,
        response: responseValue,
        latency_ms: Math.max(0, Date.now() - answerStartedAt.current),
      });

      setFeedback(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["reviewPlan", userId] }),
        queryClient.invalidateQueries({ queryKey: ["report", userId] }),
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交失败";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (cards.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-sm text-muted-foreground">当前会话还没有可学习的卡片。</CardContent>
      </Card>
    );
  }

  if (currentIndex >= cards.length) {
    return (
      <Card>
        <CardHeader className="space-y-3">
          <Badge variant="success" className="w-fit">
            本轮完成
          </Badge>
          <CardTitle className="text-2xl">这轮学习已经完成</CardTitle>
          <CardDescription>{completionMessage}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="secondary" onClick={() => setCurrentIndex(0)}>
            <RotateCcw className="mr-2 h-4 w-4" />
            重新开始
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="primary">{title}</Badge>
            <Badge>{currentCard.type.toUpperCase()}</Badge>
            <Badge>{currentCard.difficulty} 难度</Badge>
          </div>
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-2xl">{currentCard.stem}</CardTitle>
                <CardDescription className="mt-3 max-w-3xl leading-7">{subtitle}</CardDescription>
              </div>
              <div className="rounded-[22px] bg-background/75 px-4 py-3 text-right">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">进度</p>
                <p className="mt-2 text-lg font-semibold tracking-[-0.03em]">
                  {currentIndex + 1}/{cards.length}
                </p>
              </div>
            </div>
            <Progress value={progress} />
          </div>
        </CardHeader>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="space-y-6 p-6 sm:p-8">
          {currentCard.type === "knowledge" ? (
            <div className="space-y-5">
              <div className="rounded-[28px] bg-white/75 p-6">
                <p className="text-lg leading-8 tracking-[-0.02em]">{currentCard.stem}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button variant="secondary" onClick={() => setShowKnowledgeAnswer((value) => !value)}>
                  {showKnowledgeAnswer ? "收起答案" : "查看答案"}
                </Button>
              </div>
              {showKnowledgeAnswer ? (
                <div className="space-y-4 rounded-[28px] border border-primary/15 bg-primary/5 p-6">
                  <p className="text-sm font-medium text-muted-foreground">答案</p>
                  <p className="text-lg leading-8 tracking-[-0.02em]">{currentCard.answer}</p>
                  {currentCard.explanation ? (
                    <p className="text-sm leading-7 text-muted-foreground">{currentCard.explanation}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-3">
                    <Button variant="success" onClick={() => setKnowledgeState(true)}>
                      记住了
                    </Button>
                    <Button variant="secondary" onClick={() => setKnowledgeState(false)}>
                      还需要再看一遍
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="space-y-5">
              {currentCard.type === "mcq" ? (
                <div className="grid gap-3">
                  {currentCard.choices.map((choice) => (
                    <button
                      key={choice}
                      type="button"
                      className={`rounded-[24px] border px-5 py-4 text-left text-sm transition-all ${
                        selectedChoice === choice
                          ? "border-primary/30 bg-primary/10 text-foreground"
                          : "border-white/80 bg-white/70 text-muted-foreground hover:bg-white"
                      }`}
                      onClick={() => setSelectedChoice(choice)}
                    >
                      {choice}
                    </button>
                  ))}
                </div>
              ) : currentCard.type === "short" ? (
                <Textarea
                  value={draftAnswer}
                  onChange={(event) => setDraftAnswer(event.target.value)}
                  placeholder="写下你的答案，保持简洁准确。"
                />
              ) : (
                <Input
                  value={draftAnswer}
                  onChange={(event) => setDraftAnswer(event.target.value)}
                  placeholder="填入你认为正确的关键词。"
                />
              )}

              <div className="flex flex-wrap gap-3">
                <Button onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? "提交中..." : "提交答案"}
                </Button>
                <Button variant="secondary" onClick={goToNext}>
                  跳到下一题
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {feedback ? (
            <div
              className={`rounded-[28px] border p-6 ${
                feedback.evaluation.is_correct
                  ? "border-success/20 bg-success/10"
                  : "border-danger/20 bg-danger/10"
              }`}
            >
              <div className="flex flex-wrap items-center gap-3">
                {feedback.evaluation.is_correct ? (
                  <CheckCircle2 className="h-5 w-5 text-success" />
                ) : (
                  <CircleAlert className="h-5 w-5 text-danger" />
                )}
                <p className="text-sm font-medium">{feedback.evaluation.feedback}</p>
              </div>
              {!feedback.evaluation.is_correct ? (
                <div className="mt-4 space-y-2 text-sm leading-7 text-muted-foreground">
                  <p>
                    <span className="font-medium text-foreground">参考答案:</span> {currentCard.answer}
                  </p>
                  {currentCard.explanation ? <p>{currentCard.explanation}</p> : null}
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  得分 {feedback.evaluation.score.toFixed(2)}
                </span>
                <span className="inline-flex items-center gap-2">
                  <CalendarClock className="h-4 w-4" />
                  下次复习 {new Date(feedback.schedule.next_due).toLocaleString()}
                </span>
              </div>
            </div>
          ) : null}

          {knowledgeState !== null ? (
            <div className="rounded-[28px] border border-primary/15 bg-primary/5 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  {knowledgeState
                    ? "这张卡片会在你的学习流里继续向前推进。"
                    : "可以稍后回到这张知识卡，再做一轮快速回忆。"}
                </p>
                <Button onClick={goToNext}>
                  下一题
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
