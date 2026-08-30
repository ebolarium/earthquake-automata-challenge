import io
import os
import unittest
from unittest.mock import patch

from etas_challenge.object_storage import ObjectStorageConfig
from etas_challenge.object_storage import object_key
from etas_challenge.object_storage import storage_health
from etas_challenge.object_storage import write_read_delete_probe


class FakeS3:
    def __init__(self):
        self.objects = {}

    def list_objects_v2(self, **kwargs):
        return {"KeyCount": 0}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, Bucket, Key):
        del self.objects[(Bucket, Key)]


class ObjectStorageTest(unittest.TestCase):
    def setUp(self):
        self.config = ObjectStorageConfig(
            endpoint_url="https://hel1.example.test",
            bucket="test-bucket",
            region="us-east-1",
            access_key_id="access",
            secret_access_key="secret",
            prefix="prospective/v1",
        )

    def test_environment_contract(self):
        environment = {
            "S3_ENDPOINT_URL": "https://hel1.example.test",
            "S3_BUCKET": "test-bucket",
            "S3_REGION": "us-east-1",
            "S3_ACCESS_KEY_ID": "access",
            "S3_SECRET_ACCESS_KEY": "secret",
            "S3_PREFIX": "/prospective/v1/",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = ObjectStorageConfig.from_environment()
        self.assertEqual(config.prefix, "prospective/v1")
        self.assertEqual(object_key(config, "forecasts/day.json"), "prospective/v1/forecasts/day.json")

    def test_probe_verifies_and_removes_object(self):
        client = FakeS3()
        result = write_read_delete_probe(self.config, client)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(client.objects, {})
        self.assertEqual(storage_health(self.config, client), (True, None))

    def test_missing_settings_are_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "missing object storage settings"):
                ObjectStorageConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
