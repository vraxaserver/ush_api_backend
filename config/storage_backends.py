"""
Custom S3 storage backends.

StaticStorage  → s3://<bucket>/static/...   (used by collectstatic)
MediaStorage   → s3://<bucket>/media/...    (used for all file/image uploads)

Both inherit from S3Boto3Storage and read global AWS_* settings from Django
settings, overriding only the location (key prefix).

NOTE: These classes are only ever imported / used when USE_S3 is True
(i.e. DEBUG=False and ENV != 'local'), so the AWS_* settings are guaranteed
to exist in settings at that point.
"""

from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Store static files under the 'static/' prefix in S3."""

    location = "static"
    default_acl = None
    file_overwrite = True   # collectstatic is idempotent – overwrite is fine


class MediaStorage(S3Boto3Storage):
    """Store user-uploaded media files under the 'media/' prefix in S3."""

    location = "media"
    default_acl = None
    file_overwrite = False  # Never silently overwrite user uploads
