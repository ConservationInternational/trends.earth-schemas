import uuid as uuid_module
from dataclasses import field
from typing import ClassVar, List, Optional, Tuple, Type

from marshmallow import EXCLUDE, validate
from marshmallow_dataclass import dataclass


@dataclass
class ErrorRecodeProperties:
    class Meta:
        unknown = EXCLUDE

    uuid: uuid_module.UUID = field(metadata={"default": uuid_module.uuid4})
    location_name: Optional[str]
    area_km_sq: Optional[float]
    process_driving_change: Optional[str]
    basis_for_judgement: Optional[str]
    recode_deg_to: Optional[int] = field(
        metadata={"validate": validate.OneOf([None, -32768, 0, 1]), "missing": None}
    )
    recode_stable_to: Optional[int] = field(
        metadata={"validate": validate.OneOf([None, -32768, -1, 1]), "missing": None}
    )
    recode_imp_to: Optional[int] = field(
        metadata={"validate": validate.OneOf([None, -32768, -1, 0]), "missing": None}
    )
    stats: Optional[dict]


@dataclass
class ErrorRecodeFeature:
    class Meta:
        unknown = EXCLUDE

    geometry: dict
    properties: ErrorRecodeProperties
    type: str = field(metadata={"validate": validate.Equal("Feature")})


@dataclass
class ErrorRecodePolygons:
    class Meta:
        unknown = EXCLUDE

    features: List[ErrorRecodeFeature]
    name: Optional[str]
    crs: Optional[dict]
    type: str = field(metadata={"validate": validate.Equal("FeatureCollection")})

    recode_deg_to_options: ClassVar[Type[Tuple]] = (None, -32768, 0, 1)
    recode_stable_to_options: ClassVar[Type[Tuple]] = (None, -32768, -1, 1)
    recode_imp_to_options: ClassVar[Type[Tuple]] = (None, -32768, -1, 0)

    @property
    def trans_code_lists(self):
        # Key for how recoding works
        #   First digit indicates from:
        #     1 is deg
        #     2 is imp
        #     3 is stable
        #     0 is unchanged
        #
        #   Second digit indicates to:
        #     1 is deg
        #     2 is imp
        #     3 is stable
        #     0 is unchanged
        #
        #   So keys are:
        #     recode_deg_to: unchanged 10, stable 12, improved 13
        #     recode_stable_to: unchanged, 20 deg 21,improved 23
        #     recode_imp_to: unchanged 30, deg 31, stable 32
        codes = []
        deg_to = []
        stable_to = []
        imp_to = []
        n = 0
        for i in range(len(self.recode_deg_to_options)):
            for j in range(len(self.recode_stable_to_options)):
                for k in range(len(self.recode_imp_to_options)):
                    codes.append(n)
                    deg_to.append(self.recode_deg_to_options[i])
                    stable_to.append(self.recode_stable_to_options[j])
                    imp_to.append(self.recode_imp_to_options[k])
                    n += 1

        return codes, deg_to, stable_to, imp_to

    @property
    def recode_to_trans_code_dict(self):
        recode_to_trans_code = {}
        n = 0
        for i in range(len(self.recode_deg_to_options)):
            for j in range(len(self.recode_stable_to_options)):
                for k in range(len(self.recode_imp_to_options)):
                    recode_to_trans_code[
                        (
                            self.recode_deg_to_options[i],
                            self.recode_stable_to_options[j],
                            self.recode_imp_to_options[k],
                        )
                    ] = n
                    n += 1

        return recode_to_trans_code
