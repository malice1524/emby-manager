import asyncio
import json
import os
import re
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from fastapi import APIRouter, HTTPException

from ..settings_store import load_metube_settings

router = APIRouter(prefix="/api/pornhub-gap", tags=["pornhub-gap"])
VIDEO_EXTS={".mp4",".mkv",".mov",".avi",".webm",".m4v"}
IMAGE_EXTS={".jpg",".jpeg",".png",".webp"}
KEY_RE=re.compile(r"(?:ph)?([A-Za-z0-9]{11,16})(?=\.[^.]+$|$)")
DATE_RE=re.compile(r"^(\d{4}-\d{2}-\d{2})_")
PROXY=os.getenv("PORNHUB_PROXY","http://192.168.1.7:7890")
DOWNLOAD_DIR=Path(os.getenv("METUBE_DOWNLOAD_DIR","/downloads"))
CLOUD_ROOT=Path(os.getenv("CLOUD115_ROOT","/CloudDrive115")).resolve()
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"

def _safe_dir(value:str)->Path:
    p=Path(value).resolve()
    try:p.relative_to(CLOUD_ROOT)
    except ValueError:raise HTTPException(400,f"目录必须位于 {CLOUD_ROOT}")
    if not p.is_dir():raise HTTPException(404,"115 目录不存在")
    return p

def _norm_key(v:str)->str:return v[2:] if v.startswith("ph") else v

def _clean_html(v:str)->str:
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",unescape(v or ""))).strip()

def _safe_title(v:str)->str:
    v=re.sub(r"[/\\:*?\"<>|]+"," ",unescape(v or ""))
    return re.sub(r"\s+"," ",v).strip().strip(".")

def _file_title(name:str,key:str)->str:
    stem=Path(name).stem
    m=DATE_RE.match(stem)
    if m:stem=stem[m.end():]
    km=KEY_RE.search(name)
    if km:stem=stem[:max(0,len(stem)-len(km.group(0)))].strip("_-. ")
    return stem

def _norm_title(v:str)->str:return re.sub(r"[^a-z0-9]+","",unescape(v).lower())

def _profile_url(url:str)->str:
    u=urlparse(url.strip())
    host=(u.hostname or "").lower()
    if u.scheme not in {"http","https"} or (host!="pornhub.com" and not host.endswith(".pornhub.com")):raise HTTPException(400,"请输入 PornHub 网址")
    path=u.path.rstrip("/")
    if re.search(r"/(model|channels|users)/[^/]+$",path):path+="/videos"
    return urlunparse(("https",u.netloc,path,"",u.query,""))

async def _client():
    return httpx.AsyncClient(proxy=PROXY,timeout=35,follow_redirects=True,headers={"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9","Cookie":"platform=pc; age_verified=1"})

async def _fetch_text(client:httpx.AsyncClient,url:str)->str:
    r=await client.get(url);r.raise_for_status();return r.text

def _parse_page(html:str,base:str)->dict[str,dict[str,Any]]:
    start=html.find('<div id="profileContent"')
    body=html[start if start>=0 else 0:]
    out={}
    for m in re.finditer(r'<li\b(?=[^>]*pcVideoListItem)(.*?)(?=</li>)</li>',body,re.S|re.I):
        block=m.group(0)
        km=re.search(r'data-video-vkey="([A-Za-z0-9]+)"',block) or re.search(r'viewkey=([A-Za-z0-9]+)',block)
        tm=re.search(r'class="thumbnailTitle[^>]*"[^>]*>\s*(.*?)\s*</a>',block,re.S|re.I)
        if not km or not tm:continue
        raw=km.group(1);key=_norm_key(raw);title=_safe_title(_clean_html(tm.group(1)))
        if title:out[key]={"viewkey":raw,"key":key,"title":title,"url":f"https://www.pornhub.com/view_video.php?viewkey={raw}"}
    return out

