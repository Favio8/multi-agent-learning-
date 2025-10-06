"""
QuizAgent - Generate learning cards (cloze, MCQ, short answer)
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import asyncio
import concurrent.futures
from functools import partial
import random


class QuizAgent(BaseAgent):
    """
    QuizAgent generates various types of learning cards:
    - Cloze (fill-in-the-blank)
    - Multiple Choice Questions (MCQ)
    - Short Answer Questions
    
    Includes quality control mechanisms
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="QuizAgent", config=config)
        
        self.cards_per_concept = config.get("cards_per_concept", 2) if config else 2
        self.min_distractor_similarity = config.get("min_distractor_similarity", 0.3) if config else 0.3
        self.use_llm = config.get("use_llm", False) if config else False
        
        # 初始化LLM（如果启用）
        self.llm = None
        if self.use_llm:
            try:
                from nlp.llm_helper import get_llm
                self.llm = get_llm()
                if self.llm.is_available():
                    self.logger.info("LLM enabled for quiz generation")
                else:
                    self.logger.warning("LLM configured but not available")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM: {e}")
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate quiz cards from concepts and sections
        
        Args:
            input_data: {
                "doc_id": str,
                "concepts": [...],
                "relations": [...],
                "sections": [...]
            }
            
        Returns:
            {
                "doc_id": str,
                "cards": [
                    {
                        "card_id": str,
                        "type": "cloze|mcq|short",
                        "stem": str,
                        "choices": [str] (for MCQ),
                        "answer": str,
                        "explanation": str,
                        "source_ref": str,
                        "concept_refs": [str],
                        "difficulty": "L|M|H"
                    }
                ]
            }
        """
        self.validate_input(input_data, ["doc_id"])
        
        doc_id = input_data["doc_id"]
        concepts = input_data.get("concepts", [])
        sections = input_data.get("sections", [])
        
        self.logger.info(f"Generating quiz cards for {len(concepts)} concepts from {len(sections)} sections")
        
        cards = []
        
        # Method 1: Generate cards from concepts
        if self.llm and self.llm.is_available():
            # 使用并发生成（大幅提速）
            self.logger.info(f"Using concurrent generation for {len(concepts)} concepts")
            cards = self._generate_cards_concurrent(concepts, doc_id)
        else:
            # 使用规则方法（串行）
            for concept in concepts:
                # Generate cloze card
                cloze_card = self._generate_cloze(concept, doc_id)
                if cloze_card:
                    cards.append(cloze_card)
                
                # Generate MCQ card
                mcq_card = self._generate_mcq(concept, concepts, doc_id)
                if mcq_card:
                    cards.append(mcq_card)
                
                # Optionally generate short answer
                if random.random() < 0.5:  # 50% chance
                    short_card = self._generate_short_answer(concept, doc_id)
                    if short_card:
                        cards.append(short_card)
        
        # Method 2: Generate cards directly from sections (fallback if few concepts)
        if len(cards) < 3 and sections:
            self.logger.info("Generating additional cards from sections")
            section_cards = self._generate_cards_from_sections(sections, doc_id)
            cards.extend(section_cards)
        
        # Quality check
        cards = self._quality_check(cards)
        
        result = {
            "doc_id": doc_id,
            "cards": cards,
            "metadata": {
                "total_cards": len(cards),
                "by_type": self._count_by_type(cards)
            }
        }
        
        self.log_audit(
            action="generate_cards",
            input_summary=f"doc_id={doc_id}, {len(concepts)} concepts, {len(sections)} sections",
            output_summary=f"{len(cards)} cards generated"
        )
        
        return result
    
    def _generate_cloze(self, concept: Dict[str, Any], doc_id: str) -> Optional[Dict[str, Any]]:
        """Generate cloze (fill-in-the-blank) card"""
        term = concept["term"]
        definition = concept.get("definition", "")
        
        if not definition:
            return None
        
        # Replace term with blank
        stem = definition.replace(term, "____")
        
        # If nothing was replaced, try to create a different cloze
        if stem == definition:
            # Blank out a key part of the definition
            words = definition.split()
            if len(words) > 3:
                # Blank out middle portion
                mid = len(words) // 2
                words[mid] = "____"
                stem = " ".join(words)
                answer = definition.split()[mid]
            else:
                return None
        else:
            answer = term
        
        card = {
            "card_id": f"{doc_id}_{concept['cid']}_cloze",
            "doc_id": doc_id,  # 添加doc_id字段
            "type": "cloze",
            "stem": stem,
            "choices": [],
            "answer": answer,
            "explanation": f"完整定义：{definition}",
            "source_ref": concept.get("refs", [""])[0],
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "cloze")
        }
        
        return card
    
    def _generate_mcq(self, concept: Dict[str, Any], all_concepts: List[Dict[str, Any]], 
                     doc_id: str) -> Optional[Dict[str, Any]]:
        """Generate multiple choice question"""
        term = concept["term"]
        definition = concept.get("definition", "")
        
        if not definition:
            return None
        
        # Create question stem
        stem = f"{term}的定义是？"
        
        # Correct answer
        answer = definition
        
        # Generate distractors from other concepts
        distractors = []
        for other in all_concepts:
            if other["cid"] != concept["cid"] and other.get("definition"):
                distractors.append(other["definition"])
        
        # Select 3 distractors
        if len(distractors) < 3:
            # Not enough distractors, create generic ones
            distractors = [
                "一种数据结构",
                "一种算法",
                "一种编程语言特性"
            ]
        else:
            distractors = random.sample(distractors, 3)
        
        # Combine and shuffle choices
        choices = [answer] + distractors
        random.shuffle(choices)
        
        card = {
            "card_id": f"{doc_id}_{concept['cid']}_mcq",
            "doc_id": doc_id,  # 添加doc_id字段
            "type": "mcq",
            "stem": stem,
            "choices": choices,
            "answer": answer,
            "explanation": f"{term}是指{definition}",
            "source_ref": concept.get("refs", [""])[0],
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "mcq")
        }
        
        return card
    
    def _generate_short_answer(self, concept: Dict[str, Any], doc_id: str) -> Optional[Dict[str, Any]]:
        """Generate short answer question"""
        term = concept["term"]
        definition = concept.get("definition", "")
        
        if not definition:
            return None
        
        # Create various question types
        question_templates = [
            f"请简述{term}的含义。",
            f"什么是{term}？",
            f"解释{term}的概念。"
        ]
        
        stem = random.choice(question_templates)
        
        card = {
            "card_id": f"{doc_id}_{concept['cid']}_short",
            "doc_id": doc_id,  # 添加doc_id字段
            "type": "short",
            "stem": stem,
            "choices": [],
            "answer": definition,
            "explanation": f"标准答案：{definition}",
            "source_ref": concept.get("refs", [""])[0],
            "concept_refs": [concept["cid"]],
            "difficulty": self._estimate_difficulty(concept, "short")
        }
        
        return card
    
    def _estimate_difficulty(self, concept: Dict[str, Any], card_type: str) -> str:
        """Estimate initial difficulty level"""
        # TODO: Use concept graph depth, term rarity, definition complexity
        
        definition = concept.get("definition", "")
        term = concept.get("term", "")
        
        # Simple heuristic based on length and complexity
        score = 0
        
        # Definition length
        if len(definition) > 50:
            score += 1
        if len(definition) > 100:
            score += 1
        
        # Term length (longer terms might be more specific/complex)
        if len(term) > 6:
            score += 1
        
        # Card type difficulty
        if card_type == "short":
            score += 1
        elif card_type == "cloze":
            score += 0.5
        
        if score >= 2:
            return "H"
        elif score >= 1:
            return "M"
        else:
            return "L"
    
    def _quality_check(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Quality check for generated cards"""
        # TODO: Implement:
        # - Self-consistency check
        # - Fact verification against source
        # - Remove ambiguous questions
        
        valid_cards = []
        
        for card in cards:
            # Basic checks
            if not card.get("stem") or not card.get("answer"):
                self.logger.warning(f"Skipping invalid card: {card.get('card_id')}")
                continue
            
            # Check for too short questions
            if len(card["stem"]) < 5:
                continue
            
            # Check for too short answers
            if len(card["answer"]) < 2:
                continue
            
            valid_cards.append(card)
        
        return valid_cards
    
    def _generate_cards_from_sections(self, sections: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """Generate cards directly from section text (fallback method)"""
        import re
        cards = []
        card_id = 0
        
        for section in sections[:5]:  # Limit to first 5 sections
            text = section.get("text", "")
            sec_id = section.get("sec_id", "")
            
            if len(text) < 20:
                continue
            
            # Method 1: Extract sentences with key verbs
            sentences = re.split(r'[。！？]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 15 or len(sentence) > 100:
                    continue
                
                # Look for informative sentences (containing 是/为/有/能/可以等)
                if any(keyword in sentence for keyword in ['是', '为', '有', '能', '可以', '包括', '分为', '用于', '通过']):
                    # Generate cloze by blanking a key term
                    words = re.findall(r'[\u4e00-\u9fa5]{2,8}', sentence)
                    if len(words) >= 3:
                        # Blank out a middle word
                        key_word = words[len(words)//2]
                        if key_word not in ['但是', '如果', '因为', '所以', '可以', '这个', '那个']:
                            stem = sentence.replace(key_word, '____', 1)
                            
                            cards.append({
                                "card_id": f"{doc_id}_sc{card_id}",
                                "doc_id": doc_id,  # 添加缺失的doc_id字段
                                "type": "cloze",
                                "stem": stem,
                                "choices": [],
                                "answer": key_word,
                                "explanation": f"原句：{sentence}",
                                "source_ref": sec_id,
                                "concept_refs": [],
                                "difficulty": "M"
                            })
                            card_id += 1
                            
                            if card_id >= 10:  # Limit total cards
                                break
            
            # Method 2: Generate comprehension questions
            if len(text) >= 30 and card_id < 5:
                # Extract first meaningful sentence
                first_sentence = re.split(r'[。！？]', text)[0].strip()
                if len(first_sentence) >= 15:
                    cards.append({
                        "card_id": f"{doc_id}_sc{card_id}",
                        "doc_id": doc_id,  # 添加缺失的doc_id字段
                        "type": "short",
                        "stem": f"请简述：{section.get('title', '这段内容')}的主要内容。",
                        "choices": [],
                        "answer": text[:100],  # First 100 chars as reference answer
                        "explanation": f"参考答案：{text[:100]}",
                        "source_ref": sec_id,
                        "concept_refs": [],
                        "difficulty": "M"
                    })
                    card_id += 1
            
            if card_id >= 10:
                break
        
        return cards
    
    def _count_by_type(self, cards: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count cards by type"""
        counts = {"knowledge": 0, "cloze": 0, "mcq": 0, "short": 0}
        for card in cards:
            card_type = card.get("type", "unknown")
            if card_type in counts:
                counts[card_type] += 1
        return counts
    
    def _generate_knowledge_card_llm(self, concept: Dict[str, Any], doc_id: str) -> Optional[Dict[str, Any]]:
        """使用LLM生成知识记忆卡片（正面：问题/概念，背面：答案/解释）"""
        if not self.llm or not self.llm.is_available():
            return None
        
        term = concept.get("term", "")
        definition = concept.get("definition", "")
        
        if not term or not definition:
            return None
        
        try:
            system_prompt = """你是出题专家。生成知识记忆卡片，用于帮助学习者记忆知识点。
输出JSON格式：
{
  "front": "正面内容（概念名称或问题）",
  "back": "背面内容（定义、解释或答案）",
  "hint": "提示（可选，帮助记忆）",
  "example": "例子（可选）"
}

要求：
1. front要简洁，通常是概念名称或"什么是X？"
2. back要完整准确，包含核心定义
3. hint提供记忆技巧或关键词
4. example提供具体例子"""

            prompt = f"概念：{term}\n定义：{definition}\n\n请生成一张知识记忆卡片。"
            
            response = self.llm.generate(prompt, system_prompt, temperature=0.5, max_tokens=500)
            
            if not response:
                return None
            
            # 解析JSON
            import json
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            card_data = json.loads(response)
            
            # 构建知识卡片
            card = {
                "card_id": f"{doc_id}_{concept['cid']}_knowledge",
                "doc_id": doc_id,
                "type": "knowledge",
                "stem": card_data.get("front", term),
                "answer": card_data.get("back", definition),
                "choices": [],
                "explanation": f"提示：{card_data.get('hint', '')}\n例子：{card_data.get('example', '')}".strip(),
                "source_ref": concept.get("refs", [""])[0],
                "concept_refs": [concept["cid"]],
                "difficulty": "M"
            }
            
            self.logger.info(f"Generated knowledge card using LLM for: {term}")
            return card
            
        except Exception as e:
            self.logger.error(f"LLM knowledge card generation failed: {e}")
            return None
    
    def _generate_cards_batch_llm(self, concept: Dict[str, Any], doc_id: str) -> List[Dict[str, Any]]:
        """使用LLM批量生成多张卡片（一次调用，提速）"""
        if not self.llm or not self.llm.is_available():
            return []
        
        term = concept.get("term", "")
        definition = concept.get("definition", "")
        
        if not term or not definition:
            return []
        
        try:
            system_prompt = """你是出题专家。根据给定概念一次性生成3种类型的学习卡片。
输出JSON数组格式（必须是合法的JSON，不要有额外文字）：
[
  {
    "type": "knowledge",
    "front": "正面（概念或问题）",
    "back": "背面（定义或答案）",
    "hint": "记忆提示",
    "example": "例子"
  },
  {
    "type": "cloze",
    "stem": "题干（用____表示空白）",
    "answer": "答案",
    "explanation": "解释"
  },
  {
    "type": "mcq",
    "stem": "题干",
    "choices": ["选项A", "选项B", "选项C", "选项D"],
    "answer": "正确答案",
    "explanation": "解释"
  }
]

要求：
1. knowledge卡片：简洁的正反面，便于记忆
2. cloze卡片：挖空关键信息
3. mcq卡片：干扰项合理、同类型、同难度
4. 只输出JSON，不要有其他文字"""

            prompt = f"概念：{term}\n定义：{definition}\n\n请一次性生成3张卡片（knowledge、cloze、mcq）。只输出JSON数组，不要有任何其他文字。"
            
            response = self.llm.generate(prompt, system_prompt, temperature=0.7, max_tokens=1500)
            
            if not response:
                self.logger.warning(f"LLM returned empty response for: {term}")
                return self._fallback_generate_cards(concept, doc_id)
            
            # 解析JSON - 增强鲁棒性
            import json
            import re
            
            # 清理响应
            response = response.strip()
            
            # 移除markdown代码块标记
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 尝试提取JSON数组（如果有额外文字）
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                response = json_match.group(0)
            
            # 解析JSON
            try:
                cards_data = json.loads(response)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败 for '{term}': {e}")
                self.logger.debug(f"原始响应: {response[:200]}...")
                # 使用fallback方法
                return self._fallback_generate_cards(concept, doc_id)
            
            # 构建卡片列表
            cards = []
            for idx, card_data in enumerate(cards_data):
                card_type = card_data.get("type", "unknown")
                
                if card_type == "knowledge":
                    card = {
                        "card_id": f"{doc_id}_{concept['cid']}_knowledge",
                        "doc_id": doc_id,
                        "type": "knowledge",
                        "stem": card_data.get("front", term),
                        "answer": card_data.get("back", definition),
                        "choices": [],
                        "explanation": f"提示：{card_data.get('hint', '')}\n例子：{card_data.get('example', '')}".strip(),
                        "source_ref": concept.get("refs", [""])[0],
                        "concept_refs": [concept["cid"]],
                        "difficulty": "M"
                    }
                elif card_type == "cloze":
                    card = {
                        "card_id": f"{doc_id}_{concept['cid']}_cloze_llm",
                        "doc_id": doc_id,
                        "type": "cloze",
                        "stem": card_data.get("stem", ""),
                        "answer": card_data.get("answer", ""),
                        "choices": [],
                        "explanation": card_data.get("explanation", ""),
                        "source_ref": concept.get("refs", [""])[0],
                        "concept_refs": [concept["cid"]],
                        "difficulty": "M"
                    }
                elif card_type == "mcq":
                    card = {
                        "card_id": f"{doc_id}_{concept['cid']}_mcq_llm",
                        "doc_id": doc_id,
                        "type": "mcq",
                        "stem": card_data.get("stem", ""),
                        "answer": card_data.get("answer", ""),
                        "choices": card_data.get("choices", []),
                        "explanation": card_data.get("explanation", ""),
                        "source_ref": concept.get("refs", [""])[0],
                        "concept_refs": [concept["cid"]],
                        "difficulty": "M"
                    }
                else:
                    continue
                
                cards.append(card)
            
            self.logger.info(f"Batch generated {len(cards)} cards using LLM for: {term}")
            return cards
            
        except Exception as e:
            self.logger.error(f"LLM batch card generation failed for '{term}': {e}")
            # 使用fallback方法
            return self._fallback_generate_cards(concept, doc_id)
    
    def _fallback_generate_cards(self, concept: Dict[str, Any], doc_id: str) -> List[Dict[str, Any]]:
        """当LLM失败时的fallback方法 - 使用规则生成"""
        self.logger.info(f"Using fallback rule-based generation for: {concept.get('term', 'unknown')}")
        
        cards = []
        
        # 生成cloze卡片
        cloze_card = self._generate_cloze(concept, doc_id)
        if cloze_card:
            cards.append(cloze_card)
        
        # 生成MCQ卡片（使用简化版本）
        term = concept.get("term", "")
        definition = concept.get("definition", "")
        
        if term and definition:
            # 简单的MCQ
            mcq_card = {
                "card_id": f"{doc_id}_{concept['cid']}_mcq_fallback",
                "doc_id": doc_id,
                "type": "mcq",
                "stem": f"关于{term}，以下哪个描述是正确的？",
                "choices": [
                    definition,
                    "一种数据结构",
                    "一种算法",
                    "一种编程技术"
                ],
                "answer": definition,
                "explanation": f"{term}是指{definition}",
                "source_ref": concept.get("refs", [""])[0],
                "concept_refs": [concept["cid"]],
                "difficulty": "M"
            }
            cards.append(mcq_card)
        
        return cards
    
    def _generate_cards_concurrent(self, concepts: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """并发生成卡片 - 大幅提速"""
        cards = []
        failed_concepts = []
        
        # 使用线程池并发调用LLM
        max_workers = min(5, len(concepts))  # 减少并发数避免API限流
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建任务
            future_to_concept = {
                executor.submit(self._generate_cards_batch_llm, concept, doc_id): concept
                for concept in concepts
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_concept):
                concept = future_to_concept[future]
                term = concept.get('term', 'unknown')
                
                try:
                    batch_cards = future.result(timeout=60)  # 增加到60秒超时
                    if batch_cards:
                        cards.extend(batch_cards)
                        self.logger.info(f"✅ 成功生成 {len(batch_cards)} 张卡片 for: {term}")
                    else:
                        self.logger.warning(f"⚠️ LLM返回空结果 for: {term}")
                        failed_concepts.append(concept)
                except concurrent.futures.TimeoutError:
                    self.logger.warning(f"⏰ 超时 for: {term}, 将使用fallback")
                    failed_concepts.append(concept)
                except Exception as e:
                    self.logger.error(f"❌ 生成失败 for '{term}': {str(e)[:100]}")
                    failed_concepts.append(concept)
        
        # 对失败的概念使用fallback方法
        if failed_concepts:
            self.logger.info(f"📝 使用fallback方法处理 {len(failed_concepts)} 个失败的概念")
            for concept in failed_concepts:
                fallback_cards = self._fallback_generate_cards(concept, doc_id)
                cards.extend(fallback_cards)
        
        self.logger.info(f"✨ 并发生成完成: {len(cards)} 张卡片来自 {len(concepts)} 个概念")
        return cards
    
    def _generate_card_llm(self, concept: Dict[str, Any], doc_id: str, card_type: str) -> Optional[Dict[str, Any]]:
        """使用LLM生成特定类型的卡片"""
        if not self.llm or not self.llm.is_available():
            return None
        
        term = concept.get("term", "")
        definition = concept.get("definition", "")
        
        if not term or not definition:
            return None
        
        try:
            if card_type == "cloze":
                system_prompt = """你是出题专家。根据概念生成填空题。
输出JSON格式：
{
  "stem": "题干（用____表示空白）",
  "answer": "答案",
  "explanation": "解释"
}

要求：
1. 题干要完整，挖空处要关键
2. 答案要准确
3. 解释要清晰"""
                
            elif card_type == "mcq":
                system_prompt = """你是出题专家。根据概念生成选择题。
输出JSON格式：
{
  "stem": "题干",
  "choices": ["选项A", "选项B", "选项C", "选项D"],
  "answer": "正确答案（与choices中某项完全一致）",
  "explanation": "解释为什么这个答案是对的"
}

要求：
1. 题干要清晰完整
2. 干扰项要合理但明确错误
3. 干扰项要与正确答案同类型、同难度
4. 避免"以上都是"或"以上都不是"的选项"""
                
            else:
                return None
            
            prompt = f"概念：{term}\n定义：{definition}\n\n请生成一道{card_type}题。"
            
            response = self.llm.generate(prompt, system_prompt, temperature=0.7, max_tokens=800)
            
            if not response:
                return None
            
            # 解析JSON
            import json
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            card_data = json.loads(response)
            
            # 构建卡片
            card = {
                "card_id": f"{doc_id}_{concept['cid']}_{card_type}_llm",
                "doc_id": doc_id,
                "type": card_type,
                "stem": card_data.get("stem", ""),
                "answer": card_data.get("answer", ""),
                "choices": card_data.get("choices", []),
                "explanation": card_data.get("explanation", ""),
                "source_ref": concept.get("refs", [""])[0],
                "concept_refs": [concept["cid"]],
                "difficulty": "M"
            }
            
            self.logger.info(f"Generated {card_type} card using LLM for: {term}")
            return card
            
        except Exception as e:
            self.logger.error(f"LLM {card_type} card generation failed: {e}")
            return None

