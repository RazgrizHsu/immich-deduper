import unittest
import os
import sys
import re
from typing import Optional
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from conf import envs

class TestPathProcessing(unittest.TestCase):
    @staticmethod
    def valid(path: Optional[str]) -> bool:
        if not path: return False

        thumbs_pattern = r'^(.*/)?thumbs/[0-9a-fA-F-]+/[0-9a-fA-F]{2}/[0-9a-fA-F]{2}/[0-9a-fA-F-]+-(thumbnail|preview)\.(webp|jpg|jpeg|png)$'
        encoded_video_pattern = r'^(.*/)?encoded-video/[0-9a-fA-F-]+/[0-9a-fA-F]{2}/[0-9a-fA-F]{2}/[0-9a-fA-F-]+\.(mp4|mov|avi|mkv)$'
        return bool(re.match(thumbs_pattern, path)) or bool(re.match(encoded_video_pattern, path))

    def setUp(self):
        self.sample_immich_path = "/immich"
        envs.immichPath = self.sample_immich_path

    def test_base_standard_upload_format(self):
        path = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        result = envs.pth.base(path)
        expected = "6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        self.assertEqual(result, expected)

    def test_base_photos_format(self):
        path = "/photos/thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        result = envs.pth.base(path)
        expected = "9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        self.assertEqual(result, expected)

    def test_base_direct_thumbs_format(self):
        path = "thumbs/ba33507d-6a33-4034-ba1c-870c1ef59472/ba/33/ba33507d-6a33-4034-ba1c-870c1ef59472-thumbnail.webp"
        result = envs.pth.base(path)
        expected = "ba33507d-6a33-4034-ba1c-870c1ef59472/ba/33/ba33507d-6a33-4034-ba1c-870c1ef59472-thumbnail.webp"
        self.assertEqual(result, expected)

    def test_base_invalid_path(self):
        path = "some/invalid/path/without/thumbs"
        result = envs.pth.base(path)
        self.assertEqual(result, "")

    def test_base_empty_path(self):
        result = envs.pth.base("")
        self.assertEqual(result, "")

        result = envs.pth.base(None)
        self.assertEqual(result, "")

    def test_normalize_upload_format(self):
        path = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        result = envs.pth.normalize(path)
        expected = "thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        self.assertEqual(result, expected)

    def test_normalize_photos_format(self):
        path = "/photos/thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        result = envs.pth.normalize(path)
        expected = "thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        self.assertEqual(result, expected)

    def test_normalize_non_thumbs_path(self):
        path = "some/other/path/file.jpg"
        result = envs.pth.normalize(path)
        self.assertEqual(result, path)

    def test_full_upload_format(self):
        path = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        result = envs.pth.full(path)
        expected = "/immich/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        self.assertEqual(result, expected)

    def test_full_photos_format(self):
        path = "/photos/thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        result = envs.pth.full(path)
        expected = "/immich/thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-thumbnail.webp"
        self.assertEqual(result, expected)

    def test_full_already_full_path(self):
        path = "/immich/thumbs/ba33507d-6a33-4034-ba1c-870c1ef59472/ba/33/ba33507d-6a33-4034-ba1c-870c1ef59472-thumbnail.webp"
        result = envs.pth.full(path)
        self.assertEqual(result, path)

    def test_validate_valid_thumbnail(self):
        path = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-thumbnail.webp"
        result = self.valid(path)
        self.assertTrue(result)

    def test_validate_valid_preview(self):
        path = "/photos/thumbs/9613663b-7f24-49c1-94e0-4568a1e29550/a3/d6/a3d69159-626f-4b3d-8465-670da7f2a2a3-preview.webp"
        result = self.valid(path)
        self.assertTrue(result)

    def test_validate_invalid_format(self):
        path = "some/invalid/path.jpg"
        result = self.valid(path)
        self.assertFalse(result)

    def test_buildForImage_thumbnail_priority(self):
        pathThumb = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-thumbnail.webp"
        pathPreview = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        result = envs.pth.forImg(pathThumb, pathPreview)
        expected = "/immich/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-thumbnail.webp"
        self.assertEqual(result, expected)

    def test_buildForImage_preview_requested(self):
        from conf import ks
        pathThumb = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-thumbnail.webp"
        pathPreview = "upload/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        result = envs.pth.forImg(pathThumb, pathPreview, ks.db.preview)
        expected = "/immich/thumbs/6b38913a-09c0-40b6-82e6-6bbc1294e550/1c/4f/1c4f7997-98a0-4b67-88c1-f5611a5aa499-preview.webp"
        self.assertEqual(result, expected)

    def test_base_encoded_video_format(self):
        path = "upload/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        result = envs.pth.base(path)
        expected = "f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        self.assertEqual(result, expected)

    def test_normalize_encoded_video_format(self):
        path = "upload/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        result = envs.pth.normalize(path)
        expected = "encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        self.assertEqual(result, expected)

    def test_full_encoded_video_format(self):
        path = "upload/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        result = envs.pth.full(path)
        expected = "/immich/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        self.assertEqual(result, expected)

    def test_validate_valid_encoded_video(self):
        path = "upload/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4"
        result = self.valid(path)
        self.assertTrue(result)

    def test_edge_cases_different_prefixes(self):
        test_cases = [
            "data/thumbs/uuid/12/34/uuid-thumbnail.webp",
            "storage/thumbs/uuid/ab/cd/uuid-preview.webp",
            "media/thumbs/uuid/ef/gh/uuid-thumbnail.jpg",
            "files/thumbs/uuid/56/78/uuid-preview.png"
        ]

        for path in test_cases:
            result = envs.pth.full(path)
            self.assertTrue(result.startswith(self.sample_immich_path))
            self.assertIn("thumbs/", result)

if __name__ == '__main__':
    unittest.main()
