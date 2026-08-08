"""Streamlit UI for optimized YouTube playlist downloads — SaaS-style layout."""

from __future__ import annotations

import queue
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import streamlit as st

from core import download_item, resolve_playlist

DEFAULT_SAVE_DIR = str(Path("./downloads").resolve())

CUSTOM_CSS = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    header[data-testid="stHeader"] {background: transparent;}

    div[data-testid="stAppViewContainer"] > .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: none;
        color: #fff;
        font-weight: 600;
        letter-spacing: 0.02em;
        min-height: 2.75rem;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        border: none;
        color: #fff;
    }
    div.stButton > button[kind="primary"]:disabled {
        background: #94a3b8;
        box-shadow: none;
        color: #fff;
    }

    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
    }
    [data-testid="stMetricLabel"] {font-size: 0.85rem;}
    [data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
"""


def pick_directory() -> str | None:
    """Native OS folder picker (tkinter). Keep dialog above browser window."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    # Windows: dialog often opens behind the browser — force topmost
    root.wm_attributes("-topmost", 1)
    root.attributes("-topmost", True)
    try:
        root.lift()
        root.focus_force()
        path = filedialog.askdirectory(
            parent=root,
            initialdir=st.session_state.get("save_dir") or DEFAULT_SAVE_DIR,
        )
    finally:
        root.destroy()
    return path or None


def make_progress_hook(item_id: str, event_q: queue.Queue):
    """yt_dlp progress_hooks callback — thread-safe via queue."""

    def hook(d: dict) -> None:
        try:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = min(downloaded / total, 1.0) if total else 0.0
                event_q.put(
                    {
                        "id": item_id,
                        "kind": "progress",
                        "pct": pct,
                        "status": "Đang tải Video",
                    }
                )
            elif status == "finished":
                event_q.put(
                    {
                        "id": item_id,
                        "kind": "progress",
                        "pct": 1.0,
                        "status": "Đang xử lý (merge)...",
                    }
                )
        except Exception:  # noqa: BLE001 — never crash worker on hook glitches
            pass

    return hook


class ActiveLaneBoard:
    """Fixed number of UI lanes (= concurrency). Show only videos currently downloading."""

    def __init__(self, host, lane_count: int) -> None:
        self.lanes: list[dict[str, Any]] = []
        with host:
            for i in range(lane_count):
                with st.container(border=True):
                    st.caption(f"Luồng {i + 1}")
                    self.lanes.append(
                        {
                            "root": st.empty(),
                            "item_id": None,
                            "title": None,
                            "bar": None,
                            "status": None,
                            "pct": 0.0,
                        }
                    )
        self.id_to_lane: dict[str, dict[str, Any]] = {}
        self._waitlist: list[dict] = []
        self._wait_ids: set[str] = set()

    def _mount(self, lane: dict[str, Any], item: dict) -> dict[str, Any]:
        item_id = item["id"]
        lane["item_id"] = item_id
        lane["pct"] = 0.0
        with lane["root"].container():
            lane["title"] = st.empty()
            lane["title"].markdown(f"**{item['position']}. {item['title']}**")
            lane["bar"] = st.progress(0, text="0%")
            lane["status"] = st.empty()
            lane["status"].caption("Đang lấy thông tin")
        self.id_to_lane[item_id] = lane
        return lane

    def bind(self, item: dict) -> dict[str, Any] | None:
        item_id = item["id"]
        existing = self.id_to_lane.get(item_id)
        if existing is not None:
            return existing

        for lane in self.lanes:
            if lane["item_id"] is not None:
                continue
            self._wait_ids.discard(item_id)
            return self._mount(lane, item)

        if item_id not in self._wait_ids and item_id not in self.id_to_lane:
            self._waitlist.append(item)
            self._wait_ids.add(item_id)
        return None

    def release(self, item_id: str) -> None:
        lane = self.id_to_lane.pop(item_id, None)
        if lane is None:
            self._wait_ids.discard(item_id)
            self._waitlist = [x for x in self._waitlist if x["id"] != item_id]
            return
        lane["root"].empty()
        lane["item_id"] = None
        lane["title"] = None
        lane["bar"] = None
        lane["status"] = None
        lane["pct"] = 0.0

        while self._waitlist:
            nxt = self._waitlist.pop(0)
            self._wait_ids.discard(nxt["id"])
            if nxt["id"] in self.id_to_lane:
                continue
            self._mount(lane, nxt)
            break

    def clear_all(self) -> None:
        self._waitlist.clear()
        self._wait_ids.clear()
        for item_id in list(self.id_to_lane):
            self.release(item_id)
        for lane in self.lanes:
            lane["root"].empty()


def apply_event(event: dict, board: ActiveLaneBoard, items_by_id: dict[str, dict]) -> None:
    item_id = event["id"]
    item = items_by_id.get(item_id)
    if item is None:
        return

    kind = event.get("kind")
    if kind == "started":
        board.bind(item)
        return

    lane = board.id_to_lane.get(item_id)
    if lane is None:
        lane = board.bind(item)
    if lane is None or lane.get("bar") is None:
        return

    if kind in ("progress", "status"):
        pct = float(event.get("pct", lane.get("pct", 0.0)))
        status = event.get("status", "")
        lane["pct"] = pct
        lane["bar"].progress(pct, text=f"{int(pct * 100)}%")
        if status:
            lane["status"].caption(status)
    elif kind == "done":
        tip = event.get("status", "✅ Xong")
        if event.get("thumb_error"):
            tip = f"✅ Xong (thumb lỗi: {event['thumb_error']})"
        lane["bar"].progress(1.0, text="100%")
        lane["status"].caption(tip)
        board.release(item_id)
    elif kind == "error":
        lane["status"].caption(event.get("status", "❌ Lỗi"))
        board.release(item_id)


def run_workflow(
    items: list[dict],
    resolution: int,
    save_dir: str,
    max_workers: int,
    overall_bar,
    overall_text,
    board: ActiveLaneBoard,
    metric_ok,
    metric_fail,
) -> tuple[int, int]:
    """Stage 3: concurrent downloads; UI shows only active worker lanes."""
    event_q: queue.Queue = queue.Queue()
    total = len(items)
    done_count = 0
    ok_count = 0
    fail_count = 0
    items_by_id = {item["id"]: item for item in items}

    def worker(item: dict) -> dict:
        item_id = item["id"]
        event_q.put({"id": item_id, "kind": "started"})
        event_q.put({"id": item_id, "kind": "status", "pct": 0.0, "status": "Đang lấy thông tin"})

        def on_stage(msg: str) -> None:
            pct = 1.0 if msg.startswith("✅") else (0.95 if "Thumb" in msg else None)
            payload = {"id": item_id, "kind": "status", "status": msg}
            if pct is not None:
                payload["pct"] = pct
            event_q.put(payload)

        result = download_item(
            item,
            resolution=resolution,
            save_dir=save_dir,
            progress_hook=make_progress_hook(item_id, event_q),
            on_stage=on_stage,
        )
        if result["ok"]:
            event_q.put(
                {
                    "id": item_id,
                    "kind": "done",
                    "pct": 1.0,
                    "status": "✅ Xong",
                    "thumb_error": result.get("thumb_error"),
                }
            )
        else:
            event_q.put(
                {
                    "id": item_id,
                    "kind": "error",
                    "status": f"❌ Lỗi: {result.get('error') or 'unknown'}",
                }
            )
        return result

    overall_text.markdown("**Đang tải video…**")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, item): item for item in items}
        pending = set(futures.keys())

        while pending:
            try:
                while True:
                    apply_event(event_q.get_nowait(), board, items_by_id)
            except queue.Empty:
                pass

            finished = [f for f in pending if f.done()]
            for fut in finished:
                pending.discard(fut)
                done_count += 1
                try:
                    res = fut.result()
                    if res.get("ok"):
                        ok_count += 1
                    else:
                        fail_count += 1
                except Exception as exc:  # noqa: BLE001
                    fail_count += 1
                    item = futures[fut]
                    apply_event(
                        {
                            "id": item["id"],
                            "kind": "error",
                            "status": f"❌ Lỗi: {exc}",
                        },
                        board,
                        items_by_id,
                    )
                metric_ok.metric("Thành công", ok_count)
                metric_fail.metric("Thất bại / Bỏ qua", fail_count)
                overall_bar.progress(
                    done_count / total,
                    text=f"Đang tải {done_count}/{total} video…",
                )

            if pending:
                time.sleep(0.12)

        try:
            while True:
                apply_event(event_q.get_nowait(), board, items_by_id)
        except queue.Empty:
            pass

    board.clear_all()
    overall_bar.progress(1.0, text=f"Hoàn tất {ok_count}/{total} video thành công")
    overall_text.markdown(f"**Hoàn tất** — {ok_count}/{total} thành công, {fail_count} thất bại")
    return ok_count, fail_count


