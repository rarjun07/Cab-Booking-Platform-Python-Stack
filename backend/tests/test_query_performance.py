"""Transactional index preservation and real PostgreSQL plans on synthetic data."""
import json
from uuid import uuid4

from alembic import command
from sqlalchemy import text

from test_migrations import config_for


def plan_nodes(node):
    yield node
    for child in node.get("Plans", []):
        yield from plan_nodes(child)


def test_index_upgrade_preserves_rows_and_serves_history_and_wallet_without_sorts(test_engine):
    with test_engine.connect() as db:
        transaction = db.begin()
        try:
            config = config_for(db)
            command.downgrade(config, "0008_promos_wallet")
            owner, other, driver = uuid4(), uuid4(), uuid4()
            salt = uuid4().hex
            for identity, role in [(owner, "rider"), (other, "rider"), (driver, "driver")]:
                db.execute(text("INSERT INTO users(id,name,email,password_hash,role) VALUES (:id,'Plan fixture',:email,'unused',:role)"),
                           {"id": identity, "email": f"{identity}@example.com", "role": role})
            db.execute(text("INSERT INTO drivers(user_id) VALUES (:id)"), {"id": driver})
            db.execute(text("""INSERT INTO rides(id,rider_id,driver_id,status,pickup_point,drop_point,fare_estimate,created_at)
                SELECT md5(:salt || g::text)::uuid, CASE WHEN g%2=0 THEN :owner ELSE :other END,
                  :driver,'completed',ST_SetSRID(ST_MakePoint(77.2,28.6),4326),
                  ST_SetSRID(ST_MakePoint(77.3,28.7),4326),104.38,now()-make_interval(secs=>g)
                FROM generate_series(1,4000) g"""), {"salt": salt, "owner": owner, "other": other, "driver": driver})
            db.execute(text("""INSERT INTO wallet_topups(id,user_id,request_key,amount,status,created_at,credited_at)
                SELECT md5(:salt || 'topup' || g::text)::uuid,:owner,md5(:salt || 'request' || g::text)::uuid,
                  100,'succeeded',now()-make_interval(secs=>g),now() FROM generate_series(1,2000) g"""), {"salt": salt, "owner": owner})
            db.execute(text("""INSERT INTO wallet_entries(id,user_id,topup_id,amount,created_at)
                SELECT md5(:salt || 'entry' || g::text)::uuid,:owner,md5(:salt || 'topup' || g::text)::uuid,
                  100,now()-make_interval(secs=>g) FROM generate_series(1,2000) g"""), {"salt": salt, "owner": owner})
            db.execute(text("UPDATE users SET wallet_balance=200000 WHERE id=:owner"), {"owner": owner})
            for table in ("rides", "wallet_topups", "wallet_entries"):
                db.execute(text(f"ANALYZE {table}"))
            queries = {
                "rider_history": ("SELECT * FROM rides WHERE rider_id=:owner AND status IN ('completed','cancelled') ORDER BY created_at DESC,id DESC LIMIT 6", owner, "ix_rides_rider_history"),
                "driver_history": ("SELECT * FROM rides WHERE driver_id=:owner AND status IN ('completed','cancelled') ORDER BY created_at DESC,id DESC LIMIT 6", driver, "ix_rides_driver_history"),
                "wallet_entries": ("SELECT * FROM wallet_entries WHERE user_id=:owner ORDER BY created_at DESC,id DESC LIMIT 10", owner, "ix_wallet_entries_owner_created"),
                "wallet_topups": ("SELECT * FROM wallet_topups WHERE user_id=:owner ORDER BY created_at DESC,id DESC LIMIT 5", owner, "ix_wallet_topups_owner_created"),
            }
            def explain(sql, identity):
                return db.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql), {"owner": identity})[0]
            before = {name: explain(sql, identity) for name, (sql, identity, _) in queries.items()}
            preserved = {name: db.execute(text(sql), {"owner": identity}).all() for name, (sql, identity, _) in queries.items()}
            command.upgrade(config, "head")
            report = {}
            for name, (sql, identity, index) in queries.items():
                assert db.execute(text(sql), {"owner": identity}).all() == preserved[name]
                after = explain(sql, identity)
                nodes = list(plan_nodes(after["Plan"]))
                assert index in [node.get("Index Name") for node in nodes]
                assert not any("Sort" in node["Node Type"] for node in nodes)
                report[name] = {"before_nodes": [node["Node Type"] for node in plan_nodes(before[name]["Plan"])],
                                "after_index": index, "rows": after["Plan"]["Actual Rows"],
                                "shared_blocks_before": before[name]["Plan"].get("Shared Hit Blocks", 0),
                                "shared_blocks_after": after["Plan"].get("Shared Hit Blocks", 0)}
            assert db.scalar(text("SELECT wallet_balance FROM users WHERE id=:owner"), {"owner": owner}) == 200000
            command.check(config)
            command.downgrade(config, "0008_promos_wallet")
            assert db.scalar(text("SELECT count(*) FROM wallet_entries WHERE user_id=:owner"), {"owner": owner}) == 2000
            command.upgrade(config, "head")
            print("Synthetic query plans: " + json.dumps(report, sort_keys=True))
        finally:
            transaction.rollback()
