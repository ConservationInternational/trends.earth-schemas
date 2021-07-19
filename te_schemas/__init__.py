class SchemaBase:
    '''Base class for te_schemas schemas'''
    def validate(self):
        data, errors = self.Schema().dump(self)
        self.Schema().validate(data)

    def as_json(self):
        self.Schema().dumps(nesting)