def init_state() -> None:
    if "save_dir" not in st.session_state:
        st.session_state.save_dir = DEFAULT_SAVE_DIR
    if "is_running" not in st.session_state:
        st.session_state.is_running = False


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_control_panel(disabled: bool) -> dict[str, Any] | None:
    """Left column: inputs + start. Returns submitted payload or None."""
    with st.container(border=True):
        st.markdown("### 🎛️ Thiết lập tải về")

        url = st.text_input(
            "Playlist / Video URL *",
            placeholder="https://www.youtube.com/playlist?list=...",
            disabled=disabled,
            key="url_input",
        )

        st.markdown("##### Cấu hình nâng cao")
        resolution_label = st.selectbox(
            "Độ phân giải",
            options=["1080p", "720p", "480p"],
            index=0,
            disabled=disabled,
        )

        pos_a, pos_b = st.columns(2)
        with pos_a:
            from_raw = st.number_input(
                "Từ vị trí",
                min_value=1,
                value=None,
                step=1,
                placeholder="1",
                disabled=disabled,
            )
        with pos_b:
            to_raw = st.number_input(
                "Đến vị trí",
                min_value=1,
                value=None,
                step=1,
                placeholder="10",
                disabled=disabled,
            )

        concurrency = st.slider(
            "Số luồng tải song song (Concurrency)",
            min_value=1,
            max_value=5,
            value=2,
            disabled=disabled,
        )

        st.markdown("##### Thư mục lưu trữ")
        if st.button("📂 Chọn thư mục", use_container_width=True, disabled=disabled):
            chosen = pick_directory()
            if chosen:
                st.session_state.save_dir = chosen
                st.rerun()
        st.caption(f"📁 {st.session_state.save_dir}")

        st.write("")
        submitted = st.button(
            "🚀 BẮT ĐẦU TẢI",
            type="primary",
            use_container_width=True,
            disabled=disabled,
            key="start_download",
        )

    if not submitted:
        return None

    return {
        "url": (url or "").strip(),
        "resolution_label": resolution_label,
        "from_raw": from_raw,
        "to_raw": to_raw,
        "concurrency": int(concurrency),
        "save_dir": st.session_state.save_dir or DEFAULT_SAVE_DIR,
    }


