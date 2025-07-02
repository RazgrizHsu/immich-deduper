import json
import logging
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mod.models import BaseDictModel, Json
from util import log

lg = log.get(__name__)

@dataclass
class SimpleAsset(BaseDictModel):
    id: str
    originalFileName: str
    fileCreatedAt: str
    fileModifiedAt: str
    isFavorite: int = 0
    isVectored: int = 0
    simOk: int = 0
    ownerId: str = ""
    deviceId: str = ""
    type: str = ""

@dataclass
class Address(BaseDictModel):
    street: str
    city: str
    zip_code: str
    country: Optional[str] = None

@dataclass
class Contact(BaseDictModel):
    email: str
    phone: Optional[str] = None

@dataclass
class Tag(BaseDictModel):
    name: str
    color: str

@dataclass
class ComplexAsset(BaseDictModel):
    id: str
    originalFileName: str
    fileCreatedAt: str
    owner: Contact
    tags: List[Tag]
    locations: List[Address] = None
    metadata: Json = None


# noinspection SqlResolve
def setup_simple_test_db(num_records: int = 1000) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    cursor.execute('''
	Create Table If Not Exists simple_assets (
		id TEXT Primary Key,
		ownerId TEXT,
		deviceId TEXT,
		type TEXT,
		originalFileName TEXT,
		fileCreatedAt TEXT,
		fileModifiedAt TEXT,
		isFavorite INTEGER,
		isVisible INTEGER,
		isArchived INTEGER,
		isVectored INTEGER,
		simOk INTEGER
	)
	''')

    for i in range(num_records):
        cursor.execute('''
		Insert Into simple_assets Values (
			?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
		)
		''', (
            f"id-{i}",
            f"owner-{i % 10}",
            f"device-{i % 5}",
            "image",
            f"image_{i}.jpg",
            f"2023-01-{(i % 28) + 1:02d}",
            f"2023-02-{(i % 28) + 1:02d}",
            i % 2,
            1,
            0,
            i % 3,
            i % 2
        ))

    conn.commit()
    return conn


def setup_complex_test_db(num_records: int = 1000) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    cursor.execute('''
	Create Table If Not Exists complex_assets (
		id TEXT Primary Key,
		originalFileName TEXT,
		fileCreatedAt TEXT,
		owner TEXT,
		tags TEXT,
		locations TEXT,
		metadata TEXT,
		isVisible INTEGER,
		isArchived INTEGER
	)
	''')

    for i in range(num_records):
        owner = {
            "email": f"user{i}@example.com",
            "phone": f"555-{i:04d}" if i % 2 == 0 else None
        }

        tags = []
        for j in range(1, (i % 3) + 1):
            tags.append({
                "name": f"tag{j}",
                "color": f"color{(i + j) % 5}"
            })

        locations = []
        for j in range(1, (i % 2) + 2):
            locations.append({
                "street": f"{j * 100 + i} Main St",
                "city": f"City {(i + j) % 10}",
                "zip_code": f"{10000 + i * j}",
                "country": f"Country {j}" if j % 2 == 0 else None
            })

        metadata = {
            "created": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "size": i * 1024,
            "settings": {
                "quality": "high" if i % 2 == 0 else "medium",
                "shared": i % 3 == 0
            }
        }

        # noinspection SqlResolve
        sql = "Insert Into complex_assets Values ( ?, ?, ?, ?, ?, ?, ?, ?, ? )"
        cursor.execute( sql, (
            f"id-{i}",
            f"complex_image_{i}.jpg",
            f"2023-01-{(i % 28) + 1:02d}",
            json.dumps(owner),
            json.dumps(tags),
            json.dumps(locations),
            json.dumps(metadata),
            1,
            0
        ))

    conn.commit()
    return conn


# noinspection SqlResolve
sql_select_complex_assets = "Select * From complex_assets"
# noinspection SqlResolve
sql_select_simple_assets = "Select * From simple_assets"

