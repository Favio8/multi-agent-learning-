"""
LLM Helper - 大模型API集成
支持多种LLM提供商：OpenAI, 智谱AI, 通义千问, DeepSeek等
"""

from typing import Dict, Any, List, Optional
import json
import logging
import os


class LLMHelper:
    """大模型辅助类"""
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, 
                 model: str = None, base_url: Optional[str] = None):
        """
        初始化LLM Helper
        
        Args:
            provider: 提供商 (openai, zhipu, qwen, deepseek, local)
            api_key: API密钥
            model: 模型名称
            base_url: API基础URL（可选）
        """
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.base_url = base_url
        self.logger = logging.getLogger("nlp.LLMHelper")
        
        # 设置默认模型
        if model:
            self.model = model
        else:
            self.model = self._get_default_model()
        
        # 初始化客户端
        self.client = None
        if self.api_key:
            self._init_client()
        else:
            self.logger.warning(f"No API key found for {provider}, LLM features disabled")
    
    def _get_default_model(self) -> str:
        """获取默认模型名称"""
        defaults = {
            "openai": "gpt-3.5-turbo",
            "zhipu": "glm-4",
            "qwen": "qwen-turbo",
            "deepseek": "deepseek-chat",
            "local": "local-model"
        }
        return defaults.get(self.provider, "gpt-3.5-turbo")
    
    def _init_client(self):
        """初始化API客户端"""
        try:
            if self.provider == "openai":
                from openai import OpenAI
                if self.base_url:
                    self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                else:
                    self.client = OpenAI(api_key=self.api_key)
                self.logger.info(f"OpenAI client initialized with model: {self.model}")
                
            elif self.provider == "zhipu":
                # 智谱AI - 使用OpenAI兼容接口
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://open.bigmodel.cn/api/paas/v4/"
                )
                self.logger.info(f"Zhipu AI client initialized with model: {self.model}")
                
            elif self.provider == "deepseek":
                # DeepSeek - OpenAI兼容
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
                self.logger.info(f"DeepSeek client initialized with model: {self.model}")
                
            else:
                self.logger.warning(f"Provider {self.provider} not fully supported yet")
                
        except ImportError:
            self.logger.error("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM client: {e}")
    
    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return self.client is not None
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            生成的文本，失败返回None
        """
        if not self.is_available():
            self.logger.warning("LLM not available, returning None")
            return None
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            self.logger.info(f"LLM generated response, length: {len(result)}")
            return result
            
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return None
    
    def extract_concepts(self, text: str) -> List[Dict[str, str]]:
        """
        使用LLM提取概念
        
        Args:
            text: 输入文本
            
        Returns:
            概念列表 [{"term": "...", "definition": "..."}]
        """
        if not self.is_available():
            return []
        
        system_prompt = """你是一个专业的知识提取专家。
从给定文本中提取关键概念和定义。
以JSON格式输出，格式如下：
[{"term": "概念名称", "definition": "概念定义"}]

要求：
1. 只提取文本中明确提到的概念
2. 定义要准确、完整
3. 每个概念2-20字，定义5-200字
4. 提取5-15个最重要的概念"""

        prompt = f"请从以下文本中提取关键概念：\n\n{text}"
        
        response = self.generate(prompt, system_prompt, temperature=0.3, max_tokens=1500)
        
        if not response:
            return []
        
        try:
            # 尝试解析JSON
            # 可能需要清理响应文本
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            concepts = json.loads(response)
            self.logger.info(f"Extracted {len(concepts)} concepts using LLM")
            return concepts
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:200]}")
            return []
    
    def generate_quiz_card(self, concept: Dict[str, str], card_type: str = "cloze") -> Optional[Dict]:
        """
        使用LLM生成卡片
        
        Args:
            concept: 概念字典 {"term": "...", "definition": "..."}
            card_type: 卡片类型 (cloze, mcq, short)
            
        Returns:
            卡片字典
        """
        if not self.is_available():
            return None
        
        term = concept.get("term", "")
        definition = concept.get("definition", "")
        
        if card_type == "cloze":
            system_prompt = """你是出题专家。根据概念生成填空题。
输出JSON格式：{"stem": "题干（用____表示空白）", "answer": "答案", "explanation": "解释"}"""
            
            prompt = f"概念：{term}\n定义：{definition}\n\n请生成一道填空题。"
            
        elif card_type == "mcq":
            system_prompt = """你是出题专家。根据概念生成选择题。
输出JSON格式：{"stem": "题干", "choices": ["选项A", "选项B", "选项C", "选项D"], "answer": "正确答案", "explanation": "解释"}
要求：干扰项要合理但明确错误。"""
            
            prompt = f"概念：{term}\n定义：{definition}\n\n请生成一道选择题。"
            
        else:  # short
            system_prompt = """你是出题专家。根据概念生成简答题。
输出JSON格式：{"stem": "问题", "answer": "参考答案", "explanation": "评分要点"}"""
            
            prompt = f"概念：{term}\n定义：{definition}\n\n请生成一道简答题。"
        
        response = self.generate(prompt, system_prompt, temperature=0.7, max_tokens=800)
        
        if not response:
            return None
        
        try:
            # 清理并解析JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            card = json.loads(response)
            card["type"] = card_type
            self.logger.info(f"Generated {card_type} card using LLM")
            return card
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse card JSON: {e}")
            return None
    
    def improve_text(self, text: str, task: str = "summarize") -> Optional[str]:
        """
        文本改进/总结
        
        Args:
            text: 输入文本
            task: 任务类型 (summarize, clarify, simplify)
            
        Returns:
            改进后的文本
        """
        if not self.is_available():
            return None
        
        tasks = {
            "summarize": "请总结以下内容的要点：",
            "clarify": "请用更清晰的语言重新表述以下内容：",
            "simplify": "请用简单的语言解释以下内容："
        }
        
        prompt = tasks.get(task, tasks["summarize"]) + f"\n\n{text}"
        
        return self.generate(prompt, temperature=0.5, max_tokens=1000)


# 全局LLM实例
_llm_instance = None


def get_llm(provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> LLMHelper:
    """
    获取全局LLM实例
    
    Args:
        provider: 提供商（首次调用时设置）
        api_key: API密钥（首次调用时设置）
        model: 模型名称（首次调用时设置）
        base_url: API地址（首次调用时设置）
    """
    global _llm_instance
    
    if _llm_instance is None:
        # 优先从配置文件读取
        if provider is None:
            try:
                import yaml
                with open("configs/settings.yaml", "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    llm_config = config.get("models", {}).get("llm", {})
                    
                    if llm_config.get("enabled", False):
                        provider = llm_config.get("provider", "openai")
                        api_key = api_key or llm_config.get("api_key")
                        model = model or llm_config.get("model_name")
                        base_url = base_url or llm_config.get("base_url")
            except Exception as e:
                logging.getLogger("nlp.llm_helper").warning(f"Failed to load LLM config: {e}")
        
        # 回退到环境变量
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        api_key = api_key or os.getenv("LLM_API_KEY")
        model = model or os.getenv("LLM_MODEL")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        
        _llm_instance = LLMHelper(provider=provider, api_key=api_key, model=model, base_url=base_url)
    
    return _llm_instance