def render_dashboard_placeholders() -> dict[str, Any]:
    """Right column: metrics, master progress, worker slot host."""
    st.markdown("### 📊 Bảng điều khiển tiến trình")

    m1, m2, m3 = st.columns(3)
    with m1:
        metric_total = st.empty()
        metric_total.metric("Tổng số Video", 0)
    with m2:
        metric_ok = st.empty()
        metric_ok.metric("Thành công", 0)
    with m3:
        metric_fail = st.empty()
        metric_fail.metric("Thất bại / Bỏ qua", 0)

    st.markdown("##### Tiến trình tổng thể")
    overall_text = st.empty()
    overall_text.caption("Chưa bắt đầu — nhập URL và nhấn Bắt đầu tải.")
    overall_bar = st.progress(0, text="Sẵn sàng")

    st.markdown("##### Luồng tải song song")
    slots_host = st.container()
    with slots_host:
        st.caption("Các khung worker sẽ hiện khi phiên tải bắt đầu.")

    status_area = st.empty()

    return {
        "metric_total": metric_total,
        "metric_ok": metric_ok,
        "metric_fail": metric_fail,
        "overall_text": overall_text,
        "overall_bar": overall_bar,
        "slots_host": slots_host,
        "status_area": status_area,
    }


def main() -> None:
    st.set_page_config(
        page_title="YouTube Downloader Pro",
        page_icon="📥",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_state()
    inject_styles()

    st.markdown("# YouTube Downloader Pro")
    st.caption("Resolve playlist → tải song song video + thumbnail · TLS impersonate")

    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        payload = render_control_panel(disabled=st.session_state.is_running)

    with col_right:
        dash = render_dashboard_placeholders()

    if payload is None:
        return

    if st.session_state.is_running:
        dash["status_area"].warning("Đang có phiên tải chạy.")
        return

    if not payload["url"]:
        dash["status_area"].error("Vui lòng nhập Playlist / Video URL.")
        return

    from_index = int(payload["from_raw"]) if payload["from_raw"] is not None else None
    to_index = int(payload["to_raw"]) if payload["to_raw"] is not None else None
    if from_index is not None and to_index is not None and from_index > to_index:
        dash["status_area"].error("Giá trị **Từ vị trí** phải ≤ **Đến vị trí**.")
        return

    save_dir = payload["save_dir"]
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    resolution = int(payload["resolution_label"].replace("p", ""))
    workers = payload["concurrency"]

    st.session_state.is_running = True
    try:
        with dash["status_area"].container():
            with st.status("Đang phân tích dữ liệu nguồn…", expanded=True) as status:
                status.write("Đang lấy metadata playlist (flat-extract)…")
                items = resolve_playlist(
                    payload["url"],
                    from_index=from_index,
                    to_index=to_index,
                )
                if not items:
                    status.update(label="Không tìm thấy video.", state="error")
                else:
                    status.update(
                        label=f"Đã nạp xong {len(items)} video.",
                        state="complete",
                    )

        if not items:
            dash["overall_text"].caption("Không có video nào trong phạm vi đã chọn.")
            dash["status_area"].warning("Không có video nào trong phạm vi đã chọn.")
            return

        dash["status_area"].success(f"Đã nạp xong {len(items)} video.")
        dash["metric_total"].metric("Tổng số Video", len(items))
        dash["metric_ok"].metric("Thành công", 0)
        dash["metric_fail"].metric("Thất bại / Bỏ qua", 0)
        dash["overall_text"].markdown(f"**Đã nạp {len(items)} video** — chuẩn bị tải song song")
        dash["overall_bar"].progress(0, text=f"Đang tải 0/{len(items)} video…")

        lane_count = min(workers, len(items))
        board = ActiveLaneBoard(dash["slots_host"], lane_count)
        run_workflow(
            items=items,
            resolution=resolution,
            save_dir=save_dir,
            max_workers=workers,
            overall_bar=dash["overall_bar"],
            overall_text=dash["overall_text"],
            board=board,
            metric_ok=dash["metric_ok"],
            metric_fail=dash["metric_fail"],
        )
        dash["status_area"].success("Phiên tải kết thúc.")
    except Exception as exc:  # noqa: BLE001
        dash["overall_text"].markdown("**Lỗi** — xem chi tiết bên dưới")
        dash["status_area"].error(f"Lỗi: {exc}")
        st.exception(exc)
    finally:
        st.session_state.is_running = False


if __name__ == "__main__":
    main()
