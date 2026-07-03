import os
import zipfile
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from ..tmdb_client import get_person_detail

router = APIRouter(prefix="/api/nfo", tags=["nfo"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def generate_nfo_xml(name: str, tmdb_id: int, thumb_filename: str) -> str:
    """生成演员 NFO XML 内容"""
    from xml.sax.saxutils import escape
    safe_name = escape(name)
    thumb_line = f"  <thumb>{escape(thumb_filename)}</thumb>\n" if thumb_filename else ""
    return f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<actor>
  <name>{safe_name}</name>
  <tmdbid>{tmdb_id}</tmdbid>
{thumb_line}</actor>
'''

@router.get("/person/{tmdb_id}")
async def get_person(tmdb_id: int):
    """查询演员信息"""
    person = await get_person_detail(tmdb_id)
    if "error" in person:
        raise HTTPException(status_code=400, detail=person["error"])
    return person

@router.post("/generate")
async def generate_nfo(
    background_tasks: BackgroundTasks,
    filename: str = Form(...),
    tmdb_id: int = Form(...),
    thumb: UploadFile = File(None)
):
    """生成演员 NFO 文件 + 封面图，返回 zip 下载"""
    # 0. 校验必填参数
    safe_filename = filename.strip().replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
    if not safe_filename:
        raise HTTPException(status_code=400, detail="文件名称不能为空")

    # 1. 查询 TMDB 演员信息
    person = await get_person_detail(tmdb_id)
    if "error" in person:
        raise HTTPException(status_code=400, detail=person["error"])

    actor_name = person["name"]
    profile_url = person.get("profile_url", "")

    # 2. 处理封面图扩展名
    thumb_ext = ".jpg"
    if thumb and thumb.filename:
        _, ext = os.path.splitext(thumb.filename)
        ext = ext.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}，仅支持 jpg/png/webp")
        thumb_ext = ext

    thumb_filename = f"{safe_filename}{thumb_ext}"

    # 3. 在临时目录生成文件
    tmp_dir = tempfile.mkdtemp()
    try:
        # 封面图：优先用上传的，没有则从 TMDB 下载头像
        thumb_path = os.path.join(tmp_dir, thumb_filename)
        has_thumb = False
        if thumb and thumb.filename:
            content = await thumb.read()
            if content:
                with open(thumb_path, "wb") as f:
                    f.write(content)
                has_thumb = True
        elif profile_url:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(profile_url)
                if resp.status_code == 200:
                    with open(thumb_path, "wb") as f:
                        f.write(resp.content)
                    has_thumb = True

        # NFO 文件（需要在 has_thumb 确定之后生成）
        nfo_content = generate_nfo_xml(actor_name, tmdb_id, thumb_filename if has_thumb else "")
        nfo_path = os.path.join(tmp_dir, f"{safe_filename}.nfo")
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        # 4. 打包 zip
        zip_path = os.path.join(tmp_dir, f"{safe_filename}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(nfo_path, f"{safe_filename}.nfo")
            if has_thumb and os.path.exists(thumb_path):
                zf.write(thumb_path, thumb_filename)

        # 5. 后台任务清理临时目录
        background_tasks.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)

        # 6. 返回下载
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{safe_filename}.zip"
        )
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
