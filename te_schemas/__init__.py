from marshmallow import Schema

class SchemaBase(Schema):
    '''Base class for te_schemas schemas'''
    def validate(self):
        '''Validate this instance (for example after making changes)'''
        data, errors = self.Schema().dump(self)
        self.Schema().validate(data)

    def as_json(self):
        '''Export instance to json'''
        self.Schema().dumps(self)
