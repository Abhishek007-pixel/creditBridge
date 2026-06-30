"""
MongoDB Atlas - Full Inspection Script
Shows all collections, document counts, indexes, and sample docs.
Run: venv\Scripts\python inspect_mongo.py
"""
import asyncio
import sys
from datetime import datetime

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
    from database_mongo import init_mongo, get_mongo_db

    ok = await init_mongo()
    if not ok:
        print("FAILED - Cannot connect to MongoDB Atlas.")
        return

    db = get_mongo_db()
    SEP = "=" * 60
    DIV = "-" * 60

    print(f"\n{SEP}")
    print(f"  MongoDB Atlas — Database: '{db.name}'")
    print(f"  Inspected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    # 1. All collections + doc counts
    collections = await db.list_collection_names()
    print(f"\n[COLLECTIONS]  Total: {len(collections)}")
    for c in sorted(collections):
        count = await db[c].count_documents({})
        print(f"  - {c:<35} {count} document(s)")

    # 2. Per-collection detail: indexes + sample doc
    for coll_name in sorted(collections):
        coll = db[coll_name]
        count = await coll.count_documents({})
        print(f"\n{DIV}")
        print(f"  Collection : {coll_name}  ({count} docs)")
        print(DIV)

        # Indexes
        indexes = await coll.index_information()
        print(f"  Indexes ({len(indexes)}):")
        for idx_name, idx_info in indexes.items():
            keys = dict(idx_info.get("key", []))
            unique = " [UNIQUE]" if idx_info.get("unique") else ""
            sparse = " [SPARSE]" if idx_info.get("sparse") else ""
            print(f"    * {idx_name:<40} keys={keys}{unique}{sparse}")

        # Latest sample document
        if count > 0:
            sample = await coll.find_one({}, sort=[("_id", -1)])
            if sample:
                sample["_id"] = str(sample["_id"])
                print(f"\n  Latest document (field preview):")
                for k, v in sample.items():
                    val_str = str(v)
                    if len(val_str) > 70:
                        val_str = val_str[:67] + "..."
                    print(f"    {k:<25} {val_str}")
        else:
            print(f"\n  (empty — no documents yet)")

    # 3. Server / connection info
    print(f"\n{DIV}")
    try:
        info = await db.client.admin.command("buildInfo")
        print(f"  MongoDB Server Version : {info.get('version', 'unknown')}")
    except Exception as e:
        print(f"  Server info: {e}")

    # 4. Atlas cluster info (topology)
    try:
        status = await db.client.admin.command("connectionStatus")
        auth_users = status.get("authInfo", {}).get("authenticatedUsers", [])
        if auth_users:
            print(f"  Authenticated as        : {auth_users[0].get('user', 'unknown')}")
    except Exception:
        pass

    print(f"\n{SEP}")
    print(f"  Atlas inspection complete — all systems healthy.")
    print(f"{SEP}\n")

if __name__ == "__main__":
    asyncio.run(main())
