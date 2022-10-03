from typing import List

import marshmallow_dataclass

from .jobs import Path
from .results import Band


@marshmallow_dataclass.dataclass
class DataFile:
    path: Path
    bands: List[Band]

    def indices_for_name(
        self, name_filter: str, field: str = None, field_filter: str = None
    ):
        if field:
            assert field_filter is not None

            return [
                index
                for index, band in enumerate(self.bands)
                if (band.name == name_filter and band.metadata[field] == field_filter)
            ]
        else:
            return [
                index
                for index, band in enumerate(self.bands)
                if band.name == name_filter
            ]

    def index_for_name(
        self, name_filter: str, field: str = None, field_filter: str = None
    ):
        """throw an error if more than one result"""
        out = self.indices_for_name(name_filter, field, field_filter)

        if len(out) > 1:
            raise RuntimeError(f"more than one band found for name {name_filter}")
        else:
            return out[0]

    def metadata_for_name(self, name_filter: str, field: str):
        """get value of metadata field for all bands of specific type"""
        m = [b.metadata[field] for b in self.bands if b.name == name_filter]

        if len(m) == 1:
            return m[0]
        else:
            return m

    def append(self, datafile):
        """
        Extends bands with those from another datafile

        This assumes that both DataFile share the same path (where the path
        is the one of the original DataFile)
        """
        datafiles = [self, datafile]

        self.bands = [b for d in datafiles for b in d.bands]

    def extend(self, datafiles):
        """
        Extends bands with those from another datafile

        This assumes that both DataFile share the same path (where the path
        is the one of the original DataFile)
        """

        datafiles = [self] + datafiles

        self.bands = [b for d in datafiles for b in d.bands]


def combine_data_files(path, datafiles: List[Band]) -> DataFile:
    """combine multiple datafiles with same path into one object"""

    return DataFile(path=path, bands=[b for d in datafiles for b in d.bands])
