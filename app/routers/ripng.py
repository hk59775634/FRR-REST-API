from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.services import dynamic_routing
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ripng", tags=["RIPng"])


@router.get("/instance", summary="获取 RIPng 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ripng_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/status", summary="获取 RIPng 运行状态")
async def get_status(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ripng_status()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
