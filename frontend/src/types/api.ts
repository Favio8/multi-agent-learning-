export type CardType = "knowledge" | "cloze" | "mcq" | "short";
export type Difficulty = "L" | "M" | "H";
export type BuildStrategy = "balanced" | "memory" | "challenge";
export type BuildDifficulty = "mixed" | Difficulty;

export interface BuildRequest {
  enable_kg: boolean;
  enable_consistency_check: boolean;
  target_card_count: number;
  build_strategy: BuildStrategy;
  card_types: CardType[];
  difficulty: BuildDifficulty;
}

export interface DocumentSummary {
  doc_id: string;
  title: string;
  source: string;
  source_type: string;
  lang: string;
  created_at: string | null;
  updated_at: string | null;
  sections_count: number;
  concepts_count: number;
  cards_count: number;
}

export interface IngestResponse {
  doc_id: string;
  title: string;
  status: string;
  message: string;
}

export interface BuildSummary {
  total_sections: number;
  total_concepts: number;
  total_cards: number;
  timestamp: string;
  by_type: Record<CardType, number>;
  by_difficulty: Record<Difficulty, number>;
  build_options: BuildRequest;
}

export interface BuildResponse {
  doc_id: string;
  status: string;
  summary: BuildSummary;
  message: string;
}

export interface Card {
  card_id: string;
  doc_id: string;
  type: CardType;
  stem: string;
  choices: string[];
  answer: string;
  explanation: string;
  source_ref: string;
  concept_refs: string[];
  difficulty: Difficulty;
  created_at: string | null;
}

export interface CardsResponse {
  total: number;
  cards: Card[];
}

export interface AnswerPayload {
  user_id: string;
  card_id: string;
  response: string;
  latency_ms: number;
}

export interface Evaluation {
  user_id: string;
  card_id: string;
  score: number;
  is_correct: boolean;
  error_type?: string | null;
  difficulty: Difficulty;
  feedback: string;
  latency_ms: number;
  timestamp: string;
}

export interface Schedule {
  card_id: string;
  user_id: string;
  next_due: string;
  interval_days: number;
  ef: number;
  repetitions: number;
}

export interface AnswerResponse {
  status: string;
  evaluation: Evaluation;
  schedule: Schedule;
}

export interface ReviewPlan {
  user_id: string;
  due_today: number;
  overdue: number;
  cards: Card[];
}

export interface Report {
  user_id: string;
  total_reviews: number;
  accuracy?: number;
  correct_count?: number;
  incorrect_count?: number;
  avg_latency_ms?: number;
  error_distribution?: Record<string, number>;
  message?: string;
}

export interface LearningProgress {
  user_id: string;
  doc_id: string;
  current_card_idx: number;
  total_cards: number;
  last_updated: string;
  doc_title?: string;
  doc_type?: string;
}

export interface ProgressCollection {
  total: number;
  progress: LearningProgress[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
}
