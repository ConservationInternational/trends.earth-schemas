import uuid as uuid_module
from dataclasses import field
from typing import ClassVar, List, Optional, Tuple

from marshmallow import EXCLUDE, validate
from marshmallow_dataclass import dataclass


@dataclass
class ErrorRecodeProperties:
    class Meta:
        unknown = EXCLUDE

    uuid: uuid_module.UUID
    periods_affected: List[str] = field(
        metadata={
            "validate": validate.And(
                validate.Length(min=1),
                lambda x: all(
                    item in ["baseline", "report_1", "report_2"] for item in x
                ),
            ),
        },
    )
    location_name: Optional[str] = None
    area_km_sq: Optional[float] = None
    process_driving_change: Optional[str] = None
    basis_for_judgement: Optional[str] = None
    recode_deg_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, 0, 1])},
    )
    recode_stable_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, -1, 1])},
    )
    recode_imp_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, -1, 0])},
    )
    stats: Optional[dict] = None


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

    recode_deg_to_options: ClassVar[Tuple] = (None, -32768, 0, 1)
    recode_stable_to_options: ClassVar[Tuple] = (None, -32768, -1, 1)
    recode_imp_to_options: ClassVar[Tuple] = (None, -32768, -1, 0)

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
                    # Convert None to -9999 for "no recoding" sentinel value
                    # This allows -32768 to mean "recode to nodata" as intended
                    deg_val = (
                        self.recode_deg_to_options[i]
                        if self.recode_deg_to_options[i] is not None
                        else -9999
                    )
                    stable_val = (
                        self.recode_stable_to_options[j]
                        if self.recode_stable_to_options[j] is not None
                        else -9999
                    )
                    imp_val = (
                        self.recode_imp_to_options[k]
                        if self.recode_imp_to_options[k] is not None
                        else -9999
                    )
                    deg_to.append(deg_val)
                    stable_to.append(stable_val)
                    imp_to.append(imp_val)
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
