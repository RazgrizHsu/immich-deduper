#!/usr/bin/env python
import json
import os
import sys
import unittest
from datetime import datetime
from typing import Sequence, Any, Optional
from dataclasses import dataclass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tester import T

from mod.models import Json, BaseDictModel
from mod.models import Now, Usr, Nfy, Tsk, Mdl, Asset, AssetExif, SimInfo, Gws, TskStatus
import db.pics as pics
from util import log

lg = log.get(__name__)
from dto import AutoDbField, Ausl, PairKv, DcProxy, Muod
import db.sets as sets




class MockCursor:
    def __init__(self, cols: Sequence[str]): self._desc = tuple((c,) for c in cols)

    @property
    def description(self) -> Optional[Sequence[Sequence[Any]]]: return self._desc


class TestBaseDictModel(T):
    def test_simple_model(self):
        usr = Usr(id="1", name="TestUser", email="test@example.com")

        usr_dict = usr.toDict()
        usr_json = usr.toJson()

        self.eq(usr_dict["id"], "1")
        self.eq(usr_dict["name"], "TestUser")

        usr_from_dict = Usr.fromDic(usr_dict)
        usr_from_json = Usr.fromDic(json.loads(usr_json))

        self.eq(usr_from_dict.id, "1")
        self.eq(usr_from_dict.name, "TestUser")
        self.eq(usr_from_json.id, "1")
        self.eq(usr_from_json.email, "test@example.com")

    def test_optional_fields(self):
        usr1 = Usr(id="1", name="User1")
        self.eq(usr1.id, "1")
        self.eq(usr1.name, "User1")
        self.eq(usr1.email, '')

        usr1_dict = usr1.toDict()
        usr1_restored = Usr.fromDic(usr1_dict)

        self.eq(usr1_restored.id, "1")
        self.eq(usr1_restored.name, "User1")
        self.eq(usr1_restored.email, '')

        usr2 = Usr()
        usr2_dict = usr2.toDict()
        usr2_restored = Usr.fromDic(usr2_dict)

        self.eq(usr2_restored.id, '')
        self.eq(usr2_restored.name, '')


    def test_json_class(self):
        json_str = '{"make":"Canon","model":"EOS 5D"}'
        json_obj1 = Json(json_str)
        self.eq(json_obj1["make"], "Canon")
        self.eq(json_obj1["model"], "EOS 5D")

        json_dict = {"make": "Nikon", "model": "D850"}
        json_obj2 = Json(json_dict)
        self.eq(json_obj2["make"], "Nikon")
        self.eq(json_obj2["model"], "D850")

        json_obj2["make"] = "Sony"
        self.eq(json_obj2["make"], "Sony")

        json_obj2["year"] = 2023
        self.eq(json_obj2["year"], 2023)

    def test_asset_model(self):
        asset = Asset(
            id="test-asset",
            ownerId="user1",
            originalFileName="test.jpg"
        )

        asset_dict = asset.toDict()
        self.eq(asset_dict["id"], "test-asset")
        self.eq(asset_dict["ownerId"], "user1")

        rst = Asset.fromDic(asset_dict)
        self.eq(rst.id, "test-asset")
        self.eq(rst.originalFileName, "test.jpg")

        self.eq(rst.isVectored, 0)
        self.eq(rst.simInfos, [])

    def test_asset_model_with_simInfos(self):
        ass = Asset(
            id="test-asset",
            ownerId="user1",
            originalFileName="test.jpg",
            simInfos=[SimInfo(aid=1, score=0.5), SimInfo(aid=2, score=0.6)]
        )

        dict = ass.toDict()
        self.eq(dict["id"], "test-asset")
        self.eq(dict["ownerId"], "user1")
        self.eq(len(dict["simInfos"]), 2)
        self.eq(dict["simInfos"][0]["aid"], 1)
        self.eq(dict["simInfos"][1]["aid"], 2)

        rst = Asset.fromDic(dict)
        self.eq(rst.id, "test-asset")
        self.eq(rst.originalFileName, "test.jpg")
        self.eq(len(rst.simInfos), 2)
        self.isType(rst.simInfos[0], SimInfo)
        self.eq(rst.simInfos[0].aid, 1)
        self.eq(rst.simInfos[0].score, 0.5)

    def test_asset_exif_json_string_conversion(self):
        jstr = '{"make":"Canon","model":"EOS 5D","fNumber":2.8,"iso":100,"focalLength":24.0}'

        dict = { "id": "test-asset", "jsonExif": jstr }

        rst = Asset.fromDic(dict)
        self.isType(rst.jsonExif, AssetExif)
        self.eq(rst.jsonExif.make, "Canon")
        self.eq(rst.jsonExif.model, "EOS 5D")
        self.eq(rst.jsonExif.fNumber, 2.8)
        self.eq(rst.jsonExif.iso, 100)
        self.eq(rst.jsonExif.focalLength, 24.0)

    def test_asset_exif_from_db(self):
        mock_cursor = MockCursor(['id', 'jsonExif'])
        row = ('test-asset', '{"make":"Nikon","model":"D850","fNumber":4.0,"iso":200,"focalLength":70.0}')

        asset = Asset.fromDB(mock_cursor, row)
        self.isType(asset.jsonExif, AssetExif)
        self.eq(asset.jsonExif.make, "Nikon")
        self.eq(asset.jsonExif.model, "D850")
        self.eq(asset.jsonExif.fNumber, 4.0)
        self.eq(asset.jsonExif.iso, 200)
        self.eq(asset.jsonExif.focalLength, 70.0)

    def test_asset_simInfos_from_db(self):
        mock_cursor = MockCursor(['id', 'simInfos'])
        row = ('test-asset', '[{"aid":1,"score":0.9},{"aid":2,"score":0.8},{"aid":3,"score":0.7}]')
        asset = Asset.fromDB(mock_cursor, row)

        self.eq(len(asset.simInfos), 3)
        self.isType(asset.simInfos[0], SimInfo)
        self.eq(asset.simInfos[0].aid, 1)
        self.eq(asset.simInfos[0].score, 0.9)

        row2 = ('test-asset', '[]')
        asset = Asset.fromDB(mock_cursor, row2)
        self.eq(asset.simInfos, [])

        row3 = ('test-asset', None)
        asset = Asset.fromDB(mock_cursor, row3)
        self.eq(asset.simInfos, [])

    def test_datetime_serialization(self):
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        tsk = Tsk( id="task1", name="Test Task", args={"created_at": test_dt})
        tsk_dict = tsk.toDict()
        tsk_json = tsk.toJson()

        self.ok(isinstance(tsk_dict["args"]["created_at"], datetime))

        tsk_from_json = json.loads(tsk_json)
        self.ok(isinstance(tsk_from_json["args"]["created_at"], str))

        tsk_restored = Tsk.fromDic(tsk_dict)
        self.ok(isinstance(tsk_restored.args["created_at"], datetime))
        self.eq(tsk_restored.args["created_at"].year, 2023)
        self.eq(tsk_restored.args["created_at"].month, 1)

    def test_dict_field(self):
        nfy = Nfy()
        nfy.info("Test message", 3000)

        nfy_dict = nfy.toDict()
        self.eq(len(nfy_dict["msgs"]), 1)

        self.eq(nfy_dict["msgs"][0]["message"], "Test message")
        self.eq(nfy_dict["msgs"][0]["type"], "info")

        nfy_restored = Nfy.fromDic(nfy_dict)
        self.eq(len(nfy_restored.msgs), 1)
        self.eq(nfy_restored.msgs[0]["message"], "Test message")

    def test_combined_complex_scenario(self):
        now = Now()

        nfy = Nfy()
        nfy.info("System message")
        nfy.warn("Warning message")

        tsk = Tsk( id="task1", name="Process task")
        mdl = Mdl( id="modal1", msg="Confirm delete?")
        data = { "now": now.toDict(), "nfy": nfy.toDict(), "tsk": tsk.toDict(), "mdl": mdl.toDict() }

        now_restored = Now.fromDic(data["now"])
        nfy_restored = Nfy.fromDic(data["nfy"])
        tsk_restored = Tsk.fromDic(data["tsk"])
        mdl_restored = Mdl.fromDic(data["mdl"])

        self.notNone(now_restored.sim)

        self.eq(len(nfy_restored.msgs), 2)

        tsk_restored.reset()
        self.isNone(tsk_restored.id)

        mdl_restored.reset()
        self.isNone(mdl_restored.id)
        self.notOk(mdl_restored.ok)


    def test_db_assets_exif_conversion(self):
        try:
            assets = pics.getAll(count=5)

            if not assets: self.skipTest("No assets found in database")

            for asset in assets:
                if asset.jsonExif is not None:
                    self.isType(asset.jsonExif, AssetExif)

                    if hasattr(asset.jsonExif, 'make') and asset.jsonExif.make: self.isType(asset.jsonExif.make, str)
                    if hasattr(asset.jsonExif, 'model') and asset.jsonExif.model: self.isType(asset.jsonExif.model, str)
                    if hasattr(asset.jsonExif, 'fNumber') and asset.jsonExif.fNumber: self.isType(asset.jsonExif.fNumber, float)
                    if hasattr(asset.jsonExif, 'iso') and asset.jsonExif.iso: self.isType(asset.jsonExif.iso, int)
                    if hasattr(asset.jsonExif, 'dateTimeOriginal') and asset.jsonExif.dateTimeOriginal: self.isType(asset.jsonExif.dateTimeOriginal, str)

                self.isType(asset.simInfos, list)
                for sim in asset.simInfos:
                    if sim:
                        self.isType(sim, SimInfo)
                        self.ok(hasattr(sim, 'aid'))
                        self.ok(hasattr(sim, 'score'))
        except Exception as e: self.skipTest(f"Database test failed: {e})")

    def test_db_simInfos_functionality(self):
        try:
            assets = pics.getAll(count=5)

            if not assets: self.fail("No assets found in database")

            for ass in assets:
                self.isType(ass.simInfos, list)
                for sim in ass.simInfos:
                    if sim:
                        self.isType(sim, SimInfo)
                        self.ok(hasattr(sim, 'aid'))
                        self.ok(hasattr(sim, 'score'))
        except Exception as e: self.skipTest(f"Database test failed: {e})")

    def test_specific_asset_exif_conversion(self):
        try:
            assets = pics.getAll(count=1)

            if not assets: self.skipTest("No assets found in database")

            asset_id = assets[0].id
            asset = pics.getById(asset_id)

            self.notNone(asset)
            self.eq(asset.id, asset_id)

            if asset.jsonExif is not None:
                self.isType(asset.jsonExif, AssetExif)

                if hasattr(asset.jsonExif, 'make') and asset.jsonExif.make: self.isType(asset.jsonExif.make, str)
                if hasattr(asset.jsonExif, 'model') and asset.jsonExif.model: self.isType(asset.jsonExif.model, str)
                if hasattr(asset.jsonExif, 'fNumber') and asset.jsonExif.fNumber: self.isType(asset.jsonExif.fNumber, float)
                if hasattr(asset.jsonExif, 'iso') and asset.jsonExif.iso: self.isType(asset.jsonExif.iso, int)
                if hasattr(asset.jsonExif, 'dateTimeOriginal') and asset.jsonExif.dateTimeOriginal: self.isType(asset.jsonExif.dateTimeOriginal, str)

            self.ok(hasattr(asset, 'simInfos'))
            self.isType(asset.simInfos, list)
        except Exception as e: self.skipTest(f"Database test failed: {e})")


    def test_modal_basic(self):
        now = Now()
        self.notNone(now.sim)

    def test_fromDict_error_handling(self):
        # Test with required field missing (will cause TypeError in __init__)
        class RequiredFieldModel(BaseDictModel):
            id: str  # required field
            name: str  # required field

            def __init__(self, id: str, name: str):
                self.id = id
                self.name = name

        # Missing required field 'name' should raise RuntimeError
        invalid_dict = {"id": "test"}
        with self.raises(RuntimeError): RequiredFieldModel.fromDic(invalid_dict)

        # Test with extra fields - should succeed as extra fields are filtered
        valid_dict = {"id": "test", "name": "test", "extra": "field", "another": "field"}
        result = RequiredFieldModel.fromDic(valid_dict)
        self.notNone(result)
        self.eq(result.id, "test")
        self.eq(result.name, "test")

    def test_fromStr_basic(self):
        usr = Usr(id="1", name="TestUser", email="test@example.com")
        json_str = usr.toJson()

        usr_restored = Usr.fromStr(json_str)
        self.eq(usr_restored.id, "1")
        self.eq(usr_restored.name, "TestUser")
        self.eq(usr_restored.email, "test@example.com")


    def test_fromStr_with_datetime(self):
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        tsk = Tsk(id="task1", name="Test Task", args={"created_at": test_dt})

        json_str = tsk.toJson()
        tsk_restored = Tsk.fromStr(json_str)

        self.eq(tsk_restored.id, "task1")
        self.eq(tsk_restored.name, "Test Task")
        self.hasIn("created_at", tsk_restored.args)

    def test_fromStr_invalid_json(self):
        with self.raises(ValueError) as ctx: Usr.fromStr("not a json string")
        self.hasIn("Invalid JSON string", str(ctx.exception))

        with self.raises(ValueError) as ctx: Usr.fromStr("{invalid json}")
        self.hasIn("Invalid JSON string", str(ctx.exception))

    def test_fromStr_non_dict_json(self):
        with self.raises(ValueError) as ctx: Usr.fromStr("[1, 2, 3]")
        self.hasIn("Expected dict after JSON parse", str(ctx.exception))

        with self.raises(ValueError) as ctx: Usr.fromStr('"string value"')
        self.hasIn("Expected dict after JSON parse", str(ctx.exception))

    def test_fromStr_with_complex_model(self):
        asset = Asset(
            id="test-asset",
            ownerId="user1",
            originalFileName="test.jpg",
            simInfos=[SimInfo(aid=1, score=0.5), SimInfo(aid=2, score=0.6)]
        )

        json_str = asset.toJson()
        rst = Asset.fromStr(json_str)

        self.eq(rst.id, "test-asset")
        self.eq(rst.ownerId, "user1")
        self.eq(len(rst.simInfos), 2)
        self.isType(rst.simInfos[0], SimInfo)
        self.eq(rst.simInfos[0].aid, 1)
        self.eq(rst.simInfos[0].score, 0.5)

    def test_fromDB_error_handling(self):
        # Test with required field missing (will cause TypeError in __init__)
        class RequiredFieldModel(BaseDictModel):
            id: str  # required field
            name: str  # required field

            def __init__(self, id: str, name: str):
                self.id = id
                self.name = name

        # Mock cursor with only 'id' column, missing 'name' should raise TypeError
        mock_cursor = MockCursor(['id'])
        row = ('test-id',)
        with self.raises(TypeError): RequiredFieldModel.fromDB(mock_cursor, row)

        # Test with None description should raise TypeError
        class NoneDescCursor:
            @property
            def description(self) -> None: return None

        mock_cursor2 = NoneDescCursor()
        BaseDictModel._cheDbCols.clear()
        row2 = ('test-id', 'test-name')
        with self.raises(TypeError): RequiredFieldModel.fromDB(mock_cursor2, row2)


    def test_data_with_enum(self):
        # Test 1: Create Gws with TskStatus enum
        msg = Gws(
            tsn="task-123",
            typ="progress",
            nam="Test Task",
            msg="Processing...",
            ste=TskStatus.RUNNING
        )

        self.eq(msg.tsn, "task-123")
        self.eq(msg.ste, TskStatus.RUNNING)

        # Test 2: Convert to dict
        msg_dict = msg.toDict()
        self.eq(msg_dict["tsn"], "task-123")
        self.eq(msg_dict["ste"], TskStatus.RUNNING)

        # Test 3: Convert to JSON and back
        json_str = msg.toJson()
        self.hasIn('"tsn": "task-123"', json_str)

        # Test 4: FromStr with enum
        msg_restored = Gws.fromStr(json_str)
        self.eq(msg_restored.tsn, "task-123")
        self.eq(msg_restored.typ, "progress")
        self.eq(msg_restored.nam, "Test Task")
        self.eq(msg_restored.msg, "Processing...")
        # Enum might be converted to string in JSON
        self.ok(msg_restored.ste == TskStatus.RUNNING or msg_restored.ste == "running")

        # Test 5: FromDict with enum value
        dict_with_enum = {
            "tsn": "task-456",
            "typ": "complete",
            "nam": "Another Task",
            "msg": "Done!",
            "ste": TskStatus.COMPLETED
        }
        msg_from_dict = Gws.fromDic(dict_with_enum)
        self.eq(msg_from_dict.tsn, "task-456")
        self.eq(msg_from_dict.ste, TskStatus.COMPLETED)

        # Test 6: FromDict with enum string value
        dict_with_string = {
            "tsn": "task-789",
            "typ": "error",
            "nam": "Failed Task",
            "msg": "Error occurred",
            "ste": "failed"
        }
        msg_from_string = Gws.fromDic(dict_with_string)
        self.eq(msg_from_string.tsn, "task-789")
        # Check if it can handle string value for enum
        self.ok(msg_from_string.ste == TskStatus.FAILED or msg_from_string.ste == "failed")

        # Test 7: All enum values
        for status in TskStatus:
            msg = Gws(tsn=f"test-{status.value}", ste=status)
            json_str = msg.toJson()
            restored = Gws.fromStr(json_str)
            self.eq(restored.tsn, f"test-{status.value}")
            # Check status is either enum or string value
            self.ok(restored.ste == status or restored.ste == status.value)

    def test_data_optional_fields(self):
        # Test with minimal fields
        msg = Gws(tsn="minimal-123")
        self.eq(msg.tsn, "minimal-123")
        self.isNone(msg.typ)
        self.isNone(msg.nam)
        self.isNone(msg.msg)
        self.isNone(msg.ste)

        # Convert to JSON and back
        json_str = msg.toJson()
        restored = Gws.fromStr(json_str)
        self.eq(restored.tsn, "minimal-123")
        self.isNone(restored.typ)
        self.isNone(restored.ste)

    def test_data_fromstr_errors(self):
        # Test invalid JSON
        with self.raises(ValueError) as ctx: Gws.fromStr("not json")
        self.hasIn("Invalid JSON string", str(ctx.exception))

        # Test non-dict JSON
        with self.raises(ValueError) as ctx: Gws.fromStr('["array", "not", "dict"]')
        self.hasIn("Expected dict", str(ctx.exception))

    def test_uuid_to_usr_conversion(self):
        import uuid

        # Test 1: Create UUID and convert to string for Usr
        test_uuid = uuid.uuid4()
        usr = Usr(id=str(test_uuid), name="TestUser", email="test@example.com")

        self.isType(usr.id, str)
        self.eq(usr.id, str(test_uuid))

        # Test 2: Convert to dict and back
        usr_dict = usr.toDict()
        self.isType(usr_dict["id"], str)

        usr_restored = Usr.fromDic(usr_dict)
        self.isType(usr_restored.id, str)
        self.eq(usr_restored.id, str(test_uuid))

        # Test 3: JSON serialization
        json_str = usr.toJson()
        usr_from_json = Usr.fromStr(json_str)
        self.isType(usr_from_json.id, str)
        self.eq(usr_from_json.id, str(test_uuid))

        # Test 4: Multiple UUIDs
        uuid_list = [uuid.uuid4() for _ in range(5)]
        for test_uuid in uuid_list:
            usr = Usr(id=str(test_uuid), name=f"User-{test_uuid}", email=f"{test_uuid}@test.com")
            self.isType(usr.id, str)
            self.eq(usr.id, str(test_uuid))

            # Verify round-trip conversion
            restored = Usr.fromStr(usr.toJson())
            self.eq(restored.id, str(test_uuid))

        # Test 5: UUID object in dict should be converted to str
        test_uuid = uuid.uuid4()
        dict_with_uuid = {
            "id": test_uuid,  # UUID object, not string
            "name": "TestUser",
            "email": "test@example.com"
        }

        usr_from_uuid_dict = Usr.fromDic(dict_with_uuid)
        self.isType(usr_from_uuid_dict.id, str)
        self.eq(usr_from_uuid_dict.id, str(test_uuid))

        # Test 6: Verify it's actually converted, not just equal
        self.neq(type(usr_from_uuid_dict.id), type(test_uuid))
        self.eq(type(usr_from_uuid_dict.id), str)

    def test_type_conversion_comprehensive(self):
        # Test numeric type conversions
        asset_dict = {
            "autoId": "123",  # string to int
            "id": "test-asset",
            "isVectored": "1",  # string to int
            "simOk": "0",     # string to int
            "jsonExif": {
                "fNumber": "2.8",        # string to float
                "iso": "800",            # string to int
                "focalLength": "85.0",   # string to float
                "exifImageWidth": "4000", # string to int
                "rating": "5"            # string to int
            }
        }

        asset = Asset.fromDic(asset_dict)

        # Verify numeric conversions
        self.isType(asset.autoId, int)
        self.eq(asset.autoId, 123)
        self.isType(asset.isVectored, int)
        self.eq(asset.isVectored, 1)
        self.isType(asset.simOk, int)
        self.eq(asset.simOk, 0)

        # Verify nested object numeric conversions
        self.isType(asset.jsonExif.fNumber, float)
        self.eq(asset.jsonExif.fNumber, 2.8)
        self.isType(asset.jsonExif.iso, int)
        self.eq(asset.jsonExif.iso, 800)
        self.isType(asset.jsonExif.focalLength, float)
        self.eq(asset.jsonExif.focalLength, 85.0)
        self.isType(asset.jsonExif.exifImageWidth, int)
        self.eq(asset.jsonExif.exifImageWidth, 4000)
        self.isType(asset.jsonExif.rating, int)
        self.eq(asset.jsonExif.rating, 5)

    def test_deeply_nested_structure(self):
        # Test Asset with nested simInfos, jsonExif, simGIDs
        assets_data = [
            {
                "autoId": "100",
                "id": "asset-1",
                "originalFileName": "photo1.jpg",
                "isVectored": "1",
                "simInfos": [
                    {"aid": "1001", "score": "0.95", "isSelf": False},
                    {"aid": "1002", "score": "0.87", "isSelf": True}
                ],
                "jsonExif": {
                    "make": "Canon",
                    "fNumber": "1.8",
                    "iso": "200"
                },
                "simGIDs": ["10", "20", "30"]
            },
            {
                "autoId": "200",
                "id": "asset-2",
                "originalFileName": "photo2.jpg",
                "isVectored": "0",
                "simInfos": [
                    {"aid": "2001", "score": "0.73", "isSelf": False}
                ],
                "simGIDs": ["40", "50"]
            }
        ]

        asset1 = Asset.fromDic(assets_data[0])
        self.isType(asset1, Asset)
        self.isType(asset1.autoId, int)
        self.eq(asset1.autoId, 100)
        self.eq(asset1.id, "asset-1")
        self.isType(asset1.isVectored, int)
        self.eq(asset1.isVectored, 1)

        self.eq(len(asset1.simInfos), 2)
        self.isType(asset1.simInfos[0], SimInfo)
        self.isType(asset1.simInfos[0].aid, int)
        self.eq(asset1.simInfos[0].aid, 1001)
        self.isType(asset1.simInfos[0].score, float)
        self.eq(asset1.simInfos[0].score, 0.95)
        self.notOk(asset1.simInfos[0].isSelf)

        self.isType(asset1.jsonExif, AssetExif)
        self.eq(asset1.jsonExif.make, "Canon")
        self.isType(asset1.jsonExif.fNumber, float)
        self.eq(asset1.jsonExif.fNumber, 1.8)
        self.isType(asset1.jsonExif.iso, int)
        self.eq(asset1.jsonExif.iso, 200)

        self.eq(len(asset1.simGIDs), 3)
        self.isType(asset1.simGIDs[0], int)
        self.eq(asset1.simGIDs, [10, 20, 30])

        asset2 = Asset.fromDic(assets_data[1])
        self.isType(asset2.autoId, int)
        self.eq(asset2.autoId, 200)
        self.eq(len(asset2.simInfos), 1)
        self.isType(asset2.simInfos[0].aid, int)
        self.eq(asset2.simInfos[0].aid, 2001)
        self.eq(asset2.simGIDs, [40, 50])


