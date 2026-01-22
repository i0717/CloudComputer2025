from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import os
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
import logging

from config import settings
from parser import ppt_parser, SlideContent, PPTStructure, SlideStructure
from agent import knowledge_agent

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="PPT内容扩展智能体API",
    description="基于云原生和LLM的PPT内容扩展系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建上传目录
UPLOAD_DIR = Path(settings.upload_folder)
UPLOAD_DIR.mkdir(exist_ok=True)

# 内存存储（生产环境应使用数据库）
file_store = {}
expansion_results = {}
hierarchy_analysis_results = {}  # 新增：层级分析结果存储


# 数据模型
class PPTUploadRequest(BaseModel):
    description: Optional[str] = None


class SlideExpansionRequest(BaseModel):
    slide_numbers: List[int] = Field(default_factory=list)
    expansion_types: List[str] = Field(default_factory=lambda: ["explanation", "examples", "references", "quiz"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "PPT内容扩展智能体API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "上传PPT": "POST /api/upload",
            "获取文件列表": "GET /api/files",
            "获取文件详情": "GET /api/file/{file_id}",
            "扩展内容": "POST /api/expand/{file_id}",
            "按层级分析扩展": "POST /api/expand-by-hierarchy/{file_id}",  # 新增
            "下载结果": "GET /api/download/{file_id}",
            "搜索内容": "POST /api/search",
            "层级分析": "GET /api/hierarchy/{file_id}",
            "分析层级结构": "POST /api/analyze-hierarchy/{file_id}"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "parser": "ready",
            "agent": "ready",
            "storage": "ready"
        }
    }


@app.post("/api/upload")
async def upload_ppt(
        file: UploadFile = File(...),
        description: Optional[str] = None
):
    """上传PPT文件"""
    try:
        logger.info(f"收到上传请求: {file.filename}")

        # 验证文件类型
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.pptx', '.ppt', '.pdf']:
            raise HTTPException(status_code=400, detail="仅支持PPT、PPTX和PDF文件")

        # 生成文件ID
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        # 保存文件
        file_content = await file.read()
        if len(file_content) > settings.max_upload_size:
            raise HTTPException(status_code=400, detail="文件太大")

        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        logger.info(f"文件保存成功: {file_path}")

        # 解析PPT
        try:
            structure = ppt_parser.parse_pptx(str(file_path))

            # 保存解析结果
            json_path = UPLOAD_DIR / f"{file_id}_parsed.json"
            ppt_parser.save_to_json(structure, str(json_path))

            try:
                logger.info(f"开始向量索引: {file_id}")

                # 索引PPT内容
                indexed_count = vector_db.index_file(
                    file_id=file_id,
                    slides=structure.slides,
                    structures=structure.hierarchical_structure
                )

                if indexed_count > 0:
                    vector_indexed_files.add(file_id)
                    logger.info(f"✅ 向量索引完成: {indexed_count} 张幻灯片")
                else:
                    logger.warning(f"⚠️ 向量索引失败或没有内容可索引")

            except Exception as e:
                logger.error(f"❌ 向量索引失败: {e}")

            # 存储到内存
            file_store[file_id] = {
                "file_id": file_id,
                "original_filename": file.filename,
                "file_path": str(file_path),
                "json_path": str(json_path),
                "uploaded_at": datetime.now().isoformat(),
                "file_size": len(file_content),
                "description": description,
                "structure": structure.dict()
            }

            logger.info(f"PPT解析成功: {file_id}, {structure.metadata.total_slides} 张幻灯片")
            logger.info(f"层级结构分析完成: {len(structure.hierarchical_structure)} 个结构元素")

            return {
                "success": True,
                "file_id": file_id,
                "filename": file.filename,
                "total_slides": structure.metadata.total_slides,
                "outline": structure.outline[:10],  # 只返回前10条大纲
                "hierarchical_elements": len(structure.hierarchical_structure),
                "message": "文件上传和解析成功"
            }

        except Exception as e:
            logger.error(f"PPT解析失败: {e}")
            # 清理文件
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"PPT解析失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/api/files")
async def list_files():
    """获取文件列表"""
    files = []
    for file_id, file_info in file_store.items():
        files.append({
            "file_id": file_id,
            "filename": file_info["original_filename"],
            "uploaded_at": file_info["uploaded_at"],
            "total_slides": file_info["structure"]["metadata"]["total_slides"],
            "file_size": file_info["file_size"],
            "description": file_info.get("description"),
            "hierarchical_elements": len(file_info["structure"].get("hierarchical_structure", []))
        })

    # 按上传时间排序
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)

    return {"files": files}


