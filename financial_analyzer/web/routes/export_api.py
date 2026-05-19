"""导出下载 API"""
import io
import logging
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.responses import FileResponse, StreamingResponse

from .data_api import _get_session
from financial_analyzer.utils.export import DataExporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{format}")
async def export_data(
    request: Request,
    format: str,
    analysis_type: str = Query(""),
):
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<p>无可导出数据</p>", status_code=400)

    data = {k: pd.DataFrame(v) for k, v in data_raw.items()}

    suffix_map = {"csv": ".csv", "xlsx": ".xlsx", "json": ".json"}
    suffix = suffix_map.get(format, f".{format}")
    filename = f"{stock_code}_{analysis_type or 'data'}{suffix}"

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
            background=lambda: tmp_path.unlink(missing_ok=True),
        )
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.error(f"Export error: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"<p>导出失败: {e}</p>", status_code=500)
