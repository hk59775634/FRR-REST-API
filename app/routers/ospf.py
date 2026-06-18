from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.services import dynamic_routing
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ospf", tags=["OSPF"])


@router.get("/instance", summary="获取 OSPFv2 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ospf_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/summary", summary="获取 OSPFv2 运行摘要")
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ospf_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/neighbors", summary="获取 OSPFv2 邻居")
async def get_neighbors(_: str = Depends(verify_api_key)) -> dict:
    try:
        return dynamic_routing.get_ospf_neighbors()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
