from pathlib import Path
from typing import List, Any

from fastapi import APIRouter, Depends

from app import schemas
from app.chain.media import MediaChain
from app.core.config import settings
from app.core.context import Context
from app.core.metainfo import MetaInfo, MetaInfoPath
from app.core.security import verify_token, verify_uri_token
from app.schemas import MediaType

router = APIRouter()


@router.get("/recognize", summary="识别媒体信息（种子）", response_model=schemas.Context)
def recognize(title: str,
              subtitle: str = None,
              _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据标题、副标题识别媒体信息
    """
    # 识别媒体信息
    metainfo = MetaInfo(title, subtitle)
    mediainfo = MediaChain().recognize_by_meta(metainfo)
    if mediainfo:
        return Context(meta_info=metainfo, media_info=mediainfo).to_dict()
    return schemas.Context()


@router.get("/recognize2", summary="识别种子媒体信息（API_TOKEN）", response_model=schemas.Context)
def recognize2(title: str,
               subtitle: str = None,
               _: str = Depends(verify_uri_token)) -> Any:
    """
    根据标题、副标题识别媒体信息 API_TOKEN认证（?token=xxx）
    """
    # 识别媒体信息
    return recognize(title, subtitle)


@router.get("/recognize_file", summary="识别媒体信息（文件）", response_model=schemas.Context)
def recognize_file(path: str,
                   _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据文件路径识别媒体信息
    """
    # 识别媒体信息
    context = MediaChain().recognize_by_path(path)
    if context:
        return context.to_dict()
    return schemas.Context()


@router.get("/recognize_file2", summary="识别文件媒体信息（API_TOKEN）", response_model=schemas.Context)
def recognize_file2(path: str,
                    _: str = Depends(verify_uri_token)) -> Any:
    """
    根据文件路径识别媒体信息 API_TOKEN认证（?token=xxx）
    """
    # 识别媒体信息
    return recognize_file(path)


@router.get("/search", summary="搜索媒体信息", response_model=List[schemas.MediaInfo])
def search_by_title(title: str,
                    page: int = 1,
                    count: int = 8,
                    _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    模糊搜索媒体信息列表
    """
    _, medias = MediaChain().search(title=title)
    if medias:
        return [media.to_dict() for media in medias[(page - 1) * count: page * count]]
    return []


@router.get("/scrape", summary="刮削媒体信息", response_model=schemas.Response)
def scrape(path: str,
           _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    刮削媒体信息
    """
    if not path:
        return schemas.Response(success=False, message="刮削路径无效")
    scrape_path = Path(path)
    if not scrape_path.exists():
        return schemas.Response(success=False, message="刮削路径不存在")
    # 识别
    chain = MediaChain()
    meta = MetaInfoPath(scrape_path)
    mediainfo = chain.recognize_media(meta)
    if not media_info:
        return schemas.Response(success=False, message="刮削失败，无法识别媒体信息")
    # 刮削
    chain.scrape_metadata(path=scrape_path, mediainfo=mediainfo, transfer_type=settings.TRANSFER_TYPE)
    return schemas.Response(success=True, message="刮削完成")


@router.get("/{mediaid}", summary="查询媒体详情", response_model=schemas.MediaInfo)
def media_info(mediaid: str, type_name: str,
               _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据媒体ID查询themoviedb或豆瓣媒体信息，type_name: 电影/电视剧
    """
    mtype = MediaType(type_name)
    tmdbid, doubanid = None, None
    if mediaid.startswith("tmdb:"):
        tmdbid = int(mediaid[5:])
    elif mediaid.startswith("douban:"):
        doubanid = mediaid[7:]
    if not tmdbid and not doubanid:
        return schemas.MediaInfo()
    if settings.RECOGNIZE_SOURCE == "themoviedb":
        if not tmdbid and doubanid:
            tmdbinfo = MediaChain().get_tmdbinfo_by_doubanid(doubanid=doubanid, mtype=mtype)
            if tmdbinfo:
                tmdbid = tmdbinfo.get("id")
            else:
                return schemas.MediaInfo()
    else:
        if not doubanid and tmdbid:
            doubaninfo = MediaChain().get_doubaninfo_by_tmdbid(tmdbid=tmdbid, mtype=mtype)
            if doubaninfo:
                doubanid = doubaninfo.get("id")
            else:
                return schemas.MediaInfo()
    mediainfo = MediaChain().recognize_media(tmdbid=tmdbid, doubanid=doubanid, mtype=mtype)
    if mediainfo:
        MediaChain().obtain_images(mediainfo)
        return mediainfo.to_dict()
    return schemas.MediaInfo()
