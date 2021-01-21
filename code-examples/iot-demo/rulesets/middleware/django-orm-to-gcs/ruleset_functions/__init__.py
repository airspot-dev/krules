from google.cloud import storage
from krules_core.base_functions import RuleFunctionBase
from cloudstorage.drivers.google import GoogleStorageDriver


class CreateGCSFolder(RuleFunctionBase):

    def execute(self, bucket, path):
        client = storage.Client()
        bucket = client.get_bucket(bucket)
        blob = bucket.blob(path)
        blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')


class DeleteGCSFolder(RuleFunctionBase):

    def execute(self, bucket, path):
        driver = GoogleStorageDriver()
        container = driver.get_container(bucket)
        for blob in driver.get_blobs(container):
            if blob.name.startswith(path):
                driver.delete_blob(blob)
