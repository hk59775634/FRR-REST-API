from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

from app.config import settings
from app.routers import bgp, daemons, frr, isis, ospf, ospf6, rip, ripng, static_routes
from app.schemas import HealthResponse

OPENAPI_TAGS = [
    {
        "name": "系统",
        "description": "服务健康检查等基础接口。",
    },
    {
        "name": "FRR 配置管理",
        "description": (
            "基于 [frr-reload.py](https://docs.frrouting.org/projects/dev/en/latest/frr-reload.html) "
            "的 FRR 配置查询与动态重载接口。所有接口均需在请求头中携带 `X-API-Key`。"
        ),
    },
    {
        "name": "静态路由",
        "description": "静态路由的查询、添加与删除。支持 IPv4/IPv6 单播、黑洞及拒绝路由。",
    },
    {
        "name": "BGP",
        "description": "BGP 实例、邻居管理、路由表查询及 network 宣告。",
    },
    {
        "name": "动态路由开关",
        "description": "通过编辑 /etc/frr/daemons 启用或禁用各动态路由守护进程（bgpd、ospfd、ripd 等）。",
    },
    {
        "name": "OSPF",
        "description": "OSPFv2 实例配置、运行摘要与邻居查询。需先启用 ospfd。",
    },
    {
        "name": "OSPFv6",
        "description": "OSPFv3 实例配置与运行摘要。需先启用 ospf6d。",
    },
    {
        "name": "RIP",
        "description": "RIPv2 实例配置与运行状态。需先启用 ripd。",
    },
    {
        "name": "RIPng",
        "description": "RIPng 实例配置与运行状态。需先启用 ripngd。",
    },
    {
        "name": "IS-IS",
        "description": "IS-IS 实例配置、摘要与邻居查询。需先启用 isisd。",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "在 .env 中配置的 API 密钥",
        }
    }
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "tags" in operation:
                if operation.get("tags") == ["系统"] and operation.get("summary") == "健康检查":
                    continue
                operation["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app = FastAPI(
    title="FRR REST API",
    description=(
        "## FRR 配置管理 REST API\n\n"
        "本服务封装 FRR 的 `frr-reload.py` 工具，提供 HTTP 接口用于：\n\n"
        "- 查询 FRR 运行状态与当前配置\n"
        "- 预览配置变更差异（dry-run）\n"
        "- 动态应用配置重载\n"
        "- 静态路由与 BGP 的精细化管理\n"
        "- 动态路由守护进程开关（daemons 管理）\n"
        "- OSPF、RIP、IS-IS 等协议状态查询\n\n"
        "### 认证方式\n\n"
        "所有 `/api/v1/*` 接口需要在请求头中设置：\n\n"
        "```\n"
        "X-API-Key: <您的 API 密钥>\n"
        "```\n\n"
        "API 密钥在 `.env` 文件的 `API_KEY` 中配置。\n\n"
        "### 典型使用流程\n\n"
        "1. `GET /api/v1/running-config` — 获取当前运行配置\n"
        "2. `POST /api/v1/reload/test` — 提交新配置，预览变更\n"
        "3. `POST /api/v1/reload/apply` — 确认无误后应用变更\n"
    ),
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.openapi = custom_openapi

app.include_router(frr.router)
app.include_router(static_routes.router)
app.include_router(bgp.router)
app.include_router(daemons.router)
app.include_router(ospf.router)
app.include_router(ospf6.router)
app.include_router(rip.router)
app.include_router(ripng.router)
app.include_router(isis.router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["系统"],
    summary="健康检查",
    description="无需认证，用于负载均衡或监控探活。",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", message="FRR REST API 服务运行正常")


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc 文档",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "FRR REST API 服务",
        "docs": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
    }


def run():
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
