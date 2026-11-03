"""历史项目数据库 API：查询 / 详情 / 新增 / Excel 导入（openpyxl 实现）。

整改 B2：列表与统计共用 services.history_service，统计口径严格跟随筛选条件。
"""
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import HistoricalProject
from schemas import HistoryCreate, HistoryOut, ImportPreview
from services.history_service import HistoryFilters, apply_filters, compute_stats

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(
    keyword: str = "",
    project_type: str = "",
    region: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    q = apply_filters(db, HistoryFilters(keyword=keyword, region=region,
                                         project_type=project_type,
                                         date_from=date_from, date_to=date_to))
    total = q.count()
    items = (q.order_by(HistoricalProject.bid_open_date.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [HistoryOut.model_validate(i) for i in items],
    }


@router.get("/stats")
def stats(
    keyword: str = "",
    project_type: str = "",
    region: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    """统计严格跟随与列表一致的筛选条件，并返回有效样本数。"""
    return compute_stats(db, HistoryFilters(keyword=keyword, region=region,
                                            project_type=project_type,
                                            date_from=date_from, date_to=date_to))


@router.get("/{item_id}", response_model=HistoryOut)
def get_history(item_id: int, db: Session = Depends(get_db)):
    item = db.get(HistoricalProject, item_id)
    if not item:
        raise HTTPException(404, "历史项目不存在")
    return item


@router.post("", response_model=HistoryOut)
def create_history(payload: HistoryCreate, db: Session = Depends(get_db)):
    item = HistoricalProject(**payload.model_dump(), is_demo=False)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_history(item_id: int, db: Session = Depends(get_db)):
    item = db.get(HistoricalProject, item_id)
    if not item:
        raise HTTPException(404, "历史项目不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


TEMPLATE_HEADERS = ["项目名称", "项目编号", "区域", "工程类型", "招标方式", "招标人",
                    "中标单位", "中标金额(万元)", "控制价(万元)", "投标单位(用/分隔)", "开标日期", "备注"]


@router.get("/import/template")
def download_template():
    """下载 Excel 导入模板。"""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "历史项目导入"
    ws.append(TEMPLATE_HEADERS)
    ws.append(["示例：深圳XX学校改扩建工程", "SZ-2025-0001", "南山区", "房建", "公开招标",
               "深圳市XX局", "深圳市XX建设集团有限公司", "8600.00", "9000.00",
               "单位A/单位B/单位C", "2025-06-15", "示例行导入前请删除"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=history_import_template.xlsx"},
    )


def _parse_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


@router.post("/import", response_model=ImportPreview)
async def import_history(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Excel 批量导入：列顺序同模板，投标单位用“/”分隔。"""
    from openpyxl import load_workbook

    if not (file.filename or "").endswith(".xlsx"):
        raise HTTPException(400, "请上传 .xlsx 格式的 Excel 文件（可先下载导入模板）")
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(400, "Excel 文件解析失败，请使用导入模板填写")
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    imported, errors = 0, []
    for idx, row in enumerate(rows, start=2):
        if not row or not row[0]:
            continue
        try:
            name = str(row[0]).strip()
            if name.startswith("示例："):
                continue
            participants = []
            if len(row) > 9 and row[9]:
                participants = [s.strip() for s in str(row[9]).replace("／", "/").split("/") if s.strip()]
            item = HistoricalProject(
                project_name=name,
                project_code=str(row[1] or "").strip() if len(row) > 1 else "",
                region=str(row[2] or "深圳市").strip() if len(row) > 2 else "深圳市",
                project_type=str(row[3] or "房建").strip() if len(row) > 3 else "房建",
                tender_method=str(row[4] or "公开招标").strip() if len(row) > 4 else "公开招标",
                tenderer=str(row[5] or "").strip() if len(row) > 5 else "",
                winner=str(row[6] or "").strip() if len(row) > 6 else "",
                bid_amount=float(row[7] or 0) if len(row) > 7 else 0.0,
                control_amount=float(row[8] or 0) if len(row) > 8 else 0.0,
                participants=participants,
                bid_open_date=_parse_date(row[10]) if len(row) > 10 else None,
                remarks=str(row[11] or "").strip() if len(row) > 11 else "",
                is_demo=False,
            )
            db.add(item)
            imported += 1
        except Exception as exc:
            errors.append(f"第 {idx} 行导入失败：{exc}")
    db.commit()
    return ImportPreview(
        ok=len(errors) == 0,
        message=f"共识别 {len(rows)} 行，成功导入 {imported} 条" + (f"，失败 {len(errors)} 条" if errors else ""),
        rows=len(rows),
        imported=imported,
        errors=errors[:20],
    )
