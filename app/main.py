"""口述史事件先后核对：FastAPI 后端。

* GET  /              单页应用
* POST /api/check     粘贴文本 → 逐行校验并联立区间
* GET  /healthz       容器健康检查
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .solver import check_text

app = FastAPI(title="口述史事件先后核对", version="1.0.0")


class CheckRequest(BaseModel):
    text: str = Field(default="", description="多行“事件甲,事件乙,最少分钟,最多分钟”")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/check")
def api_check(req: CheckRequest):
    return JSONResponse(check_text(req.text))


# 静态资源放最后挂载，避免吞掉上面的 API 路由
app.mount("/", StaticFiles(directory="static", html=True), name="static")
