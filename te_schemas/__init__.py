from marshmallow_dataclass import class_schema

class SchemaBase:
    '''Base class for te_schemas schemas'''
    def validate(self):
        '''Validate this instance (for example after making changes)'''
        data, errors = self.Schema().dump(self)
        self.Schema().validate(data)

    def dump(self):
        '''Serialize to Python datatypes'''
        return self.__class__.Schema().dump(self)

    def dumps(self):
        '''Serialize to json-formatted text'''
        return self.__class__.Schema().dumps(self)