def method1_simple_dict_zip(cursor: sqlite3.Cursor):
    start_time = time.time()

    cursor.execute(sql_select_simple_assets)

    columns = [col[0] for col in cursor.description]
    result = []

    for row in cursor.fetchall():
        asset = dict(zip(columns, row))
        result.append(asset)

    end_time = time.time()
    execution_time = end_time - start_time
    lg.info(f"Method 1 (dict(zip)) simple data: {execution_time:.6f} seconds")

    return result, execution_time

def method2_simple_base_dict_model(cursor: sqlite3.Cursor):
    start_time = time.time()

    cursor.execute(sql_select_simple_assets)

    result = []
    for row in cursor.fetchall():
        asset = SimpleAsset.fromDB(cursor, row)
        result.append(asset)

    end_time = time.time()
    execution_time = end_time - start_time
    lg.info(f"Method 2 (BaseDictModel.fromDB) simple data: {execution_time:.6f} seconds")

    return result, execution_time


def method3_complex_dict_zip(cursor: sqlite3.Cursor):
    start_time = time.time()

    cursor.execute(sql_select_complex_assets)

    columns = [col[0] for col in cursor.description]
    result = []

    for row in cursor.fetchall():
        asset = dict(zip(columns, row))

        json_fields = ['owner', 'tags', 'locations', 'metadata']
        for field in json_fields:
            if field in asset and asset.get(field):
                try:
                    asset[field] = json.loads(asset[field])
                except:
                    asset[field] = None

        result.append(asset)

    end_time = time.time()
    execution_time = end_time - start_time
    lg.info(f"Method 3 (dict(zip) + JSON parsing) complex data: {execution_time:.6f} seconds")

    return result, execution_time


def method4_complex_base_dict_model(cursor: sqlite3.Cursor):
    start_time = time.time()

    cursor.execute(sql_select_complex_assets)

    columns = [col[0] for col in cursor.description]
    result = []

    for row in cursor.fetchall():
        data = dict(zip(columns, row))

        json_fields = ['owner', 'tags', 'locations', 'metadata']
        for field in json_fields:
            if field in data and data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except:
                    data[field] = None

        asset = ComplexAsset.fromDic(data)
        result.append(asset)

    end_time = time.time()
    execution_time = end_time - start_time
    lg.info(f"Method 4 (BaseDictModel.fromDict) complex data: {execution_time:.6f} seconds")

    return result, execution_time


def run_simple_test(iterations: int = 5, num_records: int = 1000, silent: bool = False):
    if not silent:
        lg.info(f"Starting simple data performance test: reading {num_records} records, testing {iterations} times")

    method1_times = []
    method2_times = []

    for i in range(iterations):
        if not silent:
            lg.info(f"Running test {i + 1}...")

        conn = setup_simple_test_db(num_records)
        cursor = conn.cursor()

        _, time1 = method1_simple_dict_zip(cursor)
        method1_times.append(time1)

        _, time2 = method2_simple_base_dict_model(cursor)
        method2_times.append(time2)

        conn.close()

    avg_time1 = sum(method1_times) / len(method1_times)
    avg_time2 = sum(method2_times) / len(method2_times)

    speedup = avg_time2 / avg_time1 if avg_time1 > 0 else 0

    if not silent:
        lg.info("=" * 50)
        lg.info(f"Simple data test completed: read {num_records} records, tested {iterations} times")
        lg.info(f"Method 1 (dict(zip)) average time: {avg_time1:.6f} seconds")
        lg.info(f"Method 2 (BaseDictModel.fromDB) average time: {avg_time2:.6f} seconds")
        lg.info(f"Performance gap: BaseDictModel.fromDB takes {speedup:.2f} times longer than dict(zip)")
        lg.info(f"       => dict(zip) is {speedup:.2f} times faster than BaseDictModel.fromDB")
        lg.info("=" * 50)

    return avg_time1, avg_time2


