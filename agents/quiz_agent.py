"""
Quiz card generation with stronger concept grounding and quality checks.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from .base_agent import BaseAgent


class QuizAgent(BaseAgent):
    """Generate knowledge, cloze, MCQ and short-answer cards from concepts."""

    TYPE_PRIORITY = ["knowledge", "cloze", "mcq", "short"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="QuizAgent", config=config)

        config = config or {}
        self.cards_per_concept = max(1, config.get("cards_per_concept", 2))
        self.min_distractor_similarity = config.get("min_distractor_similarity", 0.3)
        self.max_workers = max(1, config.get("max_workers", 3))
        self.section_fallback_limit = config.get("section_fallback_limit", 6)
        self.max_section_cards = config.get("max_section_cards", 6)
        self.target_card_count = max(4, config.get("target_card_count", 12))
        self.build_strategy = config.get("build_strategy", "balanced")
        self.difficulty_mode = config.get("difficulty_mode", "mixed")
        self.use_llm = config.get("use_llm", False)

        configured_types = config.get(
            "card_types", ["knowledge", "cloze", "mcq", "short"]
        )
        self.allowed_card_types = [
            card_type
            for card_type in self.TYPE_PRIORITY
            if card_type in configured_types
        ] or self.TYPE_PRIORITY.copy()
        self.invalid_term_exact = {
            "而不",
            "而不是",
            "不是",
            "如果",
            "因为",
            "所以",
            "例如",
            "比如",
            "以下",
            "作者",
            "某天",
            "写下",
            "问自己",
            "接着问自己",
            "试想一下",
            "他们会说",
            "这句话暴露了一切",
            "这就",
            "这不",
            "最后",
            "记住",
        }
        self.invalid_term_prefixes = (
            "的",
            "而",
            "是",
            "被",
            "把",
            "让",
            "像",
            "从",
            "在",
            "于",
            "对",
            "向",
            "如果",
            "因为",
            "所以",
            "例如",
            "比如",
            "以下",
            "作者",
            "某天",
            "写下",
            "问自己",
            "接着问自己",
            "试想",
            "想象",
            "让它",
            "附加题",
            "针对",
            "他们会说",
            "这句话",
            "这就",
            "这不",
            "现在",
            "今天",
            "我",
            "你",
            "我们",
            "他们",
            "改变你",
            "改变分为",
            "下个星期",
            "大自然就",
            "是因为",
            "像这样",
            "打个响",
            "最后",
            "记住",
        )

        self.llm = None
        if self.use_llm:
            try:
                from nlp.llm_helper import get_llm

                self.llm = get_llm()
                if self.llm.is_available():
                    self.logger.info("LLM enabled for quiz generation")
                else:
                    self.logger.warning("LLM configured but not available")
            except Exception as exc:
                self.logger.warning("Failed to initialize LLM: %s", exc)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quiz cards from concepts and sections."""
        self.validate_input(input_data, ["doc_id"])

        doc_id = input_data["doc_id"]
        concepts = input_data.get("concepts", [])
        sections = input_data.get("sections", [])
        concepts_for_generation = self._select_generation_concepts(concepts)

        self.logger.info(
            "Generating cards for %s selected concepts from %s total concepts and %s sections",
            len(concepts_for_generation),
            len(concepts),
            len(sections),
        )

        if concepts_for_generation:
            if self.llm and self.llm.is_available():
                cards = self._generate_cards_concurrent(
                    concepts_for_generation, sections, doc_id
                )
            else:
                cards = self._generate_cards_rule_based(
                    concepts_for_generation, sections, doc_id
                )
        else:
            cards = []

        minimum_cards = max(4, min(8, len(sections) * 2 if sections else 4))
        if len(cards) < minimum_cards and sections:
            self.logger.info("Adding section fallback cards")
            cards.extend(self._generate_cards_from_sections(sections, doc_id))

        cards = self._quality_check(cards)
        cards = self._apply_build_preferences(cards)

        result = {
            "doc_id": doc_id,
            "cards": cards,
            "metadata": {
                "total_cards": len(cards),
                "by_type": self._count_by_type(cards),
                "by_difficulty": self._count_by_difficulty(cards),
            },
        }

        self.log_audit(
            action="generate_cards",
            input_summary=f"doc_id={doc_id}, {len(concepts)} concepts, {len(sections)} sections",
            output_summary=f"{len(cards)} cards generated",
        )
        return result

    def _select_generation_concepts(
        self, concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Limit generation scope so builds stay responsive on large documents."""
        if not concepts:
            return []

        practice_slots = min(self.cards_per_concept, len(self._get_practice_type_order()))
        cards_per_concept = practice_slots + (1 if "knowledge" in self.allowed_card_types else 0)
        cards_per_concept = max(1, cards_per_concept)

        concept_budget = (self.target_card_count + cards_per_concept - 1) // cards_per_concept
        concept_budget = min(len(concepts), max(2, concept_budget + 4))
        return concepts[:concept_budget]

    def _generate_cards_rule_based(
        self,
        concepts: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate cards without the LLM."""
        section_lookup = self._build_section_lookup(sections)
        cards: List[Dict[str, Any]] = []
        for concept in concepts:
            concept_cards = self._fallback_generate_cards(
                concept, concepts, section_lookup, doc_id
            )
            cards.extend(self._select_card_mix(concept_cards))
        return cards

    def _generate_cards_concurrent(
        self,
        concepts: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate cards per concept with small-batch concurrency."""
        section_lookup = self._build_section_lookup(sections)
        cards: List[Dict[str, Any]] = []
        failed_concepts: List[Dict[str, Any]] = []

        max_workers = min(self.max_workers, max(1, len(concepts)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_concept = {
                executor.submit(
                    self._generate_cards_for_concept,
                    concept,
                    concepts,
                    section_lookup,
                    doc_id,
                ): concept
                for concept in concepts
            }

            for future in concurrent.futures.as_completed(future_to_concept):
                concept = future_to_concept[future]
                try:
                    concept_cards = future.result(timeout=90)
                    if concept_cards:
                        cards.extend(concept_cards)
                    else:
                        failed_concepts.append(concept)
                except Exception as exc:
                    self.logger.warning(
                        "Card generation failed for %s: %s",
                        concept.get("term", "unknown"),
                        exc,
                    )
                    failed_concepts.append(concept)

        if failed_concepts:
            self.logger.info(
                "Falling back to rule-based generation for %s concepts",
                len(failed_concepts),
            )
            for concept in failed_concepts:
                cards.extend(
                    self._select_card_mix(
                        self._fallback_generate_cards(
                            concept, concepts, section_lookup, doc_id
                        )
                    )
                )

        return cards

    def _generate_cards_for_concept(
        self,
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate the final card mix for a single concept."""
        if not self._is_study_worthy_term(concept.get("term", "").strip()):
            return []

        cards: List[Dict[str, Any]] = []

        if self.llm and self.llm.is_available():
            cards = self._generate_cards_batch_llm(
                concept, all_concepts, section_lookup, doc_id
            )

        fallback_cards = self._fallback_generate_cards(
            concept, all_concepts, section_lookup, doc_id
        )

        if not cards:
            cards = fallback_cards
        else:
            existing_types = {card.get("type") for card in cards}
            for fallback_card in fallback_cards:
                if fallback_card.get("type") not in existing_types:
                    cards.append(fallback_card)

        return self._select_card_mix(cards)

    def _generate_cards_batch_llm(
        self,
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate a small, diverse card batch for one concept via LLM."""
        if not self.llm or not self.llm.is_available():
            return []

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition:
            return []

        context = self._get_source_context(concept, section_lookup, limit=320)
        distractors = self._select_distractor_terms(concept, all_concepts, limit=6)
        target_types = [
            card_type
            for card_type in self.allowed_card_types
            if card_type not in {"short", "cloze"}
        ]
        if "short" in self.allowed_card_types and self.cards_per_concept >= 3:
            target_types.append("short")
        if not target_types:
            return []

        system_prompt = (
            "你是资深教研老师，请基于给定概念生成高质量学习卡片。"
            "返回严格 JSON 数组，不要输出任何说明。"
            "每个元素包含字段：type, stem, answer, choices, explanation。"
            "规则：knowledge 用于记忆概念，stem 应是概念名或一句简洁提问，choices 必须为空数组；"
            "cloze 必须包含 ____ 且答案唯一明确；"
            "mcq 必须有 4 个互不重复的选项，answer 必须完全等于 choices 中某一项；"
            "short 是简答题。"
            "不要编造文档中没有的信息，解释要简洁有用。"
        )
        prompt = (
            f"概念：{term}\n"
            f"定义：{definition}\n"
            f"来源片段：{context or '无'}\n"
            f"可用的干扰项候选：{', '.join(distractors) if distractors else '无'}\n"
            f"请生成以下类型的卡片：{', '.join(target_types)}。"
        )

        response = self.llm.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=1200,
        )
        payload = self._parse_json_payload(response)
        if not isinstance(payload, list):
            return []

        cards: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            card = self._standardize_llm_card(
                item, concept, all_concepts, section_lookup, doc_id
            )
            if card:
                cards.append(card)

        return cards

    def _fallback_generate_cards(
        self,
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """Rule-based generation for a single concept."""
        cards: List[Dict[str, Any]] = []

        knowledge = self._generate_knowledge_card(concept, section_lookup, doc_id)
        cloze = self._generate_cloze(concept, section_lookup, doc_id)
        mcq = self._generate_mcq(concept, all_concepts, section_lookup, doc_id)
        short = self._generate_short_answer(concept, section_lookup, doc_id)

        for card in [knowledge, cloze, mcq, short]:
            if card:
                cards.append(card)

        return cards

    def _generate_knowledge_card(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        if "knowledge" not in self.allowed_card_types:
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition or not self._is_study_worthy_term(term):
            return None

        source_ref = self._get_primary_ref(concept)
        context = self._get_source_context(concept, section_lookup, limit=180)

        return {
            "card_id": f"{doc_id}_{concept['cid']}_knowledge",
            "doc_id": doc_id,
            "type": "knowledge",
            "stem": f"什么是“{term}”？",
            "choices": [],
            "answer": definition,
            "explanation": context or f"核心概念：{term}",
            "source_ref": source_ref,
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "knowledge"),
        }

    def _generate_cloze(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        if "cloze" not in self.allowed_card_types:
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition or not self._is_study_worthy_term(term):
            return None

        stem = self._build_cloze_stem(term, concept, section_lookup, definition)
        if not stem:
            return None

        return {
            "card_id": f"{doc_id}_{concept['cid']}_cloze",
            "doc_id": doc_id,
            "type": "cloze",
            "stem": stem,
            "choices": [],
            "answer": term,
            "explanation": definition,
            "source_ref": self._get_primary_ref(concept),
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "cloze"),
        }

    def _generate_mcq(
        self,
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        if "mcq" not in self.allowed_card_types:
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition or not self._is_study_worthy_term(term):
            return None

        distractors = self._select_distractor_terms(concept, all_concepts, limit=3)
        if len(distractors) < 3:
            distractors.extend(
                self._select_distractor_terms_from_context(
                    concept, section_lookup, existing=distractors, limit=3 - len(distractors)
                )
            )

        fallback_terms = ["概念框架", "关键机制", "分析模型", "应用策略"]
        for item in fallback_terms:
            if len(distractors) >= 3:
                break
            if item != term and item not in distractors:
                distractors.append(item)

        choices = self._dedupe_list([term] + distractors)[:4]
        if term not in choices:
            choices = (choices[:3] + [term])[:4]
        if len(choices) < 4:
            return None

        clue = self._shorten_text(definition, 90)
        context = self._get_source_context(concept, section_lookup, limit=150)

        return {
            "card_id": f"{doc_id}_{concept['cid']}_mcq",
            "doc_id": doc_id,
            "type": "mcq",
            "stem": f"根据下面的描述，最符合的概念是哪一项？\n{clue}",
            "choices": self._shuffle_choices(choices, term),
            "answer": term,
            "explanation": context or definition,
            "source_ref": self._get_primary_ref(concept),
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "mcq"),
        }

    def _generate_short_answer(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        if "short" not in self.allowed_card_types:
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        if not term or not definition or not self._is_study_worthy_term(term):
            return None

        context = self._get_source_context(concept, section_lookup, limit=180)
        return {
            "card_id": f"{doc_id}_{concept['cid']}_short",
            "doc_id": doc_id,
            "type": "short",
            "stem": f"请用自己的话解释“{term}”的含义。",
            "choices": [],
            "answer": definition,
            "explanation": context or "回答时尽量覆盖定义中的关键限定词。",
            "source_ref": self._get_primary_ref(concept),
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "short"),
        }

    def _estimate_difficulty(self, concept: Dict[str, Any], card_type: str) -> str:
        """Estimate difficulty from concept length and card type."""
        definition = concept.get("definition", "")
        term = concept.get("term", "")

        score = 0
        if len(definition) > 40:
            score += 1
        if len(definition) > 90:
            score += 1
        if len(term) > 8:
            score += 1
        if card_type in {"short", "mcq"}:
            score += 1

        if score >= 3:
            return "H"
        if score >= 1:
            return "M"
        return "L"

    def _quality_check(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize, validate, dedupe and cap cards."""
        valid_cards: List[Dict[str, Any]] = []
        seen_keys = set()
        seen_type_per_concept = set()
        section_card_count = 0

        for card in cards:
            normalized = self._normalize_card(card)
            if not normalized:
                continue

            key = (
                normalized["type"],
                self._normalize_text(normalized["stem"]),
                self._normalize_text(normalized["answer"]),
            )
            if key in seen_keys:
                continue

            concept_key = normalized.get("concept_refs", [])
            concept_anchor = concept_key[0] if concept_key else normalized.get("source_ref", "")
            type_key = (concept_anchor, normalized["type"])
            if concept_anchor and type_key in seen_type_per_concept:
                continue

            if not normalized.get("concept_refs"):
                if section_card_count >= self.max_section_cards:
                    continue
                section_card_count += 1

            seen_keys.add(key)
            if concept_anchor:
                seen_type_per_concept.add(type_key)
            valid_cards.append(normalized)

        valid_cards.sort(
            key=lambda item: (
                0 if item.get("concept_refs") else 1,
                self.TYPE_PRIORITY.index(item["type"]),
                item["card_id"],
            )
        )
        return valid_cards

    def _normalize_card(self, card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and normalize a single card record."""
        card_type = str(card.get("type", "")).strip().lower()
        if card_type not in self.allowed_card_types:
            return None

        stem = self._clean_text(card.get("stem", ""))
        answer = self._clean_text(card.get("answer", ""))
        explanation = self._clean_text(card.get("explanation", "")) or answer
        source_ref = self._clean_text(card.get("source_ref", ""))
        concept_refs = [
            ref for ref in card.get("concept_refs", []) if isinstance(ref, str) and ref.strip()
        ]
        difficulty = str(card.get("difficulty", "M")).upper()
        if difficulty not in {"L", "M", "H"}:
            difficulty = "M"

        min_stem_length = 2 if card_type == "knowledge" else 6
        if len(stem) < min_stem_length or len(answer) < 2:
            return None

        choices = card.get("choices", [])
        if not isinstance(choices, list):
            choices = []
        choices = [self._clean_text(choice) for choice in choices if self._clean_text(choice)]
        choices = self._dedupe_list(choices)

        if card_type == "knowledge":
            stem = self._normalize_knowledge_stem(stem)
            choices = []
            if self._normalize_text(stem) == self._normalize_text(answer):
                return None
        elif card_type == "cloze":
            choices = []
            if not self._is_study_worthy_term(answer):
                return None
            if "____" not in stem:
                if answer in stem:
                    stem = stem.replace(answer, "____", 1)
                else:
                    return None
            if not self._is_clean_cloze_stem(stem):
                return None
        elif card_type == "mcq":
            if answer not in choices:
                if len(choices) >= 4:
                    choices = choices[:3] + [answer]
                else:
                    choices.append(answer)
            choices = self._dedupe_list(choices)
            if len(choices) != 4 or answer not in choices:
                return None
            if len({self._normalize_text(choice) for choice in choices}) != 4:
                return None
            choices = self._shuffle_choices(choices, answer)

        return {
            "card_id": card.get("card_id") or f"card_{self._normalize_text(stem)[:24]}",
            "doc_id": card.get("doc_id", ""),
            "type": card_type,
            "stem": stem,
            "choices": choices,
            "answer": answer,
            "explanation": explanation,
            "source_ref": source_ref,
            "concept_refs": concept_refs,
            "difficulty": difficulty,
        }

    def _generate_cards_from_sections(
        self, sections: List[Dict[str, Any]], doc_id: str
    ) -> List[Dict[str, Any]]:
        """Fallback cards when concept extraction is sparse."""
        cards: List[Dict[str, Any]] = []
        card_index = 0

        for section in sections[: self.section_fallback_limit]:
            sec_id = section.get("sec_id", "")
            title = self._clean_text(section.get("title", "")) or "本段内容"
            text = self._clean_text(section.get("text", ""))
            if len(text) < 30:
                continue

            informative_sentences = [
                sentence
                for sentence in self._split_sentences(text)
                if 18 <= len(sentence) <= 120
                and any(keyword in sentence for keyword in ["是", "指", "用于", "包括", "通过", "可以"])
            ]
            if not informative_sentences:
                continue

            sentence = informative_sentences[0]
            cloze_target = self._pick_cloze_target(sentence)

            if cloze_target and "cloze" in self.allowed_card_types:
                cards.append(
                    {
                        "card_id": f"{doc_id}_section_{card_index}_cloze",
                        "doc_id": doc_id,
                        "type": "cloze",
                        "stem": sentence.replace(cloze_target, "____", 1),
                        "choices": [],
                        "answer": cloze_target,
                        "explanation": sentence,
                        "source_ref": sec_id,
                        "concept_refs": [],
                        "difficulty": "M",
                    }
                )
                card_index += 1

            if "short" in self.allowed_card_types and len(cards) < self.max_section_cards:
                cards.append(
                    {
                        "card_id": f"{doc_id}_section_{card_index}_short",
                        "doc_id": doc_id,
                        "type": "short",
                        "stem": f"请概括“{title}”这一部分的核心信息。",
                        "choices": [],
                        "answer": self._shorten_text(sentence, 100),
                        "explanation": "回答时覆盖定义、用途或关键关系即可。",
                        "source_ref": sec_id,
                        "concept_refs": [],
                        "difficulty": "M",
                    }
                )
                card_index += 1

            if len(cards) >= self.max_section_cards:
                break

        return cards

    def _standardize_llm_card(
        self,
        card_data: Dict[str, Any],
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        section_lookup: Dict[str, Dict[str, Any]],
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Convert an LLM response object to the internal card schema."""
        card_type = str(card_data.get("type", "")).strip().lower()
        if card_type not in self.allowed_card_types:
            return None

        term = concept.get("term", "").strip()
        definition = concept.get("definition", "").strip()
        source_ref = self._get_primary_ref(concept)

        if card_type == "knowledge":
            stem = self._normalize_knowledge_stem(
                card_data.get("stem") or card_data.get("front") or "",
                fallback_term=term,
            )
            answer = self._clean_text(card_data.get("answer") or card_data.get("back") or definition)
            explanation = self._clean_text(card_data.get("explanation") or card_data.get("hint") or "")
            choices: List[str] = []
        elif card_type == "cloze":
            stem = self._clean_text(card_data.get("stem", ""))
            answer = self._clean_text(card_data.get("answer", "")) or term
            explanation = self._clean_text(card_data.get("explanation", "")) or definition
            if not self._is_study_worthy_term(answer):
                return None
            choices = []
        elif card_type == "mcq":
            stem = self._clean_text(card_data.get("stem", ""))
            answer = self._clean_text(card_data.get("answer", "")) or term
            raw_choices = card_data.get("choices", [])
            if not isinstance(raw_choices, list):
                raw_choices = []
            choices = [self._clean_text(choice) for choice in raw_choices if self._clean_text(choice)]
            if len(choices) < 4:
                filler = self._select_distractor_terms(concept, all_concepts, limit=3)
                choices = self._dedupe_list(choices + [term] + filler)[:4]
            explanation = self._clean_text(card_data.get("explanation", "")) or definition
        else:
            stem = self._clean_text(card_data.get("stem", "")) or f"请解释“{term}”的含义。"
            answer = self._clean_text(card_data.get("answer", "")) or definition
            explanation = self._clean_text(card_data.get("explanation", "")) or self._get_source_context(
                concept, section_lookup, limit=160
            )
            choices = []

        return {
            "card_id": f"{doc_id}_{concept['cid']}_{card_type}_llm",
            "doc_id": doc_id,
            "type": card_type,
            "stem": stem,
            "choices": choices,
            "answer": answer,
            "explanation": explanation,
            "source_ref": source_ref,
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, card_type),
        }

    def _select_card_mix(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep one knowledge card plus a bounded number of practice cards."""
        by_type: Dict[str, Dict[str, Any]] = {}
        for card in cards:
            card_type = card.get("type")
            if card_type in self.allowed_card_types and card_type not in by_type:
                by_type[card_type] = card

        selected: List[Dict[str, Any]] = []
        if "knowledge" in by_type:
            selected.append(by_type["knowledge"])

        practice_budget = self.cards_per_concept
        for card_type in self._get_practice_type_order():
            if card_type in by_type and practice_budget > 0:
                selected.append(by_type[card_type])
                practice_budget -= 1

        return selected

    def _select_distractor_terms(
        self,
        concept: Dict[str, Any],
        all_concepts: List[Dict[str, Any]],
        limit: int = 3,
    ) -> List[str]:
        """Choose concept-aware distractors from other extracted concepts."""
        target_term = concept.get("term", "")
        target_refs = set(concept.get("refs", []))
        candidates = []

        for other in all_concepts:
            other_term = self._clean_text(other.get("term", ""))
            if not other_term or other_term == target_term:
                continue

            score = 0.0
            score -= abs(len(other_term) - len(target_term)) * 0.2
            if other_term[-1:] == target_term[-1:]:
                score += 0.4
            if target_refs & set(other.get("refs", [])):
                score += 0.8
            if other_term[:1] == target_term[:1]:
                score += 0.2

            candidates.append((score, other_term))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        ordered = [term for _, term in candidates]
        return self._dedupe_list(ordered)[:limit]

    def _select_distractor_terms_from_context(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        existing: Optional[Iterable[str]] = None,
        limit: int = 1,
    ) -> List[str]:
        """Extract fallback distractors from the source section text."""
        existing = set(existing or [])
        context = self._get_source_context(concept, section_lookup, limit=220)
        if not context:
            return []

        candidates = re.findall(
            r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9\-]{2,20}",
            context,
        )
        results = []
        for candidate in candidates:
            candidate = self._clean_text(candidate)
            if (
                candidate
                and candidate != concept.get("term", "")
                and candidate not in existing
                and candidate not in results
            ):
                results.append(candidate)
            if len(results) >= limit:
                break
        return results

    def _build_section_lookup(
        self, sections: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        return {section.get("sec_id", ""): section for section in sections if section.get("sec_id")}

    def _get_primary_ref(self, concept: Dict[str, Any]) -> str:
        refs = concept.get("refs", [])
        return refs[0] if refs else ""

    def _get_source_context(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        limit: int = 180,
    ) -> str:
        for ref in concept.get("refs", []):
            section = section_lookup.get(ref)
            if not section:
                continue
            text = self._strip_markdown_artifacts(section.get("text", ""))
            if text:
                return self._shorten_text(text, limit)
        return ""

    def _pick_cloze_target(self, sentence: str) -> str:
        quoted = re.findall(r"(?:“|《|「|『)(.{2,12}?)(?:”|》|」|』)", sentence)
        if quoted:
            return quoted[0]

        words = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9\-]{2,20}", sentence)
        stop_words = {"这个", "那个", "我们", "他们", "用于", "包括", "通过", "可以"}
        candidates = [word for word in words if word not in stop_words]
        return candidates[len(candidates) // 2] if candidates else ""

    def _is_study_worthy_term(self, term: str) -> bool:
        term = self._clean_text(term)
        compact = re.sub(r"\s+", "", term)
        if len(compact) < 2 or len(compact) > 20:
            return False
        if compact in self.invalid_term_exact:
            return False
        if any(compact.startswith(prefix) for prefix in self.invalid_term_prefixes):
            return False
        if re.search(r"[*_#`]|[:：?!？！]|[“”\"'‘’]", term):
            return False
        if "自己" in compact or "____" in compact:
            return False
        if "你" in compact or "我们" in compact or "他们" in compact:
            return False
        if any(token in compact for token in ("写道", "不仅仅", "到底", "下个星期", "像这样", "大自然就", "是因为", "打个响")):
            return False
        if compact.endswith(("写道", "仅仅", "到底", "不是", "而不", "而不是", "不")):
            return False
        if len(compact) <= 2 and compact.endswith("型"):
            return False
        if len(compact) <= 4 and compact.endswith(("的", "地", "得", "了", "着", "过", "不")):
            return False
        return True

    def _normalize_knowledge_stem(self, stem: Any, fallback_term: str = "") -> str:
        stem_text = self._strip_markdown_artifacts(stem)
        fallback_term = self._clean_text(fallback_term)
        candidate = stem_text or fallback_term

        if not candidate:
            return ""
        if candidate.startswith(("什么是", "请解释", "如何理解", "为什么")):
            return candidate
        if any(marker in candidate for marker in ("？", "?", "：", ":")) and len(candidate) > 8:
            return candidate
        if len(candidate) <= 24 and self._is_study_worthy_term(candidate):
            return f"什么是“{candidate}”？"
        return candidate

    def _select_cloze_sentence(
        self,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        term: str,
    ) -> str:
        for ref in concept.get("refs", []):
            section = section_lookup.get(ref)
            if not section:
                continue
            text = self._strip_markdown_artifacts(section.get("text", ""))
            if not text:
                continue
            for sentence in self._split_sentences(text):
                sentence = self._strip_markdown_artifacts(sentence)
                if self._is_viable_cloze_sentence(sentence, term):
                    return sentence
        return ""

    def _build_definition_cloze(self, term: str, definition: str) -> str:
        clue = self._strip_markdown_artifacts(definition)
        if not clue or len(clue) < 12 or len(clue) > 110:
            return ""
        if any(marker in clue for marker in ("____", "________", "→", "⚠️", "✍️", "http://", "https://")):
            return ""

        clue = re.sub(
            r"[，,]?\s*通过(?:填写|写下)?“[^”]{0,40}[:：]?\s*”来(?:识别|揭示|表达|定义|说明)",
            "",
            clue,
        )
        clue = re.sub(r"\s{2,}", " ", clue).strip()

        for prefix in ("指的是", "是指", "指", "是"):
            if clue.startswith(prefix) and len(clue) - len(prefix) >= 8:
                clue = clue[len(prefix) :].lstrip("，,：: ")
                break

        clue = clue.rstrip("。！？!?；; ")
        if not clue:
            return ""

        stem = f"根据文档，下列描述指的是 ____。{clue}。"
        return stem if self._is_clean_cloze_stem(stem) else ""

    def _build_cloze_stem(
        self,
        term: str,
        concept: Dict[str, Any],
        section_lookup: Dict[str, Dict[str, Any]],
        definition: str,
    ) -> str:
        definition_stem = self._build_definition_cloze(term, definition)
        if definition_stem:
            return definition_stem

        sentence = self._select_cloze_sentence(concept, section_lookup, term)
        if sentence:
            stem = sentence.replace(term, "____", 1)
            return stem if self._is_clean_cloze_stem(stem) else ""
        if term in definition and len(definition) <= 100:
            stem = definition.replace(term, "____", 1)
            return stem if self._is_clean_cloze_stem(stem) else ""
        return ""

    def _is_viable_cloze_sentence(self, sentence: str, term: str) -> bool:
        sentence = self._clean_text(sentence)
        if (
            term not in sentence
            or len(sentence) < 16
            or len(sentence) > 120
            or sentence.count(term) != 1
            or sentence.count("，") + sentence.count(",") > 3
        ):
            return False
        if "____" in sentence or "________" in sentence:
            return False
        if self._looks_like_structured_prompt(sentence):
            return False
        return True

    def _looks_like_structured_prompt(self, text: str) -> bool:
        text = self._clean_text(text)
        if not text:
            return False
        if any(marker in text for marker in ("→", "⚠️", "✍️", "——", " - ")):
            return True
        if re.match(r"^(步骤\s*\d+|第[一二三四五六七八九十\d]+步|附加题|记住|最后|然后)\s*[:：]", text):
            return True
        if re.match(r"^[^。！？!?]{1,12}\s*[:：]", text):
            return True
        return False

    def _is_clean_cloze_stem(self, stem: str) -> bool:
        stem = self._clean_text(stem)
        if len(stem) < 12 or len(stem) > 120:
            return False
        if stem.count("____") != 1:
            return False
        if stem.startswith(("“", "”", ":", "：", "-", "—", "–")):
            return False
        if stem.startswith(("____：", "____:", "____（", "____(", "____ -", "____—", "____–")):
            return False
        if stem.count("“") + stem.count("”") + stem.count('"') > 2:
            return False
        if stem.count("：") + stem.count(":") > 1:
            return False
        if self._looks_like_structured_prompt(stem):
            return False
        if any(
            marker in stem
            for marker in ("我正在构建：", "我绝对拒绝让我的人生变成：", "我是那种")
        ):
            return False
        return True

    def _apply_build_preferences(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select and order cards according to requested build preferences."""
        filtered_cards = [
            card for card in cards if card.get("type") in self.allowed_card_types
        ]
        if not filtered_cards:
            return []

        target_count = min(len(filtered_cards), max(1, self.target_card_count))
        type_order = self._get_type_priority_order()
        strategy_weights = {
            "balanced": {"knowledge": 3, "cloze": 3, "mcq": 2, "short": 2},
            "memory": {"knowledge": 4, "cloze": 3, "short": 2, "mcq": 1},
            "challenge": {"mcq": 4, "short": 3, "cloze": 2, "knowledge": 1},
        }.get(self.build_strategy, {"knowledge": 3, "cloze": 3, "mcq": 2, "short": 2})

        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for card_type in type_order:
            bucket = [
                card for card in filtered_cards if card.get("type") == card_type
            ]
            if bucket:
                bucket.sort(key=self._card_priority_key)
                buckets[card_type] = bucket

        selected: List[Dict[str, Any]] = []
        anchor_counts: Dict[str, int] = defaultdict(int)
        type_counts: Dict[str, int] = defaultdict(int)

        def take_from_bucket(card_type: str) -> Optional[Dict[str, Any]]:
            bucket = buckets.get(card_type, [])
            if not bucket:
                return None

            bucket.sort(
                key=lambda card: (
                    anchor_counts[self._card_anchor(card)],
                    self._card_priority_key(card),
                )
            )
            candidate = bucket.pop(0)
            if not bucket:
                buckets.pop(card_type, None)
            return candidate

        def remember(card: Dict[str, Any]) -> None:
            selected.append(card)
            anchor_counts[self._card_anchor(card)] += 1
            type_counts[str(card.get("type", ""))] += 1

        for card_type in type_order:
            if len(selected) >= target_count:
                break
            candidate = take_from_bucket(card_type)
            if candidate:
                remember(candidate)

        while len(selected) < target_count and buckets:
            available_types = [card_type for card_type in type_order if card_type in buckets]
            if not available_types:
                break

            next_type = min(
                available_types,
                key=lambda card_type: (
                    type_counts[card_type] / max(1, strategy_weights.get(card_type, 1)),
                    type_order.index(card_type),
                ),
            )
            candidate = take_from_bucket(next_type)
            if candidate:
                remember(candidate)

        return selected

    def _get_practice_type_order(self) -> List[str]:
        return [
            card_type
            for card_type in self._get_type_priority_order()
            if card_type != "knowledge"
        ]

    def _get_type_priority_order(self) -> List[str]:
        preferred_order = {
            "balanced": ["knowledge", "cloze", "mcq", "short"],
            "memory": ["knowledge", "cloze", "short", "mcq"],
            "challenge": ["mcq", "short", "cloze", "knowledge"],
        }.get(self.build_strategy, self.TYPE_PRIORITY)

        ordered: List[str] = []
        for card_type in preferred_order + self.TYPE_PRIORITY:
            if card_type in self.allowed_card_types and card_type not in ordered:
                ordered.append(card_type)
        return ordered

    def _card_priority_key(self, card: Dict[str, Any]) -> tuple:
        type_order = self._get_type_priority_order()
        card_type = str(card.get("type", ""))
        difficulty = str(card.get("difficulty", "M")).upper()
        difficulty_rank = self._difficulty_rank(difficulty)

        if self.difficulty_mode == "mixed":
            difficulty_penalty = 0
        else:
            difficulty_penalty = abs(
                difficulty_rank - self._difficulty_rank(self.difficulty_mode)
            )

        type_index = (
            type_order.index(card_type) if card_type in type_order else len(type_order)
        )

        return (
            difficulty_penalty,
            type_index,
            difficulty_rank,
            self._card_anchor(card),
            self._normalize_text(str(card.get("stem", ""))),
            str(card.get("card_id", "")),
        )

    def _difficulty_rank(self, difficulty: str) -> int:
        return {"L": 0, "M": 1, "H": 2}.get(str(difficulty).upper(), 1)

    def _card_anchor(self, card: Dict[str, Any]) -> str:
        concept_refs = card.get("concept_refs", [])
        if isinstance(concept_refs, list):
            for concept_ref in concept_refs:
                if isinstance(concept_ref, str) and concept_ref.strip():
                    return concept_ref.strip()

        source_ref = self._clean_text(card.get("source_ref", ""))
        return source_ref or self._clean_text(card.get("card_id", ""))

    def _count_by_type(self, cards: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {"knowledge": 0, "cloze": 0, "mcq": 0, "short": 0}
        for card in cards:
            card_type = card.get("type")
            if card_type in counts:
                counts[card_type] += 1
        return counts

    def _count_by_difficulty(self, cards: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {"L": 0, "M": 0, "H": 0}
        for card in cards:
            difficulty = str(card.get("difficulty", "")).upper()
            if difficulty in counts:
                counts[difficulty] += 1
        return counts

    def _parse_json_payload(self, response: Optional[str]) -> Optional[Any]:
        """Parse structured LLM output with tolerant JSON extraction."""
        if not response:
            return None

        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        candidate = self._extract_first_json_block(text)
        if not candidate:
            return None

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def _extract_first_json_block(self, text: str) -> Optional[str]:
        for open_char, close_char in [("[", "]"), ("{", "}")]:
            start = text.find(open_char)
            while start != -1:
                depth = 0
                in_string = False
                escape = False
                for index in range(start, len(text)):
                    char = text[index]
                    if in_string:
                        if escape:
                            escape = False
                        elif char == "\\":
                            escape = True
                        elif char == '"':
                            in_string = False
                        continue

                    if char == '"':
                        in_string = True
                    elif char == open_char:
                        depth += 1
                    elif char == close_char:
                        depth -= 1
                        if depth == 0:
                            return text[start : index + 1]
                start = text.find(open_char, start + 1)
        return None

    def _split_sentences(self, text: str) -> List[str]:
        return [part.strip() for part in re.split(r"[。！？!?；;\n]", text) if part.strip()]

    def _clean_text(self, text: Any) -> str:
        text = str(text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _strip_markdown_artifacts(self, text: Any) -> str:
        cleaned = self._clean_text(text)
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned)
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
        cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
        return self._clean_text(cleaned)

    def _normalize_text(self, text: str) -> str:
        text = self._clean_text(text).lower()
        return re.sub(r"[\s\W_]+", "", text)

    def _shorten_text(self, text: str, limit: int) -> str:
        text = self._clean_text(text)
        if len(text) <= limit:
            return text
        shortened = text[:limit].rstrip("，,；; ")
        return shortened + "..."

    def _dedupe_list(self, items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            key = self._normalize_text(item)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _shuffle_choices(self, choices: List[str], answer: str) -> List[str]:
        """Stable pseudo-shuffle so results stay deterministic."""
        unique_choices = self._dedupe_list(choices)
        if answer not in unique_choices:
            unique_choices.append(answer)
        return sorted(unique_choices, key=lambda item: (item == answer, self._normalize_text(item)))
