"""
Concept extraction and lightweight relation building.
"""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base_agent import BaseAgent


class ConceptAgent(BaseAgent):
    """
    Extract concepts, definitions and lightweight relations from document sections.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="ConceptAgent", config=config)

        config = config or {}
        self.similarity_threshold = config.get("similarity_threshold", 0.85)
        self.min_concept_length = config.get("min_concept_length", 2)
        self.max_concept_length = config.get("max_concept_length", 20)
        self.max_concepts_per_section = config.get("max_concepts_per_section", 6)
        self.llm_section_limit = config.get("llm_section_limit", 12)
        self.llm_char_limit = config.get("llm_char_limit", 1400)
        self.use_llm = config.get("use_llm", False)

        self.stop_terms = {
            "我们",
            "你们",
            "他们",
            "它们",
            "这个",
            "那个",
            "这些",
            "那些",
            "问题",
            "方法",
            "过程",
            "内容",
            "情况",
            "东西",
            "部分",
            "结果",
            "系统",
            "模型",
            "方式",
            "能力",
            "作者",
            "例如",
            "比如",
            "以下",
            "某天",
            "问自己",
            "写下",
            "接着问自己",
            "试想一下",
            "而不是",
            "而不",
        }
        self.fragment_terms = {
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
            "现在延伸到10年后",
            "最后",
            "记住",
        }
        self.fragment_prefixes = (
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
        self.fragment_suffixes = ("的", "地", "得", "了", "着", "过", "不")
        self.definition_keywords = (
            "是",
            "指",
            "表示",
            "意味着",
            "用于",
            "包括",
            "由",
            "通过",
            "可以",
        )

        self.llm = None
        if self.use_llm:
            try:
                from nlp.llm_helper import get_llm

                self.llm = get_llm()
                if self.llm.is_available():
                    self.logger.info("LLM enabled for concept extraction")
                else:
                    self.logger.warning("LLM configured but not available")
            except Exception as exc:
                self.logger.warning("Failed to initialize LLM: %s", exc)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract concepts and relations from sections.
        """
        self.validate_input(input_data, ["doc_id", "sections"])

        doc_id = input_data["doc_id"]
        sections = input_data["sections"]
        self.logger.info("Extracting concepts from %s sections", len(sections))

        llm_candidates: List[Dict[str, Any]] = []
        if self.llm and self.llm.is_available():
            llm_candidates = self._extract_concepts_llm(sections, doc_id)

        rule_candidates: List[Dict[str, Any]] = []
        if len(llm_candidates) < 8:
            rule_candidates = self._extract_concepts(sections, doc_id)
        elif llm_candidates:
            self.logger.info(
                "Using LLM concept candidates as the primary source; skipping noisy rule fallback"
            )

        concepts = self._merge_similar_concepts(llm_candidates + rule_candidates)
        concepts = self._assign_concept_ids(concepts, doc_id)
        relations = self._extract_relations(concepts)

        result = {
            "doc_id": doc_id,
            "concepts": concepts,
            "relations": relations,
            "metadata": {
                "total_concepts": len(concepts),
                "total_relations": len(relations),
            },
        }

        self.log_audit(
            action="extract_concepts",
            input_summary=f"doc_id={doc_id}, {len(sections)} sections",
            output_summary=f"{len(concepts)} concepts, {len(relations)} relations",
        )
        return result

    def _extract_concepts(
        self, sections: List[Dict[str, Any]], doc_id: str
    ) -> List[Dict[str, Any]]:
        """Rule-based concept extraction."""
        concepts: List[Dict[str, Any]] = []

        for section in sections:
            text = self._clean_text(section.get("text", ""))
            sec_id = section.get("sec_id", "")
            if len(text) < 20:
                continue

            candidates = self._extract_definition_candidates(text)
            if len(candidates) < 2:
                candidates.extend(self._extract_keyword_candidates(text))

            seen_terms = set()
            per_section = 0
            for term, definition in candidates:
                term_key = self._normalize_term(term)
                if not term_key or term_key in seen_terms:
                    continue

                concept = self._build_concept_candidate(term, definition, doc_id, sec_id)
                if not concept:
                    continue

                concepts.append(concept)
                seen_terms.add(term_key)
                per_section += 1
                if per_section >= self.max_concepts_per_section:
                    break

        return concepts

    def _extract_concepts_llm(
        self, sections: List[Dict[str, Any]], doc_id: str
    ) -> List[Dict[str, Any]]:
        """Section-level concept extraction using the configured LLM."""
        if not self.llm:
            return []

        concepts: List[Dict[str, Any]] = []
        llm_sections = [
            section for section in sections if len(self._clean_text(section.get("text", ""))) >= 80
        ][: self.llm_section_limit]

        for section in llm_sections:
            sec_id = section.get("sec_id", "")
            text = self._truncate_text(section.get("text", ""), self.llm_char_limit)
            try:
                llm_concepts = self.llm.extract_concepts(text)
            except Exception as exc:
                self.logger.error("LLM concept extraction failed for %s: %s", sec_id, exc)
                continue

            per_section = 0
            for item in llm_concepts:
                if not isinstance(item, dict):
                    continue
                concept = self._build_concept_candidate(
                    item.get("term", ""),
                    item.get("definition", ""),
                    doc_id,
                    sec_id,
                    aliases=item.get("aliases", []),
                )
                if not concept:
                    continue

                concepts.append(concept)
                per_section += 1
                if per_section >= self.max_concepts_per_section:
                    break

        self.logger.info("LLM extracted %s raw concept candidates", len(concepts))
        return concepts

    def _extract_definition_candidates(self, text: str) -> List[Tuple[str, str]]:
        """Pull explicit term-definition pairs from informative sentences."""
        candidates: List[Tuple[str, str]] = []
        sentences = self._split_sentences(text)
        patterns = [
            re.compile(
                r"(?P<term>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·()（）\-]{1,24}?)"
                r"\s*(?:是指|指的是|通常指|可以理解为|可理解为|是|即|指)\s*"
                r"(?P<definition>[^。！？；\n]{8,140})"
            ),
            re.compile(
                r"(?:所谓|其中|这里的)\s*(?P<term>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·()（）\-]{1,24}?)"
                r"\s*(?:是指|是|指)\s*(?P<definition>[^。！？；\n]{8,140})"
            ),
            re.compile(
                r"(?P<term>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·()（）\-]{1,24}?)\s*[:：]\s*"
                r"(?P<definition>[^。！？；\n]{8,140})"
            ),
            re.compile(
                r"(?P<term>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·()（）\-]{1,24}?)"
                r"\s*(?:用于|用来|负责|衡量|描述|解释)\s*"
                r"(?P<definition>[^。！？；\n]{8,140})"
            ),
            re.compile(
                r"(?P<term>[A-Z][A-Za-z0-9\- ]{1,30})\s+(?:is|refers to|means)\s+"
                r"(?P<definition>[^.!?\n]{8,140})",
                flags=re.IGNORECASE,
            ),
        ]

        for sentence in sentences:
            for pattern in patterns:
                for match in pattern.finditer(sentence):
                    term = match.group("term")
                    definition = match.group("definition")
                    candidates.append((term, definition))

        return candidates

    def _extract_keyword_candidates(self, text: str) -> List[Tuple[str, str]]:
        """Fallback candidate extraction using quoted terms and repeated keywords."""
        candidates: List[Tuple[str, str]] = []
        sentences = self._split_sentences(text)

        for term in re.findall(r"(?:“|《|「|『|\"|'|‘)(.{2,20}?)(?:”|》|」|』|\"|'|’)", text):
            sentence = self._find_best_sentence_for_term(term, sentences)
            if sentence:
                candidates.append((term, sentence))

        sentence_patterns = [
            re.compile(
                r"(?P<term>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·()（）\-]{1,16}?)"
                r"\s*(?:用于|用来|可以|能够|通过|包括|分为)\s*"
                r"(?P<definition>[^。！？；\n]{8,140})"
            ),
            re.compile(
                r"(?P<term>[A-Z][A-Za-z0-9\- ]{1,24})\s+(?:can|may|uses?|includes?)\s+"
                r"(?P<definition>[^.!?\n]{8,140})",
                flags=re.IGNORECASE,
            ),
        ]

        for sentence in sentences:
            for pattern in sentence_patterns:
                for match in pattern.finditer(sentence):
                    candidates.append((match.group("term"), match.group("definition")))

        return candidates

    def _build_concept_candidate(
        self,
        term: str,
        definition: str,
        doc_id: str,
        sec_id: str,
        aliases: Optional[Iterable[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Normalize and validate a raw concept candidate."""
        term = self._clean_term(term)
        definition = self._clean_definition(definition)
        aliases = aliases or []
        alias_values = [
            self._clean_term(alias)
            for alias in aliases
            if isinstance(alias, str) and self._clean_term(alias)
        ]

        if not self._is_valid_term(term):
            return None
        if not self._is_informative_definition(term, definition):
            return None

        alias_values = sorted(
            {
                alias
                for alias in alias_values
                if alias and self._normalize_term(alias) != self._normalize_term(term)
            }
        )

        return {
            "doc_id": doc_id,
            "term": term,
            "aliases": alias_values,
            "definition": definition,
            "refs": [sec_id] if sec_id else [],
        }

    def _merge_similar_concepts(
        self, concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge duplicated or near-duplicated concepts."""
        merged: List[Dict[str, Any]] = []

        for concept in concepts:
            matched_index = None
            for index, existing in enumerate(merged):
                if self._should_merge(existing, concept):
                    matched_index = index
                    break

            if matched_index is None:
                merged.append(
                    {
                        "doc_id": concept["doc_id"],
                        "term": concept["term"],
                        "aliases": list(concept.get("aliases", [])),
                        "definition": concept["definition"],
                        "refs": list(concept.get("refs", [])),
                    }
                )
            else:
                merged[matched_index] = self._merge_concept_pair(
                    merged[matched_index], concept
                )

        merged.sort(
            key=lambda item: (
                -len(item.get("refs", [])),
                -self._term_quality_score(item.get("term", "")),
                -self._definition_quality_score(item.get("definition", "")),
                len(item.get("term", "")),
            )
        )
        return merged

    def _assign_concept_ids(
        self, concepts: List[Dict[str, Any]], doc_id: str
    ) -> List[Dict[str, Any]]:
        """Attach stable concept ids after merge."""
        finalized = []
        for index, concept in enumerate(concepts):
            finalized.append(
                {
                    "cid": f"{doc_id}_c{index}",
                    "doc_id": doc_id,
                    "term": concept["term"],
                    "aliases": concept.get("aliases", []),
                    "definition": concept["definition"],
                    "refs": concept.get("refs", []),
                }
            )
        return finalized

    def _extract_relations(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create lightweight related_to relations based on shared section refs."""
        relation_weights: Dict[Tuple[str, str], int] = defaultdict(int)
        section_to_concepts: Dict[str, List[str]] = defaultdict(list)

        for concept in concepts:
            for sec_id in concept.get("refs", []):
                section_to_concepts[sec_id].append(concept["cid"])

        for concept_ids in section_to_concepts.values():
            unique_ids = sorted(set(concept_ids))
            for src, dst in combinations(unique_ids, 2):
                relation_weights[(src, dst)] += 1

        relations = []
        for index, ((src, dst), weight) in enumerate(
            sorted(relation_weights.items(), key=lambda item: (-item[1], item[0]))
        ):
            relations.append(
                {
                    "id": f"r{index}",
                    "src": src,
                    "rel": "related_to",
                    "dst": dst,
                    "weight": float(weight),
                }
            )
        return relations

    def _should_merge(
        self, left: Dict[str, Any], right: Dict[str, Any]
    ) -> bool:
        """Decide whether two concept candidates represent the same concept."""
        left_key = self._normalize_term(left.get("term", ""))
        right_key = self._normalize_term(right.get("term", ""))

        if not left_key or not right_key:
            return False
        if left_key == right_key:
            return True

        left_aliases = {self._normalize_term(alias) for alias in left.get("aliases", [])}
        right_aliases = {self._normalize_term(alias) for alias in right.get("aliases", [])}
        if left_key in right_aliases or right_key in left_aliases:
            return True
        if left_aliases & right_aliases:
            return True

        similarity = self._definition_similarity(
            left.get("definition", ""), right.get("definition", "")
        )
        if (left_key in right_key or right_key in left_key) and similarity >= 0.55:
            return True

        return similarity >= max(0.65, self.similarity_threshold - 0.15)

    def _merge_concept_pair(
        self, left: Dict[str, Any], right: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two concept candidates into a single richer concept."""
        left_score = self._term_quality_score(left.get("term", ""))
        right_score = self._term_quality_score(right.get("term", ""))

        primary = left if left_score >= right_score else right
        secondary = right if primary is left else left

        aliases = {
            alias
            for alias in primary.get("aliases", []) + secondary.get("aliases", [])
            if alias
        }
        aliases.add(secondary.get("term", ""))
        aliases.discard(primary.get("term", ""))

        primary_definition = primary.get("definition", "")
        secondary_definition = secondary.get("definition", "")
        definition = (
            primary_definition
            if self._definition_quality_score(primary_definition)
            >= self._definition_quality_score(secondary_definition)
            else secondary_definition
        )

        refs = sorted(set(primary.get("refs", []) + secondary.get("refs", [])))
        return {
            "doc_id": primary.get("doc_id") or secondary.get("doc_id"),
            "term": primary.get("term", ""),
            "aliases": sorted(alias for alias in aliases if alias),
            "definition": definition,
            "refs": refs,
        }

    def _definition_similarity(self, left: str, right: str) -> float:
        """Simple token overlap score used for deduplication."""
        left_tokens = self._tokenize_for_similarity(left)
        right_tokens = self._tokenize_for_similarity(right)
        if not left_tokens or not right_tokens:
            return 0.0

        intersection = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        return intersection / union if union else 0.0

    def _tokenize_for_similarity(self, text: str) -> set:
        english_tokens = re.findall(r"[a-z0-9]+", text.lower())
        chinese_tokens = re.findall(r"[\u4e00-\u9fff]", text)
        return set(english_tokens + chinese_tokens)

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[。！？!?；;\n])", text)
        return [part.strip() for part in parts if part and part.strip()]

    def _find_best_sentence_for_term(self, term: str, sentences: List[str]) -> str:
        for sentence in sentences:
            if term in sentence:
                return sentence[:160]
        return ""

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "")
        return text.strip()

    def _clean_term(self, term: str) -> str:
        term = self._clean_text(term)
        term = term.strip("“”\"'‘’《》「」『』()（）[]【】,，。；;：: ")
        term = re.sub(r"^(所谓|这里的|其中的)", "", term)
        term = re.sub(r"(是|指)$", "", term)
        return term.strip()

    def _clean_definition(self, definition: str) -> str:
        definition = self._clean_text(definition)
        definition = definition.strip("“”\"'‘’《》「」『』")
        definition = re.sub(r"^[：:\-]+", "", definition).strip()
        if len(definition) > 180:
            definition = definition[:180].rstrip("，,；; ")
        return definition

    def _normalize_term(self, term: str) -> str:
        term = self._clean_term(term).lower()
        term = re.sub(r"[\s_\-·()（）【】\[\]\"'“”‘’《》「」『』:：,，。；;!?！？]", "", term)
        return term

    def _looks_like_fragment_term(self, term: str, normalized: str) -> bool:
        compact = re.sub(r"\s+", "", self._clean_term(term))
        if not compact:
            return True
        if compact in self.fragment_terms or normalized in self.fragment_terms:
            return True
        if any(compact.startswith(prefix) for prefix in self.fragment_prefixes):
            return True
        if len(compact) <= 4 and compact.endswith(self.fragment_suffixes):
            return True
        if re.search(r"[*_#`]|[:：?!？！]|[“”\"'‘’]", term):
            return True
        if re.search(r"\d+[:：]\d+|^\d+$", compact):
            return True
        if "____" in compact or "自己" in compact:
            return True
        if "你" in compact or "我们" in compact or "他们" in compact:
            return True
        if any(token in compact for token in ("写道", "不仅仅", "到底", "下个星期", "像这样", "大自然就", "是因为", "打个响")):
            return True
        if compact.endswith(("写道", "仅仅", "到底", "不是", "而不", "而不是", "不")):
            return True
        if len(compact) <= 2 and compact.endswith("型"):
            return True
        return False

    def _is_valid_term(self, term: str) -> bool:
        normalized = self._normalize_term(term)
        if not normalized:
            return False
        if normalized in self.stop_terms:
            return False
        if self._looks_like_fragment_term(term, normalized):
            return False
        if len(term) < self.min_concept_length or len(term) > self.max_concept_length:
            return False
        if normalized.isdigit():
            return False
        if re.fullmatch(r"[A-Za-z]$", term):
            return False
        return True

    def _is_informative_definition(self, term: str, definition: str) -> bool:
        if not definition or len(definition) < 8:
            return False
        if self._normalize_term(definition) == self._normalize_term(term):
            return False
        if len(definition) > 180:
            return False
        token_count = len(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", definition))
        return token_count >= 6

    def _term_quality_score(self, term: str) -> float:
        score = 0.0
        normalized = self._normalize_term(term)
        if self._looks_like_fragment_term(term, normalized):
            return -1.0
        if 2 <= len(term) <= 12:
            score += 2
        if normalized and normalized not in self.stop_terms:
            score += 1
        if re.search(r"[\u4e00-\u9fffA-Za-z]", term):
            score += 1
        if term.endswith(("方法", "模型", "理论", "算法", "结构", "机制", "系统")):
            score += 0.5
        return score

    def _definition_quality_score(self, definition: str) -> float:
        score = min(len(definition), 120) / 40
        if any(keyword in definition for keyword in self.definition_keywords):
            score += 1
        if re.search(r"[。；;]", definition):
            score -= 0.2
        return score

    def _truncate_text(self, text: str, limit: int) -> str:
        cleaned = self._clean_text(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rsplit(" ", 1)[0] or cleaned[:limit]