def run_complex_test(iterations: int = 5, num_records: int = 1000, silent: bool = False):
    if not silent:
        lg.info(f"Starting complex data performance test: reading {num_records} records, testing {iterations} times")

    method3_times = []
    method4_times = []

    for i in range(iterations):
        if not silent:
            lg.info(f"Running test {i + 1}...")

        conn = setup_complex_test_db(num_records)
        cursor = conn.cursor()

        _, time3 = method3_complex_dict_zip(cursor)
        method3_times.append(time3)

        _, time4 = method4_complex_base_dict_model(cursor)
        method4_times.append(time4)

        conn.close()

    avg_time3 = sum(method3_times) / len(method3_times)
    avg_time4 = sum(method4_times) / len(method4_times)

    speedup = avg_time4 / avg_time3 if avg_time3 > 0 else 0

    if not silent:
        lg.info("=" * 50)
        lg.info(f"Complex data test completed: read {num_records} records, tested {iterations} times")
        lg.info(f"Method 3 (dict(zip) + JSON parsing) average time: {avg_time3:.6f} seconds")
        lg.info(f"Method 4 (BaseDictModel.fromDict) average time: {avg_time4:.6f} seconds")
        lg.info(f"Performance gap: BaseDictModel.fromDict takes {speedup:.2f} times longer than dict(zip)+JSON parsing")
        lg.info(f"       => dict(zip)+JSON parsing is {speedup:.2f} times faster than BaseDictModel.fromDict")
        lg.info("=" * 50)

    return avg_time3, avg_time4


def run_nested_object_test(iterations: int = 3, num_records: int = 100, silent: bool = False):
    if not silent:
        lg.info(f"Starting nested object creation performance test: creating {num_records} records, testing {iterations} times")

    method_dict_times = []
    method_model_times = []

    for i in range(iterations):
        if not silent:
            lg.info(f"Running test {i + 1}...")

        test_data = []
        for j in range(num_records):
            data = {
                'id': f"id-{j}",
                'originalFileName': f"nested_image_{j}.jpg",
                'fileCreatedAt': f"2023-01-{(j % 28) + 1:02d}",
                'owner': {
                    "email": f"user{j}@example.com",
                    "phone": f"555-{j:04d}" if j % 2 == 0 else None
                },
                'tags': [
                    {
                        "name": f"tag{k}",
                        "color": f"color{(j + k) % 5}"
                    } for k in range(1, (j % 3) + 1)
                ],
                'locations': [
                    {
                        "street": f"{k * 100 + j} Main St",
                        "city": f"City {(j + k) % 10}",
                        "zip_code": f"{10000 + j * k}",
                        "country": f"Country {k}" if k % 2 == 0 else None
                    } for k in range(1, (j % 2) + 2)
                ],
                'metadata': {
                    "created": f"2023-{(j % 12) + 1:02d}-{(j % 28) + 1:02d}",
                    "size": j * 1024,
                    "settings": {
                        "quality": "high" if j % 2 == 0 else "medium",
                        "shared": j % 3 == 0
                    }
                }
            }
            test_data.append(data)

        start_time = time.time()
        dict_results = []
        for data in test_data:
            result = {key: value for key, value in data.items()}
            dict_results.append(result)
        dict_time = time.time() - start_time
        method_dict_times.append(dict_time)
        if not silent:
            lg.info(f"Pure dictionary processing time: {dict_time:.6f} seconds")

        start_time = time.time()
        model_results = []
        for data in test_data:
            model = ComplexAsset.fromDic(data)
            model_results.append(model)
        model_time = time.time() - start_time
        method_model_times.append(model_time)
        if not silent:
            lg.info(f"BaseDictModel processing time: {model_time:.6f} seconds")

    avg_dict_time = sum(method_dict_times) / len(method_dict_times)
    avg_model_time = sum(method_model_times) / len(method_model_times)

    speedup = avg_model_time / avg_dict_time if avg_dict_time > 0 else 0

    if not silent:
        lg.info("=" * 50)
        lg.info(f"Nested object creation test completed: processed {num_records} records, tested {iterations} times")
        lg.info(f"Pure dictionary processing average time: {avg_dict_time:.6f} seconds")
        lg.info(f"BaseDictModel processing average time: {avg_model_time:.6f} seconds")
        lg.info(f"Performance gap: BaseDictModel processing takes {speedup:.2f} times longer than pure dictionary")
        lg.info(f"       => Pure dictionary processing is {speedup:.2f} times faster than BaseDictModel")
        lg.info("=" * 50)

    return avg_dict_time, avg_model_time


