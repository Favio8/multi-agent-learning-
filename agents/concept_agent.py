"""
ConceptAgent - Concept extraction, definition identification, and relation building
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent


class ConceptAgent(BaseAgent):
    """
    ConceptAgent extracts concepts and builds knowledge graph:
    - Extract terms, concepts, and formulas
    - Identify definitions
    - Extract relationships between concepts
    - Build lightweight knowledge graph
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="ConceptAgent", config=config)
        
        self.similarity_threshold = config.get("similarity_threshold", 0.85) if config else 0.85
        self.use_llm = config.get("use_llm", False) if config else False
        
        # 初始化LLM（如果启用）
        self.llm = None
        if self.use_llm:
            try:
                from nlp.llm_helper import get_llm
                self.llm = get_llm()
                if self.llm.is_available():
                    self.logger.info("LLM enabled for concept extraction")
                else:
                    self.logger.warning("LLM configured but not available")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM: {e}")
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract concepts and relations from sections
        
        Args:
            input_data: {
                "doc_id": str,
                "sections": [{"sec_id", "text", ...}],
                "language": str
            }
            
        Returns:
            {
                "doc_id": str,
                "concepts": [
                    {
                        "cid": str,
                        "term": str,
                        "aliases": [str],
                        "definition": str,
                        "refs": [str]  # section ids
                    }
                ],
                "relations": [
                    {
                        "src": str,  # concept id
                        "rel": str,  # relation type
                        "dst": str   # concept id
                    }
                ]
            }
        """
        self.validate_input(input_data, ["doc_id", "sections"])
        
        doc_id = input_data["doc_id"]
        sections = input_data["sections"]
        
        self.logger.info(f"Extracting concepts from {len(sections)} sections")
        
        # Extract concepts
        # Try LLM first if available, fallback to rule-based
        if self.llm and self.llm.is_available():
            self.logger.info("Using LLM for concept extraction")
            concepts = self._extract_concepts_llm(sections, doc_id)
            # Fallback to rule-based if LLM fails
            if not concepts:
                self.logger.warning("LLM extraction failed, using rule-based method")
                concepts = self._extract_concepts(sections, doc_id)
        else:
            concepts = self._extract_concepts(sections, doc_id)
        
        # Merge similar concepts
        concepts = self._merge_similar_concepts(concepts)
        
        # Extract relations
        relations = self._extract_relations(concepts, sections)
        
        result = {
            "doc_id": doc_id,
            "concepts": concepts,
            "relations": relations,
            "metadata": {
                "total_concepts": len(concepts),
                "total_relations": len(relations)
            }
        }
        
        self.log_audit(
            action="extract_concepts",
            input_summary=f"doc_id={doc_id}, {len(sections)} sections",
            output_summary=f"{len(concepts)} concepts, {len(relations)} relations"
        )
        
        return result
    
    def _extract_concepts(self, sections: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """Extract concepts from sections"""
        import re
        
        concepts = []
        concept_id = 0
        
        for section in sections:
            text = section["text"]
            sec_id = section["sec_id"]
            
            # Method 1: Definition pattern matching
            definition_patterns = [
                r'([^。，；\n]{2,20}?)(?:是|指|即|为|叫做|称为|定义为)([^。！？\n]{5,})',
                r'([^。，；\n]{2,20}?)[:：]([^。！？\n]{5,})',
                r'所谓([^。，；\n]{2,20})(?:是|指)?([^。！？\n]{5,})',
            ]
            
            for pattern in definition_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        term = groups[0].strip()
                        definition = groups[1].strip()
                        
                        # Filter noise
                        if (len(term) >= 2 and len(term) <= 30 and 
                            len(definition) >= 5 and len(definition) <= 200 and
                            not term.isdigit()):
                            
                            concepts.append({
                                "cid": f"{doc_id}_c{concept_id}",
                                "doc_id": doc_id,
                                "term": term,
                                "aliases": [],
                                "definition": definition,
                                "refs": [sec_id]
                            })
                            concept_id += 1
            
            # Method 2: Extract key noun phrases (fallback)
            # Look for capitalized words or words in quotes
            if concept_id < 3:  # If we haven't found enough concepts
                # Chinese: look for specialized terms in《》or「」
                special_terms = re.findall(r'[《「]([^》」]{2,15})[》」]', text)
                for term in special_terms:
                    # Use surrounding context as definition
                    context_pattern = f'.{{0,30}}{re.escape(term)}.{{0,50}}'
                    context_match = re.search(context_pattern, text)
                    definition = context_match.group(0) if context_match else text[:100]
                    
                    concepts.append({
                        "cid": f"{doc_id}_c{concept_id}",
                        "doc_id": doc_id,
                        "term": term,
                        "aliases": [],
                        "definition": definition,
                        "refs": [sec_id]
                    })
                    concept_id += 1
                
                # Extract potential key terms (2-6 characters, appears multiple times)
                words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
                word_freq = {}
                for word in words:
                    if word not in ['但是', '如果', '因为', '所以', '可以', '这个', '那个', '什么', '怎么']:
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Take top frequent terms as concepts
                for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]:
                    if freq >= 2 and concept_id < 10:  # Appears at least twice
                        # Use first occurrence context
                        context_pattern = f'.{{0,30}}{re.escape(word)}.{{0,50}}'
                        context_match = re.search(context_pattern, text)
                        definition = context_match.group(0) if context_match else text[:100]
                        
                        concepts.append({
                            "cid": f"{doc_id}_c{concept_id}",
                            "doc_id": doc_id,
                            "term": word,
                            "aliases": [],
                            "definition": definition.strip(),
                            "refs": [sec_id]
                        })
                        concept_id += 1
        
        return concepts
    
    def _extract_concepts_llm(self, sections: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """使用LLM提取概念"""
        if not self.llm:
            return []
        
        concepts = []
        concept_id = 0
        
        # 合并sections文本（限制长度）
        combined_text = ""
        for section in sections[:5]:  # 最多取5个section
            combined_text += section["text"] + "\n\n"
            if len(combined_text) > 2000:  # 限制总长度
                break
        
        if not combined_text.strip():
            return []
        
        # 使用LLM提取概念
        try:
            llm_concepts = self.llm.extract_concepts(combined_text)
            
            for llm_concept in llm_concepts:
                term = llm_concept.get("term", "").strip()
                definition = llm_concept.get("definition", "").strip()
                
                if term and definition:
                    concepts.append({
                        "cid": f"{doc_id}_c{concept_id}",
                        "doc_id": doc_id,
                        "term": term,
                        "aliases": [],
                        "definition": definition,
                        "refs": [sections[0]["sec_id"]] if sections else []
                    })
                    concept_id += 1
            
            self.logger.info(f"LLM extracted {len(concepts)} concepts")
        except Exception as e:
            self.logger.error(f"LLM concept extraction failed: {e}")
        
        return concepts
    
    def _merge_similar_concepts(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge concepts with similar terms"""
        # TODO: Use embeddings to find and merge similar concepts
        # For now, simple exact match after normalization
        
        merged = {}
        for concept in concepts:
            term_key = concept["term"].lower().strip()
            
            if term_key in merged:
                # Merge: combine refs and aliases
                merged[term_key]["refs"].extend(concept["refs"])
                merged[term_key]["refs"] = list(set(merged[term_key]["refs"]))
            else:
                merged[term_key] = concept
        
        return list(merged.values())
    
    def _extract_relations(self, concepts: List[Dict[str, Any]], 
                          sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships between concepts"""
        # TODO: Implement relation extraction:
        # - Co-occurrence in same section
        # - Dependency parsing
        # - LLM-based relation classification
        
        relations = []
        relation_id = 0
        
        # Simple co-occurrence based relations
        for section in sections:
            sec_id = section["sec_id"]
            text = section["text"].lower()
            
            # Find concepts mentioned in this section
            mentioned_concepts = [
                c for c in concepts 
                if c["term"].lower() in text
            ]
            
            # Create relations between co-occurring concepts
            for i, c1 in enumerate(mentioned_concepts):
                for c2 in mentioned_concepts[i+1:]:
                    relations.append({
                        "id": f"r{relation_id}",
                        "src": c1["cid"],
                        "rel": "related_to",
                        "dst": c2["cid"]
                    })
                    relation_id += 1
        
        return relations