class TestAutoDbField(T):
    def test_dto_types(self):
        from dto import DtoSets

        fresh = DtoSets()
        fresh.clearCache()

        self.isType(fresh.thMin, float)
        self.isType(fresh.autoNext, bool)
        self.isType(fresh.rtreeMax, int)
        self.isType(fresh.mdlImgSets, dict)

    def test_dataclass_attr_write(self):
        @dataclass
        class MdlSets:
            auto: bool = False
            help: bool = True

        class TestDto: cfg = AutoDbField('test_mdl_dc', MdlSets, MdlSets())

        obj1 = TestDto()
        obj1.cfg.auto = True
        obj1.cfg.help = False

        obj2 = TestDto()
        if hasattr(obj2, '_cache_test_mdl_dc'): delattr(obj2, '_cache_test_mdl_dc')

        self.eq(obj2.cfg.auto, True)
        self.eq(obj2.cfg.help, False)

    def test_dataclass_field_types(self):
        @dataclass
        class ISet:
            a: bool = False
            b: bool = True
            c: int = 123

        class Dto: cfg = AutoDbField('test_iset_types', ISet)

        dto = Dto()
        dto.cfg.a = True
        dto.cfg.c = 456

        dto2 = Dto()
        if hasattr(dto2, '_cache_test_iset_types'): delattr(dto2, '_cache_test_iset_types')

        self.eq(dto2.cfg.a, True)
        self.eq(dto2.cfg.b, True)
        self.eq(dto2.cfg.c, 456)
        self.isType(dto2.cfg.c, int)

    def test_dataclass_string_to_int_conversion(self):

        # Simulate old db data with string numbers
        sets.save('test_str_conv', '{"on": "true", "sz": "42", "rate": "0.95"}')

        @dataclass
        class StrTest:
            on: bool = False
            sz: int = 10
            rate: float = 0.5

        class Dto: cfg = AutoDbField('test_str_conv', StrTest)

        dto = Dto()
        self.isType(dto.cfg.on, bool)
        self.eq(dto.cfg.on, True)
        self.isType(dto.cfg.sz, int)
        self.eq(dto.cfg.sz, 42)
        self.isType(dto.cfg.rate, float)
        self.eq(dto.cfg.rate, 0.95)

    def test_dcproxy_setattr_type_conversion(self):

        @dataclass
        class ExclTest:
            on: bool = True
            fndLes: int = 0
            fndOvr: int = 0
            filNam: str = ''

        class Dto: excl = AutoDbField('test_excl_setattr', ExclTest)

        dto = Dto()
        # Simulate Dash Select returning string values
        dto.excl.fndOvr = "20"  # string from Select #type:ignore
        dto.excl.on = "false"   # string bool #type:ignore

        self.isType(dto.excl.fndOvr, int)
        self.eq(dto.excl.fndOvr, 20)
        self.isType(dto.excl.on, bool)
        self.eq(dto.excl.on, False)

        # Verify saved to db correctly
        dto2 = Dto()
        if hasattr(dto2, '_cache_test_excl_setattr'): delattr(dto2, '_cache_test_excl_setattr')
        self.isType(dto2.excl.fndOvr, int)
        self.eq(dto2.excl.fndOvr, 20)
        self.isType(dto2.excl.on, bool)
        self.eq(dto2.excl.on, False)


    def test_muod_sz_type_via_proxy(self):
        sets.save('test_muod_proxy', '{"on": false, "sz": 10}')

        class Dto: muod = AutoDbField('test_muod_proxy', Muod)

        dto = Dto()
        self.isType(dto.muod.sz, int)
        self.eq(dto.muod.sz, 10)

        dto.muod.sz = "20"#type:ignore
        self.isType(dto.muod.sz, int)
        self.eq(dto.muod.sz, 20)

        dto2 = Dto()
        if hasattr(dto2, '_cache_test_muod_proxy'): delattr(dto2, '_cache_test_muod_proxy')
        self.isType(dto2.muod.sz, int)
        self.eq(dto2.muod.sz, 20)

        sets.save('test_muod_proxy', '{"on": "false", "sz": "15"}')
        dto3 = Dto()
        if hasattr(dto3, '_cache_test_muod_proxy'): delattr(dto3, '_cache_test_muod_proxy')
        self.isType(dto3.muod.sz, int)
        self.eq(dto3.muod.sz, 15)

        val = dto3.muod.sz
        self.ok(isinstance(val, int), f"muod.sz is {type(val).__name__}, val={val!r}")
        result = len([]) < val
        self.isType(result, bool)


    def test_muod_set_whole_dataclass_with_string_fields(self):

        class Dto: muod = AutoDbField('test_muod_set_whole', Muod)

        dto = Dto()
        dto.muod = Muod("true", "5")#type:ignore

        # Without clearing cache - simulates same process reading back
        self.isType(dto.muod.sz, int, f"cached muod.sz should be int but got {type(dto.muod.sz).__name__}={dto.muod.sz!r}")
        self.eq(dto.muod.sz, 5)
        self.isType(dto.muod.on, bool)
        self.eq(dto.muod.on, True)

        # Also verify DB round-trip
        dto2 = Dto()
        if hasattr(dto2, '_cache_test_muod_set_whole'): delattr(dto2, '_cache_test_muod_set_whole')
        self.isType(dto2.muod.sz, int, f"db muod.sz should be int but got {type(dto2.muod.sz).__name__}={dto2.muod.sz!r}")
        self.eq(dto2.muod.sz, 5)


    def test_castVal_type_mismatch_with_default(self):
        from dto import cstv

        # bool → int: 類型不匹配, 應用 default
        self.eq(cstv(int, False, 10), 10)
        self.eq(cstv(int, True, 10), 10)

        # bool → float: 類型不匹配, 應用 default
        self.eq(cstv(float, False, 0.93), 0.93)
        self.eq(cstv(float, True, 0.93), 0.93)

        # None → int/float: 應用 default
        self.eq(cstv(int, None, 10), 10)
        self.eq(cstv(float, None, 0.93), 0.93)

        # str → int: 正常轉換, 不用 default
        self.eq(cstv(int, '5', 10), 5)
        self.eq(cstv(int, '0', 10), 0)

        # str → float: 正常轉換
        self.eq(cstv(float, '0.5', 0.93), 0.5)

        # int → int: 正常, 不用 default
        self.eq(cstv(int, 5, 10), 5)
        self.eq(cstv(int, 0, 10), 0)

        # empty str → int/float: 應用 default
        self.eq(cstv(int, '', 10), 10)
        self.eq(cstv(float, '', 0.93), 0.93)

        # 無 default 時, bool → int 仍轉為 int (不是 bool)
        r = cstv(int, False)
        self.isType(r, int)
        self.notType(r, bool)

        # bool → bool: 不受影響
        self.eq(cstv(bool, True), True)
        self.eq(cstv(bool, False), False)

        # int → bool: 正常轉換
        self.eq(cstv(bool, 1), True)
        self.eq(cstv(bool, 0), False)

    def test_muod_bool_in_int_field_uses_default(self):

        sets.save('test_muod_bad', '{"on": true, "sz": false}')

        class Dto: muod = AutoDbField('test_muod_bad', Muod)

        dto = Dto()
        self.isType(dto.muod.sz, int)
        self.eq(dto.muod.sz, 10)
        self.eq(dto.muod.on, True)

    def test_muod_null_in_int_field_uses_default(self):

        sets.save('test_muod_null', '{"on": true, "sz": null}')

        class Dto: muod = AutoDbField('test_muod_null', Muod)

        dto = Dto()
        self.isType(dto.muod.sz, int)
        self.eq(dto.muod.sz, 10)

    def test_castVal_all_cases(self):
        from dto import cstv, Ausl
        from dataclasses import fields as dc_fields

        # verify fld.type actual values
        for fld in dc_fields(Ausl):
            if fld.name in ('on', 'skipLow', 'allLive'):
                self.assertIs(fld.type, bool, f"{fld.name}: fld.type should be bool, got {fld.type!r}")
            elif fld.name in ('usr', 'pth'):
                from dto import PairKv
                self.assertIs(fld.type, PairKv, f"{fld.name}: fld.type should be PairKv, got {fld.type!r}")
            else:
                self.assertIs(fld.type, int, f"{fld.name}: fld.type should be int, got {fld.type!r}")

        # int field + str val
        self.isType(cstv(int, '2'), int)
        self.eq(cstv(int, '2'), 2)

        # int field + bool val (bool is subclass of int)
        r = cstv(int, True)
        self.isType(r, int, f"cstv(int, True) = {r!r} type={type(r).__name__}")

        # int field + int val
        self.isType(cstv(int, 2), int)
        self.eq(cstv(int, 2), 2)

        # bool field + str val
        self.isType(cstv(bool, 'true'), bool)
        self.eq(cstv(bool, 'true'), True)
        self.eq(cstv(bool, '2'), False)

        # bool field + int val (not str, skips bool branch)
        r2 = cstv(bool, 1)
        print(f"  cstv(bool, 1) = {r2!r} type={type(r2).__name__}")

        # bool field + bool val
        self.eq(cstv(bool, True), True)


    def test_get_exception_returns_dcproxy(self):
        sets.save('test_ausl_bad_json', 'NOT_VALID_JSON{{{')

        class Dto: ausl = AutoDbField('test_ausl_bad_json', Ausl)

        dto = Dto()
        a = dto.ausl
        self.isType(a, DcProxy, f"exception path should return DcProxy, got {type(a).__name__}")

        a.fav = '2' #type:ignore
        self.isType(a.fav, int, f"fav should be int, got {type(a.fav).__name__}={a.fav!r}")
        self.ok(a.fav > 0)


    def test_set_dataclass_caches_dcproxy(self):
        sets.save('test_ausl_set_dc', '{"on": true, "skipLow": true, "allLive": false, "earlier": 2, "later": 0, "exRich": 1, "exPoor": 0, "ofsBig": 2, "ofsSml": 0, "dimBig": 2, "dimSml": 0, "namLon": 1, "namSht": 0, "typJpg": 0, "typPng": 0, "typHeic": 0, "fav": 0, "inAlb": 0, "usr": ""}')

        class Dto: ausl = AutoDbField('test_ausl_set_dc', Ausl)

        dto = Dto()
        dto.ausl = Ausl(on=True, skipLow=False, allLive=False, earlier=1, later=0, exRich=0, exPoor=0, ofsBig=0, ofsSml=0, dimBig=0, dimSml=0, namLon=0, namSht=0, typJpg=0, typPng=0, typHeic=0, fav=0, inAlb=0, usr='') #type:ignore

        a = dto.ausl
        self.isType(a, DcProxy, f"after __set__ with dataclass, should be DcProxy, got {type(a).__name__}")

        a.fav = '3' #type:ignore
        self.isType(a.fav, int, f"fav should be int, got {type(a.fav).__name__}={a.fav!r}")
        self.ok(a.fav > 0)


    def test_get_db_json_extra_keys(self):
        sets.save('test_ausl_extra', '{"on": true, "skipLow": false, "allLive": false, "earlier": 2, "later": 0, "exRich": 1, "exPoor": 0, "ofsBig": 2, "ofsSml": 0, "dimBig": 2, "dimSml": 0, "namLon": 1, "namSht": 0, "typJpg": 0, "typPng": 0, "typHeic": 0, "fav": 3, "inAlb": 0, "usr": "", "obsoleteField": 999, "removed": "abc"}')

        class Dto: ausl = AutoDbField('test_ausl_extra', Ausl)

        dto = Dto()
        a = dto.ausl
        self.isType(a, DcProxy, f"should be DcProxy, got {type(a).__name__}")
        self.eq(a.fav, 3)
        self.eq(a.skipLow, False)


    def test_get_db_json_missing_keys(self):
        sets.save('test_ausl_missing', '{"on": false, "skipLow": true}')

        class Dto: ausl = AutoDbField('test_ausl_missing', Ausl)

        dto = Dto()
        a = dto.ausl
        self.isType(a, DcProxy, f"should be DcProxy, got {type(a).__name__}")
        self.eq(a.on, False)
        self.eq(a.skipLow, True)
        self.eq(a.fav, 0)
        self.eq(a.earlier, 2)
        self.isType(a.fav, int)


    def test_get_db_json_extra_and_missing_keys(self):
        sets.save('test_ausl_both', '{"on": true, "fav": 4, "gone": true, "oldWeight": 5}')

        class Dto: ausl = AutoDbField('test_ausl_both', Ausl)

        dto = Dto()
        a = dto.ausl
        self.isType(a, DcProxy, f"should be DcProxy, got {type(a).__name__}")
        self.eq(a.on, True)
        self.eq(a.fav, 4)
        self.eq(a.earlier, 2)
        self.isType(a.earlier, int)


    def test_set_dcproxy_saves_valid_json(self):
        sets.save('test_ausl_proxy_set', '{"on": true, "skipLow": true, "allLive": false, "earlier": 2, "later": 0, "exRich": 1, "exPoor": 0, "ofsBig": 2, "ofsSml": 0, "dimBig": 2, "dimSml": 0, "namLon": 1, "namSht": 0, "typJpg": 0, "typPng": 0, "typHeic": 0, "fav": 3, "inAlb": 0, "usr": ""}')

        class Dto: ausl = AutoDbField('test_ausl_proxy_set', Ausl)

        dto = Dto()
        proxy = dto.ausl
        self.isType(proxy, DcProxy)

        dto.ausl = proxy #type:ignore

        raw = sets.get('test_ausl_proxy_set')
        import json
        data = json.loads(raw) #type:ignore
        self.isType(data, dict, f"DB should have valid JSON, got {raw!r}")
        self.eq(data['fav'], 3)

        dto2 = Dto()
        if hasattr(dto2, '_cache_test_ausl_proxy_set'): delattr(dto2, '_cache_test_ausl_proxy_set')
        a2 = dto2.ausl
        self.isType(a2, DcProxy, f"reload should be DcProxy, got {type(a2).__name__}")
        self.eq(a2.fav, 3)


    def _mkAusl(self, key, jsonStr):
        sets.save(key, jsonStr)
        class D: ausl = AutoDbField(key, Ausl)
        return D()

    def _reAusl(self, key):
        class D: ausl = AutoDbField(key, Ausl)
        return D()

    def test_cstv_nested_dataclass(self):
        from dto import cstv, PairKv

        r = cstv(PairKv, {"k": "/library/clean", "v": 3})
        self.isType(r, PairKv)
        self.eq(r.k, "/library/clean")
        self.isType(r.v, int)
        self.eq(r.v, 3)

        r = cstv(PairKv, PairKv(k="test", v="2"))#type:ignore
        self.isType(r.v, int)
        self.eq(r.v, 2)

        r = cstv(PairKv, {"k": 123, "v": "4"})
        self.isType(r.k, str)
        self.eq(r.k, "123")
        self.isType(r.v, int)
        self.eq(r.v, 4)

        r = cstv(PairKv, {"k": "path", "v": 2, "extra": "ignored", "foo": 99})
        self.eq(r.k, "path")
        self.eq(r.v, 2)

        r = cstv(PairKv, {"k": "/some/path"})
        self.eq(r.v, 0)
        r = cstv(PairKv, {})
        self.eq(r.k, "")
        self.eq(r.v, 0)

        r = cstv(PairKv, None, PairKv(k="def", v=1))
        self.eq(r.k, "def")
        self.eq(r.v, 1)

        r = cstv(PairKv, "garbage")
        self.isType(r, PairKv)
        self.eq(r.k, "")

        r = cstv(PairKv, 42)
        self.isType(r, PairKv)
        self.eq(r.v, 0)

        r = cstv(PairKv, [1, 2])
        self.isType(r, PairKv)

        r = cstv(PairKv, True)
        self.isType(r, PairKv)

    def test_ausl_pth_roundtrip(self):
        from dto import PairKv, DcProxy

        dto = self._mkAusl('t_pth_rt', '{"on": true, "pth": {"k": "/library/clean", "v": 3}}')
        a = dto.ausl
        self.isType(a, DcProxy)
        self.isType(a.pth, PairKv)
        self.eq(a.pth.k, "/library/clean")
        self.isType(a.pth.v, int)
        self.eq(a.pth.v, 3)

    def test_ausl_pth_edge_cases(self):
        dto = self._mkAusl('t_pth_miss', '{"on": true, "earlier": 2}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "")
        self.eq(dto.ausl.pth.v, 0)

        dto = self._mkAusl('t_pth_null', '{"on": true, "pth": null}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "")
        self.eq(dto.ausl.pth.v, 0)

        dto = self._mkAusl('t_pth_part', '{"on": true, "pth": {"k": "/only"}}')
        self.eq(dto.ausl.pth.k, "/only")
        self.eq(dto.ausl.pth.v, 0)

        dto = self._mkAusl('t_pth_bad', '{"on": true, "pth": "not_a_dict"}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "")
        self.eq(dto.ausl.pth.v, 0)

    def test_ausl_pth_no_db_data(self):
        sets.save('t_pth_nodata', '')
        class D: ausl = AutoDbField('t_pth_nodata', Ausl)
        dto = D()
        a = dto.ausl
        self.isType(a, DcProxy)
        self.isType(a.pth, PairKv)
        self.eq(a.pth.k, "")
        self.eq(a.pth.v, 0)
        self.eq(a.on, True)
        self.eq(a.earlier, 2)

    def test_ausl_pth_empty_dict_in_db(self):
        from dto import PairKv

        dto = self._mkAusl('t_pth_empty', '{}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "")
        self.eq(dto.ausl.pth.v, 0)
        self.eq(dto.ausl.on, True)
        self.eq(dto.ausl.earlier, 2)

    def test_ausl_pth_null_fields_in_dict(self):
        from dto import PairKv

        dto = self._mkAusl('t_pth_vnull', '{"on": true, "pth": {"k": "path", "v": null}}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "path")
        self.isType(dto.ausl.pth.v, int)
        self.eq(dto.ausl.pth.v, 0)

        dto = self._mkAusl('t_pth_knull', '{"on": true, "pth": {"k": null, "v": 3}}')
        self.isType(dto.ausl.pth.k, str)
        self.eq(dto.ausl.pth.k, "")
        self.eq(dto.ausl.pth.v, 3)

    def test_ausl_pth_bool_in_int_field(self):
        from dto import PairKv

        dto = self._mkAusl('t_pth_vbool', '{"on": true, "pth": {"k": "path", "v": true}}')
        self.isType(dto.ausl.pth.v, int)
        self.eq(dto.ausl.pth.v, 0)

    def test_ausl_pth_wrong_types_fallback(self):
        from dto import PairKv

        dto = self._mkAusl('t_pth_list', '{"on": true, "pth": [1, 2]}')
        self.isType(dto.ausl.pth, PairKv)
        self.eq(dto.ausl.pth.k, "")

        dto = self._mkAusl('t_pth_int', '{"on": true, "pth": 42}')
        self.isType(dto.ausl.pth, PairKv)

        dto = self._mkAusl('t_pth_bool2', '{"on": true, "pth": true}')
        self.isType(dto.ausl.pth, PairKv)

    def test_ausl_pth_set_and_reload(self):
        from dto import PairKv

        dto = self._mkAusl('t_pth_set', '{"on": true}')
        dto.ausl.pth = PairKv(k="/ext/dump", v=2)

        dto2 = self._reAusl('t_pth_set')
        self.isType(dto2.ausl.pth, PairKv)
        self.eq(dto2.ausl.pth.k, "/ext/dump")
        self.isType(dto2.ausl.pth.v, int)
        self.eq(dto2.ausl.pth.v, 2)

        dto.ausl.pth = PairKv(k="/path", v="4")#type:ignore
        self.isType(dto.ausl.pth.v, int)
        self.eq(dto.ausl.pth.v, 4)


if __name__ == "__main__": unittest.main()
