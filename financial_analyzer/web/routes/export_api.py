"""导出下载 API"""
import io
import logging
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from .data_api import _get_session
from financial_analyzer.utils.export import DataExporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{format}")
async def export_data(
    request: Request,
    format: str,
    stock_code: str = Query(""),
    categories: str = Query(""),
):
    session = _get_session(request)
    data_raw = session.get("data", {})
    sc = stock_code or session.get("stock_code", "")

    if not data_raw or not sc:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<p>无可导出数据</p>", status_code=400)

    # 如果指定了 categories，只导出选中的类别
    if categories:
        selected = [c.strip() for c in categories.split(",") if c.strip()]
        data_raw = {k: v for k, v in data_raw.items() if k in selected}

    if not data_raw:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<p>未选择导出内容</p>", status_code=400)

    data = {k: pd.DataFrame(v) for k, v in data_raw.items()}

    suffix_map = {"csv": ".csv", "xlsx": ".xlsx", "json": ".json"}
    suffix = suffix_map.get(format, f".{format}")
    filename = f"{sc}_data{suffix}"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if format == "csv":
            DataExporter.save_to_csv(data, str(tmp_path))
            media_type = "text/csv"
        elif format == "xlsx":
            DataExporter.save_to_excel(data, str(tmp_path))
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "json":
            DataExporter.save_to_json(data, str(tmp_path))
            media_type = "application/json"
        else:
            tmp_path.unlink(missing_ok=True)
            return StreamingResponse(
                io.BytesIO(b"Unsupported format"),
                media_type="text/plain",
                status_code=400,
            )

        return FileResponse(
            str(tmp_path),
            media_type=media_type,
            filename=filename,
            background=BackgroundTask(tmp_path.unlink, missing_ok=True),
        )
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.error(f"Export error: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"<p>导出失败: {e}</p>", status_code=500)