@app.get("/api/file/{file_id}")
async def get_file_info(file_id: str):
    """获取文件详情"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_info = file_store[file_id]
    structure = PPTStructure(**file_info["structure"])

    return {
        "file_id": file_id,
        "filename": file_info["original_filename"],
        "uploaded_at": file_info["uploaded_at"],
        "file_size": file_info["file_size"],
        "description": file_info.get("description"),
        "structure": {
            "metadata": structure.metadata.dict(),
            "total_slides": structure.metadata.total_slides,
            "keywords": structure.keywords,
            "outline": structure.outline,
            "hierarchical_structure": [s.dict() for s in structure.hierarchical_structure]
        },
        "slides_preview": [
            {
                "slide_number": slide.slide_number,
                "title": slide.title,
                "content_preview": slide.content[0][:100] + "..." if slide.content else "",
                "level": slide.level
            }
            for slide in structure.slides[:10]  # 只返回前10张预览
        ]
    }


@app.get("/api/file/{file_id}/slide/{slide_number}")
async def get_slide_detail(file_id: str, slide_number: int):
    """获取单张幻灯片详情"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_info = file_store[file_id]
    structure = PPTStructure(**file_info["structure"])

    if slide_number < 0 or slide_number >= len(structure.slides):
        raise HTTPException(status_code=404, detail="幻灯片不存在")

    slide = structure.slides[slide_number]
    return slide.dict()


