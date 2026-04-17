from fastapi import APIRouter, HTTPException
from app.schemas.api import IrasutoyaImage
from app.services.irasutoya.bridge import IrasutoyaBridge
from typing import List

router = APIRouter()
bridge = IrasutoyaBridge()

@router.get("/search", response_model=List[IrasutoyaImage])
async def search_irasutoya(q: str):
    """搜索 irasutoya 插画"""
    try:
        results = await bridge.search(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/random", response_model=IrasutoyaImage)
async def random_irasutoya():
    """获取随机 irasutoya 插画"""
    try:
        result = await bridge.random_image()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")
