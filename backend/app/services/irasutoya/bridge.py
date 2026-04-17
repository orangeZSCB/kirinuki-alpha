import httpx
from typing import List
from app.schemas.api import IrasutoyaImage
from app.core.config import settings

class IrasutoyaBridge:
    """irasutoya Node.js 服务桥接"""

    def __init__(self):
        self.base_url = f"http://localhost:{settings.irasutoya_port}"

    async def search(self, query: str) -> List[IrasutoyaImage]:
        """搜索插画"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={"query": query}
            )
            response.raise_for_status()
            data = response.json()
            return [IrasutoyaImage(**item) for item in data]

    async def random_image(self) -> IrasutoyaImage:
        """获取随机插画"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/random")
            response.raise_for_status()
            data = response.json()
            return IrasutoyaImage(**data)

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/random")
                return response.status_code == 200
        except Exception:
            return False