async def _site_items(url:str)->list[dict[str,Any]]:
    base=_profile_url(url)
    async with await _client() as c:
        first=await _fetch_text(c,base)
        pages=max([1]+[int(x) for x in re.findall(r"[?&]page=(\d+)",first)])
        if pages>30:raise HTTPException(400,"分页数量异常")
        all_items=_parse_page(first,base)
        for page in range(2,pages+1):
            sep="&" if "?" in base else "?"
            all_items.update(_parse_page(await _fetch_text(c,f"{base}{sep}page={page}"),base))
    if not all_items:raise HTTPException(502,"未从 PornHub 页面读取到视频")
    return list(all_items.values())

def _scan(target:Path,site:list[dict[str,Any]])->dict[str,Any]:
    sm={x["key"]:x for x in site};videos={};images={};unkeyed=[]
    for p in target.iterdir():
        if not p.is_file() or p.suffix.lower() not in VIDEO_EXTS|IMAGE_EXTS:continue
        m=KEY_RE.search(p.name)
        if not m:unkeyed.append(p);continue
        key=_norm_key(m.group(1))
        (videos if p.suffix.lower() in VIDEO_EXTS else images).setdefault(key,[]).append(p)
    # Match files without viewkey by title only when one site title is clearly unique.
    unkeyed_matches={}
    for p in unkeyed:
        local_title=_file_title(p.name,"")
        scored=sorted(((SequenceMatcher(None,_norm_title(local_title),_norm_title(x["title"])).ratio(),k,x) for k,x in sm.items()),reverse=True,key=lambda row:row[0])
        if scored and scored[0][0]>=0.82 and (len(scored)==1 or scored[0][0]-scored[1][0]>=0.08):
            unkeyed_matches[p]=scored[0][2]
    matched_video_keys={item["key"] for p,item in unkeyed_matches.items() if p.suffix.lower() in VIDEO_EXTS}
    matched_image_keys={item["key"] for p,item in unkeyed_matches.items() if p.suffix.lower() in IMAGE_EXTS}
    missing_videos=[x for k,x in sm.items() if k not in videos and k not in matched_video_keys]
    missing_images=[]
    for k,x in sm.items():
        has_video=k in videos or k in matched_video_keys
        has_image=k in images or k in matched_image_keys
        if has_video and not has_image:
            source=(videos.get(k) or [p for p,item in unkeyed_matches.items() if item["key"]==k and p.suffix.lower() in VIDEO_EXTS])
            missing_images.append({**x,"video_file":source[0].name})
    name_issues=[]
    for k,x in sm.items():
        for p in videos.get(k,[])+images.get(k,[]):
            title=_file_title(p.name,k)
            kinds=[]
            if not DATE_RE.match(p.name):kinds.append("missing_date")
            if not title or set(title)<=set("_-. "):kinds.append("missing_title")
            if kinds:name_issues.append({"file":p.name,"key":k,"title":x["title"],"issues":kinds})
    for p in unkeyed:
        match=unkeyed_matches.get(p)
        kinds=["missing_viewkey"]
        title=_file_title(p.name,"")
        if not DATE_RE.match(p.name):kinds.append("missing_date")
        if not title or set(title)<=set("_-. "):kinds.append("missing_title")
        name_issues.append({"file":p.name,"key":match["key"] if match else "","title":match["title"] if match else "","viewkey":match["viewkey"] if match else "","issues":kinds,"auto_match":bool(match)})
    local_video_count=sum(len(v) for v in videos.values())+sum(1 for p in unkeyed_matches if p.suffix.lower() in VIDEO_EXTS)
    local_image_count=sum(len(v) for v in images.values())+sum(1 for p in unkeyed_matches if p.suffix.lower() in IMAGE_EXTS)
    return {"site_total":len(site),"local_videos":local_video_count,"local_images":local_image_count,"missing_videos":missing_videos,"missing_images":missing_images,"name_issues":name_issues}

