import os
import logging
from typing import Dict, List, Optional, Any
import json
import asyncio
from datetime import datetime
import httpx

from parser import SlideContent

logger = logging.getLogger(__name__)


class SimpleAgent:
    """简化的知识扩展智能体"""

    def __init__(self):
        self.api_key = "sk-xeajczsypmkihgqahpcsidmhyvgddyrnxyzpediquhhavvwa"
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V3.2-Exp"

        # 添加并发控制信号量
        self.semaphore = asyncio.Semaphore(2)  # 限制同时2个请求

        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=180.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

        logger.info("✅ 智能体初始化完成")

    # 在 agent.py 的 call_llm 方法中修改
    async def call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用LLM API"""
        try:
            logger.info(f"调用LLM API，消息长度: {len(str(messages))}")

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=600.0  # 明确设置超时时间
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"LLM调用成功，返回长度: {len(content)}")
                return content
            else:
                logger.error(f"API调用失败: {response.status_code}, {response.text}")
                return ""

        except httpx.TimeoutException:
            logger.error("LLM调用超时")
            return ""
        except Exception as e:
            logger.error(f"调用LLM失败: {str(e)}", exc_info=True)  # 添加详细信息
            return ""

    # 在 agent.py 的 expand_slide 方法中修改
    async def expand_slide(self, slide: SlideContent) -> Dict[str, Any]:
        """扩展单个幻灯片内容"""
        try:
            # 检查幻灯片是否有有效内容
            if not slide.title.strip() and not slide.content and not slide.bullet_points:
                logger.info(f"跳过空幻灯片: {slide.slide_number}")
                return {
                    "slide_number": slide.slide_number,
                    "title": slide.title,
                    "skipped": True,
                    "reason": "内容为空",
                    "expanded_at": datetime.now().isoformat()
                }

            logger.info(f"扩展幻灯片: {slide.slide_number} - {slide.title[:30]}")

            # 并行执行扩展任务
            tasks = [
                self._generate_explanation(slide),
                self._generate_examples(slide),
                self._generate_references(slide),
                self._generate_quiz(slide)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果...
            # 处理结果
            expanded_content = {
                "slide_number": slide.slide_number,
                "title": slide.title,
                "explanations": results[0] if not isinstance(results[0], Exception) else [],
                "examples": results[1] if not isinstance(results[1], Exception) else [],
                "references": results[2] if not isinstance(results[2], Exception) else [],
                "quiz_questions": results[3] if not isinstance(results[3], Exception) else [],
                "expanded_at": datetime.now().isoformat()
            }

            logger.info(f"✅ 幻灯片扩展完成: {slide.slide_number}")
            return expanded_content

        except Exception as e:
            logger.error(f"扩展幻灯片失败: {e}")
            return {
                "slide_number": slide.slide_number,
                "title": slide.title,
                "error": str(e)
            }

    async def expand_multiple_slides(self, slides: List[SlideContent]) -> List[Dict[str, Any]]:
        """扩展多个幻灯片"""
        tasks = [self.expand_slide(slide) for slide in slides]
        results = await asyncio.gather(*tasks)
        return results

    async def _generate_explanation(self, slide: SlideContent) -> List[Dict[str, str]]:
        """生成详细解释"""
        content_text = "\n".join(slide.content)
        bullet_text = "\n".join(slide.bullet_points) if slide.bullet_points else "无"

        messages = [
            {"role": "system", "content": """你是一位经验丰富的教师，擅长用简单易懂的方式解释复杂概念。
请根据PPT幻灯片内容，提供详细的解释说明。"""},
            {"role": "user", "content": f"""幻灯片内容：

标题：{slide.title}

主要内容：
{content_text}

项目符号：
{bullet_text}

请为这个幻灯片生成详细的解释，包括：
1. 核心概念的定义和说明
2. 基本原理和逻辑
3. 实际应用场景
4. 与其他知识的关联

请使用中文回复，确保解释清晰准确。"""}
        ]

        try:
            explanation = await self.call_llm(messages)

            if explanation:
                # 简单解析
                sections = explanation.split("\n\n")
                explanations = []

                for section in sections:
                    if section.strip():
                        explanations.append({
                            "concept": "核心概念",
                            "explanation": section.strip(),
                            "type": "general_explanation"
                        })

                return explanations if explanations else [{
                    "concept": "整体解释",
                    "explanation": explanation,
                    "type": "general_explanation"
                }]
            return []

        except Exception as e:
            logger.error(f"生成解释失败: {e}")
            return []

    async def _generate_examples(self, slide: SlideContent) -> List[Dict[str, str]]:
        """生成代码/应用示例"""
        # 检查是否是技术相关的内容
        technical_keywords = ["代码", "编程", "算法", "函数", "类", "对象", "数据库", "网络", "协议"]

        slide_text = slide.title + " ".join(slide.content) + " ".join(slide.bullet_points)
        is_technical = any(keyword in slide_text for keyword in technical_keywords)

        if not is_technical:
            return []

        content_text = "\n".join(slide.content)

        messages = [
            {"role": "system", "content": "你是一位资深程序员和教育专家，擅长用示例解释技术概念。"},
            {"role": "user", "content": f"""根据以下幻灯片内容，生成相关的代码示例：

