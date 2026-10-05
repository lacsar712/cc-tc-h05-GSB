"""H05 回归：桩号列与毫米列从入库到展示都不许换位。

覆盖：
- 测量员报送：两格各自落库，互不吞掉对方的值；
- 待认领排队区（pending）与总表详情（done）共用 /api/logs，列序一致；
- 写入中断（commit 失败）必须回滚，不许留下列对调的碎片；
- 巡检员只读：可看不可写。

用 SQLite 临时库跑，不依赖 PostgreSQL；导入 api 前先接管环境，
并把后台认领线程摘掉，排队区的 pending 状态由测试自己掌控。
"""
import os
import tempfile

_tmp_db = os.path.join(tempfile.gettempdir(), "h05_test_tunnelconv.sqlite3")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["JWT_SECRET"] = "h05-test-secret"

import claimer  # noqa: E402

claimer.start = lambda: None  # 不启动后台认领线程

import pytest  # noqa: E402

import api  # noqa: E402
from models import ConvergenceLog, SessionLocal  # noqa: E402


@pytest.fixture()
def client():
    api.app.testing = False
    db = SessionLocal()
    try:
        db.query(ConvergenceLog).delete()
        db.commit()
    finally:
        db.close()
    api.seed()  # 两条种子：K12+180/1.2 合格、K18+040/5.6 超限
    return api.app.test_client()


def token(client, username, password):
    resp = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["access_token"]


def auth(client, username, password):
    return {"Authorization": f"Bearer {token(client, username, password)}"}


SURVEYOR = ("surveyor", "surv123456")
INSPECTOR = ("inspector", "insp123456")


def test_create_keeps_each_cell_in_its_own_column(client):
    """报送时桩号进桩号列、毫米进毫米列，两格不互相吞值。"""
    headers = auth(client, *SURVEYOR)
    resp = client.post(
        "/api/logs", json={"chainage": "K20+050", "delta_mm": -1.8}, headers=headers
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["chainage"] == "K20+050"
    assert body["delta_mm"] == pytest.approx(-1.8)
    assert body["status"] == "pending"

    db = SessionLocal()
    try:
        row = (
            db.query(ConvergenceLog).filter(ConvergenceLog.chainage == "K20+050").one()
        )
        assert row.delta_mm == pytest.approx(-1.8)
    finally:
        db.close()


def test_queue_and_detail_share_one_unswapped_view(client):
    """排队区(pending)新行与总表详情(done)种子行同走 /api/logs，列都不能错位。"""
    headers = auth(client, *SURVEYOR)
    client.post(
        "/api/logs", json={"chainage": "K7+777", "delta_mm": 2.4}, headers=headers
    )

    resp = client.get("/api/logs", headers=headers)
    assert resp.status_code == 200
    by_chainage = {r["chainage"]: r for r in resp.get_json()}

    # 三条记录的桩号都必须在桩号列，毫米值都必须在毫米列
    assert set(by_chainage) == {"K7+777", "K18+040", "K12+180"}
    assert by_chainage["K7+777"]["delta_mm"] == pytest.approx(2.4)
    assert by_chainage["K7+777"]["status"] == "pending"  # 排队区行
    assert by_chainage["K12+180"]["delta_mm"] == pytest.approx(1.2)
    assert by_chainage["K12+180"]["status"] == "done"  # 总表详情行
    assert by_chainage["K18+040"]["delta_mm"] == pytest.approx(5.6)

    # 换位碎片的典型特征：毫米值被塞进桩号列（字符串 "-1.8"/"2.4"…）
    for r in resp.get_json():
        assert r["chainage"] not in ("2.4", "1.2", "5.6")


def test_two_submissions_do_not_overwrite_each_other(client):
    """连续两格报送：每条各自保留自己的桩号与毫米值。"""
    headers = auth(client, *SURVEYOR)
    r1 = client.post(
        "/api/logs", json={"chainage": "K1+001", "delta_mm": 0.5}, headers=headers
    ).get_json()
    r2 = client.post(
        "/api/logs", json={"chainage": "K2+002", "delta_mm": -2.9}, headers=headers
    ).get_json()

    assert r1["chainage"] == "K1+001" and r1["delta_mm"] == pytest.approx(0.5)
    assert r2["chainage"] == "K2+002" and r2["delta_mm"] == pytest.approx(-2.9)
    assert r1["id"] != r2["id"]


def test_interrupted_write_leaves_no_swapped_fragment(client, monkeypatch):
    """写入在 commit 处中断：事务回滚，库里不许多出行、更不许留下对调碎片。"""
    real_session_local = api.SessionLocal

    def broken_session():
        s = real_session_local()

        def explode():
            raise RuntimeError("disk full mid-write")

        s.commit = explode  # 模拟写入中断
        return s

    monkeypatch.setattr(api, "SessionLocal", broken_session)

    db = SessionLocal()
    try:
        before = db.query(ConvergenceLog).count()
    finally:
        db.close()

    headers = auth(client, *SURVEYOR)
    resp = client.post(
        "/api/logs", json={"chainage": "K9+009", "delta_mm": 3.3}, headers=headers
    )
    assert resp.status_code == 500

    db = SessionLocal()
    try:
        rows = db.query(ConvergenceLog).all()
        assert len(rows) == before  # 没有碎片残留
        assert not db.query(ConvergenceLog).filter(
            ConvergenceLog.chainage == "3.3"
        ).first()  # 对调碎片特征：毫米值进了桩号列
        assert not db.query(ConvergenceLog).filter(
            ConvergenceLog.chainage == "K9+009"
        ).first()  # 半成品行同样不许落库
    finally:
        db.close()


def test_inspector_is_read_only(client):
    """巡检员照旧：能看总表，不能提交。"""
    headers = auth(client, *INSPECTOR)

    resp = client.get("/api/logs", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2  # 种子行可见

    resp = client.post(
        "/api/logs", json={"chainage": "K5+005", "delta_mm": 1.0}, headers=headers
    )
    assert resp.status_code == 403


def test_non_finite_delta_rejected(client):
    """NaN/Inf 这种会污染毫米列的值不允许入库。"""
    headers = auth(client, *SURVEYOR)
    resp = client.post(
        "/api/logs", json={"chainage": "K5+005", "delta_mm": "nan"}, headers=headers
    )
    assert resp.status_code == 400