async def _detail(client:httpx.AsyncClient,item:dict[str,Any])->dict[str,str]:
    html=await _fetch_text(client,item["url"])
    dm=re.search(r'"uploadDate"\s*:\s*"(\d{4}-\d{2}-\d{2})',html) or re.search(r'property="video:release_date"\s+content="(\d{4}-\d{2}-\d{2})',html)
    im=re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)',html,re.I)
    return {"date":dm.group(1) if dm else "","image":unescape(im.group(1)) if im else ""}

async def _metube_has_key(key:str)->bool:
    base=load_metube_settings()["url"].rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.get(f"{base}/history");r.raise_for_status()
            return key.lower() in json.dumps(r.json(),ensure_ascii=False).lower()
    except Exception:
        return False

async def _add_metube(url:str,key:str)->dict[str,Any]:
    if await _metube_has_key(key):return {"status":"skipped","msg":"MeTube 队列或历史中已存在"}
    base=load_metube_settings()["url"].rstrip("/")
    async with httpx.AsyncClient(timeout=90) as c:
        r=await c.post(f"{base}/add",json={"url":url});r.raise_for_status()
        try:return r.json()
        except Exception:return {"status":"error","msg":r.text[:500]}

@router.post("/check")
async def check(payload:dict[str,Any]):
    url=str(payload.get("url") or "").strip();target=_safe_dir(str(payload.get("target_dir") or ""))
    site=await _site_items(url);result=_scan(target,site);result.update({"url":_profile_url(url),"target_dir":str(target)})
    return result

@router.post("/fix")
async def fix(payload:dict[str,Any]):
    url=str(payload.get("url") or "").strip();target=_safe_dir(str(payload.get("target_dir") or ""))
    site=await _site_items(url);before=_scan(target,site);actions=[]
    for item in before["missing_videos"]:
        res=await _add_metube(item["url"],item["key"]);actions.append({"type":"video","key":item["key"],"ok":res.get("status") in {"ok","skipped"},"result":res})
    DOWNLOAD_DIR.mkdir(parents=True,exist_ok=True)
    async with await _client() as c:
        for item in before["missing_images"]:
            try:
                detail=await _detail(c,item);img=detail["image"]
                if not img:raise ValueError("未找到封面地址")
                r=await c.get(img,headers={"Referer":item["url"]});r.raise_for_status()
                if len(r.content)<10000:raise ValueError("封面文件过小")
                out=DOWNLOAD_DIR/(Path(item["video_file"]).stem+".jpg");out.write_bytes(r.content)
                actions.append({"type":"image","key":item["key"],"ok":True,"file":out.name})
            except Exception as e:actions.append({"type":"image","key":item["key"],"ok":False,"error":f"{type(e).__name__}: {e}"})
        by_key={x["key"]:x for x in site}
        detail_cache={}
        for issue in before["name_issues"]:
            if not issue["key"]:continue
            p=target/issue["file"];item=by_key.get(issue["key"])
            if not p.exists() or not item:continue
            if item["key"] not in detail_cache:
                try:detail_cache[item["key"]]=await _detail(c,item)
                except Exception:detail_cache[item["key"]]={"date":""}
            date=DATE_RE.match(p.name).group(1) if DATE_RE.match(p.name) else detail_cache[item["key"]].get("date","")
            if not date:
                actions.append({"type":"rename","file":p.name,"ok":False,"error":"无法确定发布日期"});continue
            rawkey=issue.get("viewkey") or item["viewkey"]
            safe_name=re.sub(r"\s+","_",item["title"])
            new=target/f"{date}_{safe_name}_{rawkey}{p.suffix.lower()}"
            if new.exists() and new!=p:actions.append({"type":"rename","file":p.name,"ok":False,"error":"目标文件已存在"});continue
            p.rename(new);actions.append({"type":"rename","file":p.name,"new_file":new.name,"ok":True})
    return {"before":before,"actions":actions,"queued_videos":sum(1 for x in actions if x["type"]=="video" and x["ok"]),"queued_images":sum(1 for x in actions if x["type"]=="image" and x["ok"]),"renamed":sum(1 for x in actions if x["type"]=="rename" and x["ok"]),"failed":sum(1 for x in actions if not x["ok"])}