主题：{slide.title}
内容：{content_text}

请提供：
1. 一个完整的、可运行的代码示例
2. 详细的注释说明
3. 运行结果的说明
4. 实际应用场景

使用Python语言，确保代码规范和最佳实践。"""}
        ]

        try:
            example = await self.call_llm(messages)

            if example:
                return [{
                    "language": "python",
                    "code_example": example,
                    "description": "基于幻灯片内容生成的代码示例",
                    "type": "code_example"
                }]
            return []

        except Exception as e:
            logger.error(f"生成示例失败: {e}")
            return []

    async def _generate_references(self, slide: SlideContent) -> List[Dict[str, str]]:
        """生成参考资源"""
        keywords = ", ".join(self._extract_keywords_from_slide(slide))

        messages = [
            {"role": "system", "content": "你是一位学术研究助手，擅长查找权威的学习资源。"},
            {"role": "user", "content": f"""为以下学习主题推荐相关资源：

主题：{slide.title}
关键词：{keywords}

请推荐：
1. Wikipedia相关条目（中文或英文）
2. 相关书籍或教材
3. 在线教程或课程
4. 学术论文或研究报告

对于每个资源，请提供：
- 资源名称
- 简要描述
- 相关程度（高/中/低）"""}
        ]

        try:
            references = await self.call_llm(messages)

            if references:
                # 简单解析
                parsed_refs = []
                lines = references.split("\n")

                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("请推荐") and not line.startswith("对于每个"):
                        if "：" in line or ":" in line:
                            parts = line.split("：", 1) if "：" in line else line.split(":", 1)
                            if len(parts) == 2:
                                parsed_refs.append({
                                    "title": parts[0].strip(),
                                    "description": parts[1].strip(),
                                    "type": "reference"
                                })
                        else:
                            parsed_refs.append({
                                "title": line,
                                "description": "学习资源",
                                "type": "reference"
                            })

                return parsed_refs[:5]
            return []

        except Exception as e:
            logger.error(f"生成参考资源失败: {e}")
            return []

    async def _generate_quiz(self, slide: SlideContent) -> List[Dict[str, Any]]:
        """生成测验问题"""
        content_text = "\n".join(slide.content)

        messages = [
            {"role": "system", "content": "你是一位考试命题专家，擅长设计测试学生理解程度的问题。"},
            {"role": "user", "content": f"""根据以下学习内容，设计一个选择题：

内容主题：{slide.title}
详细内容：{content_text}

请设计：
1. 一个清晰明确的问题题干
2. 4个选项（A、B、C、D）
3. 正确答案（标注清楚）
4. 详细的答案解析

格式要求：
问题：[问题题干]
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]
答案：[正确选项，如A]
解析：[详细解析]"""}
        ]

        try:
            quiz = await self.call_llm(messages)

            if quiz:
                # 解析测验内容
                lines = quiz.split("\n")
                quiz_data = {
                    "question": "",
                    "options": {},
                    "answer": "",
                    "explanation": ""
                }

                for line in lines:
                    line = line.strip()
                    if line.startswith("问题："):
                        quiz_data["question"] = line[3:].strip()
                    elif line.startswith("A."):
                        quiz_data["options"]["A"] = line[2:].strip()
                    elif line.startswith("B."):
                        quiz_data["options"]["B"] = line[2:].strip()
                    elif line.startswith("C."):
                        quiz_data["options"]["C"] = line[2:].strip()
                    elif line.startswith("D."):
                        quiz_data["options"]["D"] = line[2:].strip()
                    elif line.startswith("答案："):
                        quiz_data["answer"] = line[3:].strip()
                    elif line.startswith("解析："):
                        quiz_data["explanation"] = line[3:].strip()

                return [quiz_data] if quiz_data["question"] else []
            return []

        except Exception as e:
            logger.error(f"生成测验失败: {e}")
            return []


    def _extract_keywords_from_slide(self, slide: SlideContent) -> List[str]:
        """从幻灯片中提取关键词"""
        keywords = set()

        # 从标题中提取
        title_words = slide.title.split()
        for word in title_words:
            if len(word) > 1:
                keywords.add(word)

        # 从内容中提取（简单实现）
        for content in slide.content:
            words = content.split()
            for word in words[:10]:  # 只取前10个词
                if len(word) > 2:
                    keywords.add(word)

        return list(keywords)[:5]  # 最多返回5个

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局智能体实例
knowledge_agent = SimpleAgent()