def run_all_tests(small_only: bool = False):
    log.setLog(logging.INFO)
    lg.info("=" * 80)
    lg.info("Starting comprehensive test: BaseDictModel vs dictionary processing")
    lg.info("=" * 80)

    lg.info("Warm-up test in progress...")
    _ = run_simple_test(iterations=1, num_records=100, silent=True)
    _ = run_complex_test(iterations=1, num_records=100, silent=True)
    _ = run_nested_object_test(iterations=1, num_records=50, silent=True)

    lg.info("\n## Small test (1000 records)")
    simple_time1, simple_time2 = run_simple_test(iterations=5, num_records=1000)
    complex_time1, complex_time2 = run_complex_test(iterations=5, num_records=1000)
    nested_time1, nested_time2 = run_nested_object_test(iterations=3, num_records=100)

    if not small_only:
        lg.info("\n## Large test (10000 records)")
        lg.info("Note: This may take more time to run...")
        large_simple_time1, large_simple_time2 = run_simple_test(iterations=2, num_records=10000)
        large_complex_time1, large_complex_time2 = run_complex_test(iterations=2, num_records=5000)
    else:
        large_simple_time1, large_simple_time2 = simple_time1, simple_time2
        large_complex_time1, large_complex_time2 = complex_time1, complex_time2

    lg.info("\n" + "=" * 80)
    lg.info("BaseDictModel vs dictionary processing: Comprehensive performance report")
    lg.info("=" * 80)

    lg.info("\nSmall dataset (1000 records):")
    lg.info(f"Simple data - dict(zip) vs BaseDictModel: {simple_time1:.6f}s vs {simple_time2:.6f}s => Speed ratio: {simple_time2 / simple_time1:.2f}x")
    lg.info(f"Complex data - dict+JSON vs BaseDictModel: {complex_time1:.6f}s vs {complex_time2:.6f}s => Speed ratio: {complex_time2 / complex_time1:.2f}x")
    lg.info(f"Nested objects - Pure dict vs BaseDictModel: {nested_time1:.6f}s vs {nested_time2:.6f}s => Speed ratio: {nested_time2 / nested_time1:.2f}x")

    lg.info("\nLarge dataset:")
    lg.info(f"Simple data (10000 records) - dict(zip) vs BaseDictModel: {large_simple_time1:.6f}s vs {large_simple_time2:.6f}s => Speed ratio: {large_simple_time2 / large_simple_time1:.2f}x")
    lg.info(f"Complex data (5000 records) - dict+JSON vs BaseDictModel: {large_complex_time1:.6f}s vs {large_complex_time2:.6f}s => Speed ratio: {large_complex_time2 / large_complex_time1:.2f}x")

    lg.info("\nSummary:")
    avg_simple_ratio = ((simple_time2 / simple_time1) + (large_simple_time2 / large_simple_time1)) / 2
    avg_complex_ratio = ((complex_time2 / complex_time1) + (large_complex_time2 / large_complex_time1)) / 2

    lg.info(f"Simple data: dict(zip) is on average {avg_simple_ratio:.2f}x faster than BaseDictModel")
    lg.info(f"Complex data: dict+JSON is on average {avg_complex_ratio:.2f}x faster than BaseDictModel")
    lg.info(f"Nested objects: Pure dictionary processing is on average {nested_time2 / nested_time1:.2f}x faster than BaseDictModel")

    lg.info("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test performance differences between BaseDictModel and dict processing')
    parser.add_argument('--small', action='store_true', help='Run only small tests (skip large data tests)')
    args = parser.parse_args()

    run_all_tests(small_only=args.small)
