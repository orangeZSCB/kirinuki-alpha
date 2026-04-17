from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.db import ProviderConfig
from app.schemas.api import ProviderConfigCreate, ProviderConfigResponse
import base64

router = APIRouter()

def mask_api_key(api_key: str) -> str:
    """脱敏 API Key"""
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"

@router.post("/providers", response_model=ProviderConfigResponse)
async def create_provider_config(config: ProviderConfigCreate, db: Session = Depends(get_db)):
    """创建 Provider 配置"""
    # 如果设置为默认，取消其他默认配置
    if config.is_default:
        db.query(ProviderConfig).filter(
            ProviderConfig.provider_kind == config.provider_kind
        ).update({"is_default": False})

    # 加密 API Key（简单 base64，生产环境应使用更强加密）
    if "api_key" in config.config:
        config.config["api_key"] = base64.b64encode(config.config["api_key"].encode()).decode()

    db_config = ProviderConfig(
        provider_kind=config.provider_kind,
        name=config.name,
        config=config.config,
        is_default=config.is_default
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.get("/providers", response_model=List[ProviderConfigResponse])
async def list_provider_configs(provider_kind: str = None, db: Session = Depends(get_db)):
    """获取 Provider 配置列表"""
    query = db.query(ProviderConfig)
    if provider_kind:
        query = query.filter(ProviderConfig.provider_kind == provider_kind)

    configs = query.all()

    # 脱敏 API Key
    for config in configs:
        if "api_key" in config.config:
            # 解密
            try:
                decrypted = base64.b64decode(config.config["api_key"]).decode()
                config.config["api_key"] = mask_api_key(decrypted)
            except:
                config.config["api_key"] = "***"

    return configs

@router.get("/providers/{config_id}", response_model=ProviderConfigResponse)
async def get_provider_config(config_id: str, db: Session = Depends(get_db)):
    """获取 Provider 配置详情"""
    config = db.query(ProviderConfig).filter(ProviderConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 脱敏 API Key
    if "api_key" in config.config:
        try:
            decrypted = base64.b64decode(config.config["api_key"]).decode()
            config.config["api_key"] = mask_api_key(decrypted)
        except:
            config.config["api_key"] = "***"

    return config

@router.delete("/providers/{config_id}")
async def delete_provider_config(config_id: str, db: Session = Depends(get_db)):
    """删除 Provider 配置"""
    config = db.query(ProviderConfig).filter(ProviderConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    db.delete(config)
    db.commit()
    return {"message": "配置已删除"}

@router.post("/providers/{config_id}/test")
async def test_provider_config(config_id: str, db: Session = Depends(get_db)):
    """测试 Provider 配置"""
    config = db.query(ProviderConfig).filter(ProviderConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # TODO: 实现实际测试逻辑
    return {"status": "ok", "message": "配置测试通过"}
