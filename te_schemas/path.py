import pathlib
import re

import marshmallow_dataclass
from marshmallow import fields
from marshmallow.exceptions import ValidationError


class FilePathField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str):
            raise ValidationError
        if re.match(r"/vsi(s3)|(gs)", str(value)) is not None:
            # Don't convert direction of slashes for GDAL vsi uris, as will
            # confuse GDAL

            return pathlib.PurePosixPath(value)
        else:
            return pathlib.Path(value)


FilePath = marshmallow_dataclass.NewType("FilePath", str, field=FilePathField)
