from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.services import dynamic_routing
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ospf6", tags=["OSPFv6"])


@router.get("/instance", summary="获取 OSPFv3 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ospf6_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/summary", summary="获取 OSPFv3 运行摘要")
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ospf6_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