@app.post("/api/expand/{file_id}")
async def expand_slides(
        file_id: str,
        request: SlideExpansionRequest,
        background_tasks: BackgroundTasks
):
    """扩展幻灯片内容 - 添加校验"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        file_info = file_store[file_id]
        structure = PPTStructure(**file_info["structure"])

        # 确定要扩展的幻灯片
        if request.slide_numbers:
            slides_to_expand = [structure.slides[i] for i in request.slide_numbers
                                if 0 <= i < len(structure.slides)]
        else:
            # 默认扩展所有幻灯片，但限制数量
            slides_to_expand = structure.slides[:20]  # 限制最多20张

        if not slides_to_expand:
            raise HTTPException(status_code=400, detail="没有可扩展的幻灯片")

        # 检查幻灯片内容是否有效
        valid_slides = []
        for slide in slides_to_expand:
            if slide.title.strip() or slide.content or slide.bullet_points:
                valid_slides.append(slide)

        if not valid_slides:
            raise HTTPException(status_code=400, detail="所有选中的幻灯片内容都为空")

        logger.info(f"开始扩展 {len(valid_slides)} 张有效幻灯片")

        # 异步扩展
        expansion_task = asyncio.create_task(
            knowledge_agent.expand_multiple_slides(valid_slides)
        )

        # 等待扩展完成
        try:
            expanded_results = await asyncio.wait_for(
                expansion_task,
                timeout=600.0
            )

            # 校验扩展结果
            valid_results = []
            skipped_count = 0

            for result in expanded_results:
                if "error" in result or result.get("skipped"):
                    skipped_count += 1
                    logger.warning(
                        f"幻灯片 {result.get('slide_number')} 扩展失败或跳过: {result.get('error', result.get('reason', '未知原因'))}")
                else:
                    valid_results.append(result)

            logger.info(f"扩展完成: {len(valid_results)} 成功, {skipped_count} 跳过/失败")

        except asyncio.TimeoutError:
            logger.error(f"扩展任务超时")
            # 尝试取消任务
            expansion_task.cancel()
            try:
                await expansion_task
            except asyncio.CancelledError:
                pass
            raise HTTPException(status_code=408, detail="扩展任务超时，请减少幻灯片数量或重试")
        except Exception as e:
            logger.error(f"扩展任务异常: {e}")
            raise HTTPException(status_code=500, detail=f"扩展失败: {str(e)}")

        # 保存结果
        result_id = f"{file_id}_{int(datetime.now().timestamp())}"
        expansion_results[result_id] = {
            "file_id": file_id,
            "expanded_at": datetime.now().isoformat(),
            "total_slides": len(valid_slides),
            "successful_slides": len(valid_results),
            "skipped_slides": skipped_count,
            "slides": expanded_results
        }

        # 后台任务：保存到文件
        background_tasks.add_task(
            save_expansion_to_file,
            file_id,
            expanded_results,
            structure
        )

        return {
            "success": True,
            "result_id": result_id,
            "file_id": file_id,
            "total_expanded": len(valid_slides),
            "successful": len(valid_results),
            "skipped": skipped_count,
            "message": f"成功扩展 {len(valid_results)} 张幻灯片，跳过 {skipped_count} 张"
        }

    except Exception as e:
        logger.error(f"扩展失败: {e}")
        raise HTTPException(status_code=500, detail=f"扩展失败: {str(e)}")


@app.post("/api/expand-by-hierarchy/{file_id}")
async def expand_by_hierarchy(
        file_id: str,
        background_tasks: BackgroundTasks
):
    """根据层级分析结果扩展幻灯片内容（只扩展正文页）"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 获取层级分析结果
        hierarchy_response = hierarchy_analysis_results.get(file_id)
        if not hierarchy_response:
            # 尝试重新分析层级
            hierarchy_response = await analyze_hierarchical_structure_internal(file_id)
            if not hierarchy_response:
                raise HTTPException(status_code=400, detail="请先进行层级结构分析")

        # 从层级分析结果中提取正文页
        structure = hierarchy_response.get("structure", [])
        body_slides = []
        for item in structure:
            if item.get("content_type") == "正文":
                slide_num = item.get("slide_number", -1)
                if slide_num >= 0 and slide_num < len(file_store[file_id]["structure"]["slides"]):
                    # 获取实际的幻灯片内容
                    ppt_structure = PPTStructure(**file_store[file_id]["structure"])
                    if slide_num < len(ppt_structure.slides):
                        body_slides.append(ppt_structure.slides[slide_num])

        if not body_slides:
            raise HTTPException(status_code=400, detail="层级分析结果中没有找到正文页")

        logger.info(f"开始扩展 {len(body_slides)} 个正文页")

        # 扩展正文页
        expansion_task = asyncio.create_task(
            knowledge_agent.expand_multiple_slides(body_slides)
        )

        try:
            expanded_results = await asyncio.wait_for(
                expansion_task,
                timeout=600.0
            )
        except asyncio.TimeoutError:
            logger.error("扩展任务超时")
            expansion_task.cancel()
            try:
                await expansion_task
            except asyncio.CancelledError:
                pass
            raise HTTPException(status_code=408, detail="扩展任务超时，请稍后重试")
        except Exception as e:
            logger.error(f"扩展任务异常: {e}")
            raise HTTPException(status_code=500, detail=f"扩展失败: {str(e)}")

        # 保存结果
        result_id = f"{file_id}_hierarchy_{int(datetime.now().timestamp())}"
        expansion_results[result_id] = {
            "file_id": file_id,
            "expanded_at": datetime.now().isoformat(),
            "total_slides": len(expanded_results),
            "body_slides_count": len(body_slides),
            "expansion_type": "hierarchy_based",
            "slides": expanded_results
        }

        # 后台保存到文件
        file_info = file_store[file_id]
        structure = PPTStructure(**file_info["structure"])
        background_tasks.add_task(
            save_hierarchy_expansion_to_file,
            file_id,
            expanded_results,
            structure,
            hierarchy_response
        )

        return {
            "success": True,
            "result_id": result_id,
            "file_id": file_id,
            "total_body_slides": len(body_slides),
            "total_expanded": len(expanded_results),
            "expansion_type": "hierarchy_based",
            "message": f"成功扩展 {len(expanded_results)} 个正文页"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据层级分析扩展失败: {e}")
        raise HTTPException(status_code=500, detail=f"扩展失败: {str(e)}")


@app.get("/api/expansion/{result_id}")
async def get_expansion_result(result_id: str):
    """获取扩展结果"""
    if result_id not in expansion_results:
        raise HTTPException(status_code=404, detail="扩展结果不存在")

    return expansion_results[result_id]


@app.get("/api/download/{file_id}")
async def download_expanded_content(
        file_id: str,
        format: str = Query("markdown", regex="^(markdown|hierarchy_markdown|json|html)$")
):
    """下载扩展内容"""
    # 查找最新的扩展结果
    latest_result_id = None
    latest_time = None
    latest_expansion_type = None

    for result_id, result in expansion_results.items():
        if result["file_id"] == file_id:
            result_time = datetime.fromisoformat(result["expanded_at"])
            if latest_time is None or result_time > latest_time:
                latest_time = result_time
                latest_result_id = result_id
                latest_expansion_type = result.get("expansion_type", "normal")

    if not latest_result_id:
        raise HTTPException(status_code=404, detail="没有找到扩展结果")

    result = expansion_results[latest_result_id]

    if format == "json":
        # 返回JSON格式
        import json as json_module
        content = json_module.dumps(result, ensure_ascii=False, indent=2)
        return JSONResponse(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={file_id}_expanded.json"}
        )

    elif format in ["markdown", "hierarchy_markdown"]:
        # 生成Markdown文件
        if format == "hierarchy_markdown" and latest_expansion_type == "hierarchy_based":
            markdown_path = UPLOAD_DIR / f"{file_id}_hierarchy_expanded.md"
        else:
            markdown_path = UPLOAD_DIR / f"{file_id}_expanded.md"

        if not markdown_path.exists():
            # 如果没有缓存，重新生成
            if file_id in file_store:
                file_info = file_store[file_id]
                structure = PPTStructure(**file_info["structure"])

                if format == "hierarchy_markdown" and latest_expansion_type == "hierarchy_based":
                    # 获取层级分析结果
                    hierarchy_result = hierarchy_analysis_results.get(file_id, {})
                    await save_hierarchy_expansion_to_file(
                        file_id,
                        result["slides"],
                        structure,
                        hierarchy_result
                    )
                else:
                    await save_expansion_to_file(
                        file_id,
                        result["slides"],
                        structure
                    )
            else:
                # 如果没有文件信息，使用空结构
                await save_expansion_to_file(
                    file_id,
                    result["slides"],
                    None
                )

        filename = f"{file_id}_hierarchy_expanded.md" if format == "hierarchy_markdown" else f"{file_id}_expanded.md"
        return FileResponse(
            path=markdown_path,
            filename=filename,
            media_type="text/markdown"
        )

    else:
        raise HTTPException(status_code=400, detail="不支持的格式")


@app.post("/api/search")
async def search_content(request: SearchRequest):
    """搜索PPT内容"""
    try:
        # 简单的内存搜索（生产环境应使用向量数据库）
        search_results = []

        for file_id, file_info in file_store.items():
            structure = PPTStructure(**file_info["structure"])

            for slide in structure.slides:
                slide_text = f"{slide.title} {' '.join(slide.content)} {' '.join(slide.bullet_points)}"

                if request.query.lower() in slide_text.lower():
                    search_results.append({
                        "file_id": file_id,
                        "filename": file_info["original_filename"],
                        "slide_number": slide.slide_number,
                        "title": slide.title,
                        "content_preview": slide.content[0][:100] + "..." if slide.content else "",
                        "relevance": slide_text.lower().count(request.query.lower())
                    })

        # 按相关度排序
        search_results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "query": request.query,
            "total_results": len(search_results),
            "results": search_results[:request.limit]
        }

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.get("/api/hierarchy/{file_id}")
async def get_hierarchical_structure(file_id: str):
    """获取层级结构分析结果"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        file_info = file_store[file_id]
        structure = PPTStructure(**file_info["structure"])

        # 如果内存中有分析结果，直接返回
        if file_id in hierarchy_analysis_results:
            return hierarchy_analysis_results[file_id]

        # 否则从解析结果中提取
        hierarchical_structure = [s.dict() for s in structure.hierarchical_structure]

        result = {
            "file_id": file_id,
            "filename": file_info["original_filename"],
            "total_slides": structure.metadata.total_slides,
            "structure": hierarchical_structure,
            "analyzed_at": datetime.now().isoformat()
        }

        # 缓存结果
        hierarchy_analysis_results[file_id] = result

        return result

    except Exception as e:
        logger.error(f"获取层级结构失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取层级结构失败: {str(e)}")


@app.post("/api/analyze-hierarchy/{file_id}")
async def analyze_hierarchical_structure(file_id: str):
    """重新分析PPT的层级结构"""
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        file_info = file_store[file_id]
        file_path = file_info["file_path"]

        logger.info(f"重新分析层级结构: {file_id}")

        # 重新解析PPT
        structure = ppt_parser.parse_pptx(file_path)

        # 更新存储中的结构
        file_info["structure"] = structure.dict()
        file_store[file_id] = file_info

        # 保存更新后的解析结果
        json_path = UPLOAD_DIR / f"{file_id}_parsed.json"
        ppt_parser.save_to_json(structure, str(json_path))

        # 更新层级分析结果
        hierarchical_structure = [s.dict() for s in structure.hierarchical_structure]
        result = {
            "file_id": file_id,
            "filename": file_info["original_filename"],
            "total_slides": structure.metadata.total_slides,
            "structure": hierarchical_structure,
            "analyzed_at": datetime.now().isoformat()
        }

        hierarchy_analysis_results[file_id] = result

        logger.info(f"层级结构分析完成: {len(hierarchical_structure)} 个结构元素")

        return {
            "success": True,
            "message": f"成功分析 {len(hierarchical_structure)} 个结构元素",
            "result": result
        }

    except Exception as e:
        logger.error(f"层级结构分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"层级结构分析失败: {str(e)}")


async def analyze_hierarchical_structure_internal(file_id: str):
    """内部层级分析函数"""
    try:
        file_info = file_store[file_id]
        file_path = file_info["file_path"]

        # 解析PPT
        structure = ppt_parser.parse_pptx(file_path)

        # 更新存储中的结构
        file_info["structure"] = structure.dict()
        file_store[file_id] = file_info

        # 保存更新后的解析结果
        json_path = UPLOAD_DIR / f"{file_id}_parsed.json"
        ppt_parser.save_to_json(structure, str(json_path))

        # 创建层级分析结果
        hierarchical_structure = [s.dict() for s in structure.hierarchical_structure]
        result = {
            "file_id": file_id,
            "filename": file_info["original_filename"],
            "total_slides": structure.metadata.total_slides,
            "structure": hierarchical_structure,
            "analyzed_at": datetime.now().isoformat()
        }

        hierarchy_analysis_results[file_id] = result
        return result

    except Exception as e:
        logger.error(f"内部层级分析失败: {e}")
        return None


async def save_expansion_to_file(
        file_id: str,
        expanded_slides: List[Dict[str, Any]],
        structure: Optional[PPTStructure] = None
):
    """保存扩展结果到文件"""
    try:
        markdown_path = UPLOAD_DIR / f"{file_id}_expanded.md"

        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(f"# PPT内容扩展结果\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 如果有结构信息，添加更多元数据
            if structure:
                f.write(f"**原始文件**: {structure.metadata.filename}\n")
                f.write(f"**总幻灯片数**: {structure.metadata.total_slides}\n\n")

            for slide_result in expanded_slides:
                if "error" in slide_result:
                    continue

                f.write(f"## 幻灯片 {slide_result['slide_number'] + 1}: {slide_result['title']}\n\n")

                # 【修复1】清理重复的"详细解释"标题
                if "explanations" in slide_result and slide_result["explanations"]:
                    f.write("### 📚 详细解释\n\n")
                    for exp in slide_result["explanations"]:
                        # 避免重复显示概念标签
                        concept = exp.get('concept', '')
                        explanation = exp.get('explanation', '')

                        # 如果概念不是"详细解释"，才显示
                        if concept and concept not in ["详细解释", "基本解释", "解释"]:
                            f.write(f"**{concept}**\n\n")

                        f.write(f"{explanation}\n\n")

                # 【修复2】确保知识深度探索内容完整保存
                if "extended_readings" in slide_result and slide_result["extended_readings"]:
                    f.write("### 🧠 知识深度探索\n\n")
                    for reading in slide_result["extended_readings"]:
                        # 使用display_name或默认名称
                        display_name = reading.get('display_name', '知识深度探索')
                        f.write(f"#### {reading.get('title', display_name)}\n\n")

                        # 【关键修复】保存完整的知识深度探索内容
                        content = reading.get('content', '')
                        if content:
                            # 清理可能的重复标题
                            content_lines = content.split('\n')
                            cleaned_content = []
                            seen_headers = set(['知识深度探索', '知识深度扩展', '历史背景与发展',
                                                '实际应用案例', '前沿进展与趋势', '深入学习建议'])

                            for line in content_lines:
                                line_stripped = line.strip()
                                # 跳过重复的章节标题（后面会统一添加）
                                if any(header in line_stripped for header in seen_headers) and line_stripped.startswith(
                                        '#'):
                                    continue
                                cleaned_content.append(line)

                            f.write('\n'.join(cleaned_content))
                            f.write("\n\n")


                        # 如果有Wikipedia来源，显示出来
                        if reading.get('wikipedia_sources'):
                            f.write("**Wikipedia权威来源**:\n")
                            for source in reading.get('wikipedia_sources', [])[:3]:
                                title = source.get('title', '')
                                url = source.get('url', '')
                                description = source.get('description', '')
                                if title and url:
                                    f.write(f"- [{title}]({url}): {description[:80]}...\n")
                            f.write("\n")


                if "examples" in slide_result and slide_result["examples"]:
                    f.write("### 💻 代码示例\n")
                    for exp in slide_result["examples"]:
                        f.write(f"```{exp.get('language', 'python')}\n")
                        f.write(f"{exp.get('code_example', '')}\n")
                        f.write("```\n\n")

                if "references" in slide_result and slide_result["references"]:
                    f.write("### 📖 参考资源\n")
                    for ref in slide_result["references"]:
                        f.write(f"- **{ref.get('title', '资源')}**: {ref.get('description', '')}\n")
                    f.write("\n")

                if "quiz_questions" in slide_result and slide_result["quiz_questions"]:
                    f.write("### ❓ 测验问题\n")
                    for quiz in slide_result["quiz_questions"]:
                        f.write(f"**问题**: {quiz.get('question', '')}\n")
                        for opt_key, opt_value in quiz.get('options', {}).items():
                            f.write(f"{opt_key}. {opt_value}\n")
                        f.write(f"**答案**: {quiz.get('answer', '')}\n")
                        f.write(f"**解析**: {quiz.get('explanation', '')}\n\n")

                # 显示扩展质量信息
                if slide_result.get("validation_score") is not None:
                    score = slide_result["validation_score"]
                    if score >= 0.8:
                        quality = "✅ 优秀"
                    elif score >= 0.6:
                        quality = "⚠️ 良好"
                    else:
                        quality = "❌ 需要改进"

                    f.write(f"**扩展质量**: {quality} (得分: {score:.2f})\n")

                    # 显示校验摘要
                    if slide_result.get("validation_summary"):
                        validation = slide_result["validation_summary"]
                        if validation.get("extended_reading", {}).get("passed"):
                            f.write("**知识深度探索**: ✅ 已通过校验\n")
                        else:
                            f.write("**知识深度探索**: ⚠️ 使用默认内容\n")

                f.write("---\n\n")

        logger.info(f"扩展结果已保存: {markdown_path}")
        return True

    except Exception as e:
        logger.error(f"保存扩展结果失败: {e}")
        return False


async def save_hierarchy_expansion_to_file(
        file_id: str,
        expanded_slides: List[Dict[str, Any]],
        structure: PPTStructure,
        hierarchy_result: Dict[str, Any]
):
    """保存层级扩展结果到文件"""
    try:
        markdown_path = UPLOAD_DIR / f"{file_id}_hierarchy_expanded.md"

        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(f"# PPT正文页扩展结果（基于层级分析）\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 文件信息
            f.write(f"**原始文件**: {structure.metadata.filename}\n")
            f.write(f"**总幻灯片数**: {structure.metadata.total_slides}\n")
            f.write(f"**正文页数量**: {len(expanded_slides)}\n")
            f.write(f"**扩展类型**: 基于层级分析（只扩展正文页）\n\n")

            # 层级分析摘要
            if hierarchy_result and "structure" in hierarchy_result:
                total_structure = len(hierarchy_result["structure"])
                body_count = sum(1 for item in hierarchy_result["structure"]
                                 if item.get("content_type") == "正文")
                f.write("## 📊 层级分析摘要\n\n")
                f.write(f"- **总结构元素**: {total_structure}\n")
                f.write(f"- **正文页数量**: {body_count}\n")
                f.write(f"- **已扩展正文页**: {len(expanded_slides)}\n\n")

            f.write("## 📝 正文页扩展内容\n\n")

            for slide_result in expanded_slides:
                if "error" in slide_result or slide_result.get("skipped"):
                    continue

                f.write(f"### 正文页 {slide_result['slide_number'] + 1}: {slide_result['title']}\n\n")

                if "explanations" in slide_result and slide_result["explanations"]:
                    f.write("#### 📚 详细解释\n")
                    for exp in slide_result["explanations"]:
                        f.write(f"**{exp.get('concept', '概念')}**\n")
                        f.write(f"{exp.get('explanation', '')}\n\n")

                if "examples" in slide_result and slide_result["examples"]:
                    f.write("#### 💻 代码示例\n")
                    for exp in slide_result["examples"]:
                        f.write(f"```{exp.get('language', 'python')}\n")
                        f.write(f"{exp.get('code_example', '')}\n")
                        f.write("```\n\n")

                # ✅ 新增：知识深度探索部分（延伸阅读材料）
                if "extended_readings" in slide_result and slide_result["extended_readings"]:
                    f.write("#### 🧠 知识深度探索\n")  # ✅ 使用新名称
                    for reading in slide_result["extended_readings"]:
                        # 使用display_name或默认名称
                        display_name = reading.get('display_name', '知识深度探索')
                        f.write(f"**{reading.get('title', display_name)}**\n")
                        f.write(f"{reading.get('content', '')}\n\n")

                        # 如果有Wikipedia来源，显示出来
                        if reading.get('wikipedia_sources'):
                            f.write("**Wikipedia权威来源**:\n")
                            for source in reading.get('wikipedia_sources', [])[:2]:
                                f.write(
                                    f"- [{source.get('title', '')}]({source.get('url', '')}): {source.get('description', '')[:80]}...\n")
                            f.write("\n")

                if "references" in slide_result and slide_result["references"]:
                    f.write("#### 📖 参考资源\n")
                    for ref in slide_result["references"]:
                        f.write(f"- **{ref.get('title', '资源')}**: {ref.get('description', '')}\n")
                    f.write("\n")

                if "quiz_questions" in slide_result and slide_result["quiz_questions"]:
                    f.write("#### ❓ 测验问题\n")
                    for quiz in slide_result["quiz_questions"]:
                        f.write(f"**问题**: {quiz.get('question', '')}\n")
                        for opt_key, opt_value in quiz.get('options', {}).items():
                            f.write(f"{opt_key}. {opt_value}\n")
                        f.write(f"**答案**: {quiz.get('answer', '')}\n")
                        f.write(f"**解析**: {quiz.get('explanation', '')}\n\n")

                f.write("---\n\n")

        logger.info(f"层级扩展结果已保存: {markdown_path}")
        return True

    except Exception as e:
        logger.error(f"保存层级扩展结果失败: {e}")
        return False


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8010,
        reload=True
    )
