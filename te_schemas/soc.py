from . import SchemaBase, validate_matrix
from .land_cover import LCLegend

@dataclass
class LCTransMatrix(SchemaBase):
    '''Define meaning of each possible land cover transition'''
    lc_legend: LCLegend
    transitions: List[LCTransMeaning] = field(default_factory=list)

    '''Stock change factors for land use'''

    '''Stock change factors for management regime'''

    '''Stock change factors for input of organic matter'''


    def get_multiplier(self):
        return _get_multiplier(self)

@dataclass
class SOCTransitionDefinitionBase(SchemaBase):
    '''Base class to define meaning of land cover transitions

    Can contain one more more definitions TransitionMatrixBase'''

    legend: LCLegend
    name: str
    definitions: Any

    @validates_schema
    def validate_transitions(self, data, **kwargs):
        '''Ensure each transition is represented once and only once'''
        if isinstance(data['definitions'], dict):
            for key, m in data['definitions']:
                validate_matrix(data['legend'], m.transitions)

    def get_list(self, key=None):
        '''Get transition matrix, in GEE format'''
        if isinstance(self.definitions, dict):
            if key == None:
                raise Exception
            else:
                m = self.definitions[key]
        elif isinstance(self.definitions, LCTransitionMatrixBase):
            m = self.definitions
        else:
            raise Exception
        out = [[], []]
        for c_final in self.legend.key:
            for c_initial in self.legend.key:
                out[0].append(c_initial.code * self.get_multiplier() + c_final.code)
                trans = [t for t in m.transitions if
                         (t.initial == c_initial) and
                         (t.final == c_final)][0]
                out[1].append(trans.code())

    def get_persistence_list(self):
        '''Get transition matrix to remap persistence classes, in GEE format

        Remap persistence class codes (11, 22), etc., so they are sequential 
        (1, 2, etc.). This makes it easier to assign a clear color ramp in 
        QGIS.'''
        out = [[], []]
        for c_initial in self.legend.key:
            for c_final in self.legend.key:
                original_code = c_initial.code * self.get_multiplier() + c_final.code
                out[0].append(original_code)
                if c_final.code == c_initial.code:
                    out[1].append(c_initial.code)
                else:
                    out[1].append(original_code)
        return out

    def get_multiplier(self):
        '''Return multiplier for transition calculations

        Used to figure out what number to multiply initial codes by so that, 
        when added to the final class code,  the result is the same as if the 
        class codes were added as strings. For example: if the initial class 
        code were 7, and, the  final class code were 5, the transition would be 
        coded as 75)'''
        return math.ceil(max([c.code for c in self.legend.key]) / 10) * 10


