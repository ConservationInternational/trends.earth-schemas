from marshmallow import Schema, fields, post_load


################################################################################
# Schema for numeric data for plotting within a timeseries object

class TimeSeries(object):
    def __init__(self, time, y, name=None):
        self.time = time
        self.y = y
        self.name = name


class TimeSeriesSchema(Schema):
    time = fields.List(fields.Float())
    y = fields.List(fields.Float())
    name = fields.Str()


class TimeSeriesTable(object):
    def __init__(self, name, table):
        self.type = "TimeSeriesTable"
        self.name = name
        self.table = table


class TimeSeriesTableSchema(Schema):
    type = fields.Str()
    name = fields.Str()
    table = fields.Nested(TimeSeriesSchema, many=True)


################################################################################
# Schema for storing information on bands

class BandInfo(object):
    def __init__(self, name, add_to_map=False, activated=True, metadata={}, 
                 no_data_value=-32768):
        self.name = name
        self.no_data_value = no_data_value
        self.add_to_map = add_to_map
        self.activated = activated
        self.metadata = metadata

class BandInfoSchema(Schema):
    name = fields.Str(required=True)
    no_data_value = fields.Number(required=True)
    add_to_map = fields.Boolean(default=False)
    activated = fields.Boolean(default=True)
    metadata = fields.Dict(required=True)


################################################################################
# Schema for output from cloud calculations

class Url(object):
    def __init__(self, url, md5Hash):
        self.url = url
        self.md5Hash = md5Hash


class UrlSchema(Schema):
    url = fields.Url()
    md5Hash = fields.Str()


class CloudResults(object):
    def __init__(self, name, bands, urls):
        self.type = "CloudResults"
        self.name = name
        self.bands = bands
        self.urls = urls


class CloudResultsSchema(Schema):
    type = fields.Str()
    name = fields.Str()
    bands = fields.Nested(BandInfoSchema, many=True)
    urls = fields.Nested(UrlSchema, many=True)

    @post_load
    def make_cloud_results(self, data, **kwargs):
        data.pop('type')
        return CloudResults(**data)

################################################################################
# Schema for responses from api.trends.earth

class APIResponseSchema(Schema):
    end_date = fields.DateTime(required=True)
    id = fields.Str(required=True)
    params = fields.Dict(required=True)
    progress = fields.Integer()
    results = fields.Dict(required=True)
    script = fields.Dict(required=True)
    script_id = fields.UUID(required=True)
    start_date = fields.DateTime(required=True)
    status = fields.Str()
    user_id = fields.UUID()


################################################################################
# Schema used for all TE results (cloud or local)

class LocalRaster(object):
    def __init__(self, file, bands, metadata):
        self.file = file
        self.bands = bands
        self.metadata = metadata


class LocalRasterSchema(Schema):
    file = fields.Str(required=True)
    bands = fields.Nested(BandInfoSchema, required=True, many=True)
    metadata = fields.Dict(required=True)


class LocalTable(object):
    def __init__(self, data, metadata):
        self.data = data
        self.metadata = metadata


class LocalTableSchema(Schema):
    data = fields.Nested(TimeSeriesTableSchema)
    metadata = fields.Dict()
