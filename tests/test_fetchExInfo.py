#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from db import psql
from conf import envs

def test_fetchExInfo():
    print("=== Testing fetchExInfo ===")

    # Test asset ID
    testAssetId = "120ce167-9910-41bb-ba8d-09ef9a730ac3"

    try:
        # Test single fetchExInfo
        print(f"Testing fetchExInfo with assetId: {testAssetId}")
        exInfo = psql.fetchExInfo(testAssetId)

        print(f"Albums count: {len(exInfo.albs)}")
        for alb in exInfo.albs:
            print(f"  - Album: {alb.albumName} (ID: {alb.id})")

        print(f"Faces count: {len(exInfo.facs)}")
        for fac in exInfo.facs:
            print(f"  - Face: {fac.name} (Person ID: {fac.personId}, Owner: {fac.ownerId})")

        print(f"Tags count: {len(exInfo.tags)}")
        for tag in exInfo.tags:
            print(f"  - Tag: {tag.value} (ID: {tag.id}, User: {tag.userId})")

        # Test batch fetchExInfos
        print(f"\nTesting fetchExInfos with single asset in list...")
        exInfos = psql.fetchExInfos([testAssetId])

        print(f"Batch exInfos keys: {list(exInfos.keys())}")
        if testAssetId in exInfos:
            batchExInfo = exInfos[testAssetId]
            print(f"Batch result - Albums: {len(batchExInfo.albs)}, Faces: {len(batchExInfo.facs)}, Tags: {len(batchExInfo.tags)}")
            if batchExInfo.albs:
                for alb in batchExInfo.albs:
                    print(f"  Batch Album: {alb.albumName}")
        else:
            print("Asset not found in batch result")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fetchExInfo()
