import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import pptx
from pptx import Presentation
from pydantic import BaseModel
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class SlideContent(BaseModel):
    """幻灯片内容模型"""
    slide_number: int
    title: str
    content: List[str]
    bullet_points: List[str]
    images: List[str]
    notes: str = ""
    level: int = 1


class PPTMetadata(BaseModel):
    """PPT元数据"""
    filename: str
    total_slides: int
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None


class PPTStructure(BaseModel):
    """PPT结构"""
    metadata: PPTMetadata
    slides: List[SlideContent]
    outline: List[str]
    keywords: List[str]


class PPTParser:
    """PPT解析器"""

    def __init__(self):
        self.slides = []
        self.outline = []

    def parse_pptx(self, file_path: str) -> PPTStructure:
        """解析PPT文件"""
        try:
            logger.info(f"开始解析PPT文件: {file_path}")

            # 加载PPT
            prs = Presentation(file_path)

            # 提取元数据
            metadata = self._extract_metadata(prs, file_path)

            # 解析幻灯片
            slides_content = []
            for i, slide in enumerate(prs.slides):
                slide_content = self._parse_slide(slide, i)
                slides_content.append(slide_content)

            # 提取大纲
            outline = self._extract_outline(slides_content)

            # 提取关键词
            keywords = self._extract_keywords(slides_content)

            # 构建结构
            structure = PPTStructure(
                metadata=metadata,
                slides=slides_content,
                outline=outline,
                keywords=keywords
            )

            logger.info(f"PPT解析完成: {len(slides_content)} 张幻灯片")
            return structure

        except Exception as e:
            logger.error(f"PPT解析失败: {e}")
            raise

    def _extract_metadata(self, presentation, file_path: str) -> PPTMetadata:
        """提取元数据"""
        try:
            # 获取核心属性
            core_props = presentation.core_properties

            return PPTMetadata(
                filename=Path(file_path).name,
                total_slides=len(presentation.slides),
                author=core_props.author,
                created_date=core_props.created.isoformat() if core_props.created else None,
                modified_date=core_props.modified.isoformat() if core_props.modified else None
            )
        except:
            # 如果提取失败，使用基本信息
            return PPTMetadata(
                filename=Path(file_path).name,
                total_slides=len(presentation.slides)
            )

    def _parse_slide(self, slide, slide_num: int) -> SlideContent:
        """解析单张幻灯片"""
        # 提取标题
        title = ""
        if slide.shapes.title:
            title = slide.shapes.title.text.strip()

        # 提取内容
        content = []
        bullet_points = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                text = shape.text.strip()
                if shape != slide.shapes.title:
                    # 检查是否为项目符号
                    if any(bullet in text[:10] for bullet in ["•", "◦", "▪", "‣", "⁃", "∙"]):
                        bullet_points.append(text)
                    else:
                        content.append(text)

        # 提取图片
        images = []
        for i, shape in enumerate(slide.shapes):
            if shape.shape_type == 13:  # 图片类型
                images.append(f"slide_{slide_num}_image_{i}")

        # 提取备注
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""

        # 确定层级
        level = self._determine_level(title, content)

        return SlideContent(
            slide_number=slide_num,
            title=title,
            content=content,
            bullet_points=bullet_points,
            images=images,
            notes=notes,
            level=level
        )

    def _determine_level(self, title: str, content: List[str]) -> int:
        """确定内容层级"""
        title_lower = title.lower()

        # 根据标题关键词判断层级
        if any(keyword in title_lower for keyword in ["章节", "chapter", "part", "单元", "module"]):
            return 1
        elif any(keyword in title_lower for keyword in ["节", "section", "小节", "subsection"]):
            return 2
        elif any(keyword in title_lower for keyword in ["标题", "标题"]):
            return 3
        else:
            return 4

    def _extract_outline(self, slides: List[SlideContent]) -> List[str]:
        """提取大纲"""
        outline = []
        for slide in slides:
            if slide.level <= 3:  # 只提取前三级标题
                indent = "  " * (slide.level - 1)
                outline.append(f"{indent}{slide.title}")
        return outline

    def _extract_keywords(self, slides: List[SlideContent]) -> List[str]:
        """提取关键词"""
        keywords = set()

        # 从标题中提取关键词
        for slide in slides:
            if slide.title:
                # 简单的关键词提取：按分隔符分割
                words = slide.title.replace("：", ":").split(":")
                for word in words:
                    if len(word.strip()) > 1:
                        keywords.add(word.strip())

        return list(keywords)[:10]  # 限制最多10个关键词

    def save_to_json(self, structure: PPTStructure, output_path: str):
        """保存解析结果到JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structure.dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"解析结果已保存: {output_path}")

    def load_from_json(self, json_path: str) -> PPTStructure:
        """从JSON文件加载解析结果"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return PPTStructure(**data)


# 单例解析器
ppt_parser = PPTParser()