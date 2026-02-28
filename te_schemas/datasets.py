"""
Schemas for remote dataset definitions and Google Earth Engine (GEE) datasets.

This module defines marshmallow schemas for managing remote dataset metadata,
including validation for spatial/temporal extents, resolution specifications,
and dataset accessibility information.
"""

import re
import typing
from enum import Enum

from marshmallow import ValidationError
from marshmallow_dataclass import dataclass

from . import SchemaBase


class TemporalUnit(Enum):
    """Enumeration of temporal units."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    ONE_TIME = "one-time"  # Special case for static datasets


class SpatialUnit(Enum):
    """Enumeration of spatial units."""

    METER = "m"
    KILOMETER = "km"


def validate_spatial_resolution_value(value: typing.Union[int, float]):
    """Validate spatial resolution value is positive."""
    if value <= 0:
        raise ValidationError(f"Spatial resolution value '{value}' must be positive")


def validate_temporal_resolution_value(
    value: typing.Union[int, float, None], unit: str
):
    """Validate temporal resolution value based on unit."""
    if unit == "one-time":
        if value is not None:
            raise ValidationError(
                "Temporal resolution value must be None for 'one-time' datasets"
            )
    else:
        if value is None or value <= 0:
            raise ValidationError(
                f"Temporal resolution value must be positive for unit '{unit}'"
            )


def validate_url_format(url: typing.Optional[str]):
    """Validate URL format if provided."""
    if url is None or url == "" or url == "None available":
        return
    # Basic validation: either a full URL or a domain name
    # Allow protocols, domain names, and paths
    if (
        url.startswith("http://")
        or url.startswith("https://")
        or url.startswith("ftp://")
        or "." in url
    ):
        # Basic check passed - allow flexible URL formats for data compatibility
        return
    raise ValidationError(f"Invalid URL format: '{url}'")


@dataclass
class SpatialExtent(SchemaBase):
    """Spatial extent definition with validation."""

    spatial_resolution_value: typing.Union[int, float]
    spatial_resolution_unit: str
    min_latitude: typing.Union[int, float]
    max_latitude: typing.Union[int, float]
    min_longitude: typing.Union[int, float]
    max_longitude: typing.Union[int, float]

    def __post_init__(self):
        """Validate spatial extent after initialization."""
        validate_spatial_resolution_value(self.spatial_resolution_value)

        # Validate spatial resolution unit
        if self.spatial_resolution_unit not in [unit.value for unit in SpatialUnit]:
            raise ValidationError(
                f"Invalid spatial resolution unit: {self.spatial_resolution_unit}"
            )

        # Validate latitude range
        if not (-90 <= self.min_latitude <= 90):
            raise ValidationError(
                f"min_latitude must be between -90 and 90, got {self.min_latitude}"
            )
        if not (-90 <= self.max_latitude <= 90):
            raise ValidationError(
                f"max_latitude must be between -90 and 90, got {self.max_latitude}"
            )

        # Validate longitude range
        if not (-180 <= self.min_longitude <= 180):
            raise ValidationError(
                f"min_longitude must be between -180 and 180, got {self.min_longitude}"
            )
        if not (-180 <= self.max_longitude <= 180):
            raise ValidationError(
                f"max_longitude must be between -180 and 180, got {self.max_longitude}"
            )

        # Validate min < max
        if self.min_latitude >= self.max_latitude:
            raise ValidationError("min_latitude must be less than max_latitude")
        if self.min_longitude >= self.max_longitude:
            raise ValidationError("min_longitude must be less than max_longitude")


@dataclass
class TemporalExtent(SchemaBase):
    """Temporal extent definition with validation."""

    temporal_resolution_value: typing.Optional[typing.Union[int, float]] = None
    temporal_resolution_unit: str = "one-time"
    start_year: typing.Optional[typing.Union[int, str]] = None
    end_year: typing.Optional[typing.Union[int, str]] = None

    def __post_init__(self):
        """Validate temporal extent after initialization."""
        # Validate temporal resolution unit
        if self.temporal_resolution_unit not in [unit.value for unit in TemporalUnit]:
            raise ValidationError(
                f"Invalid temporal resolution unit: {self.temporal_resolution_unit}"
            )

        # Validate temporal resolution value based on unit
        validate_temporal_resolution_value(
            self.temporal_resolution_value, self.temporal_resolution_unit
        )

        # Allow None, "NA", or valid years
        for year_field, year_value in [
            ("start_year", self.start_year),
            ("end_year", self.end_year),
        ]:
            if year_value is not None and year_value != "NA":
                try:
                    year_int = int(year_value)
                    if not (1800 <= year_int <= 2100):  # Reasonable year range
                        raise ValidationError(
                            f"{year_field} must be between 1800 and 2100, got {year_int}"
                        )
                except (ValueError, TypeError):
                    raise ValidationError(
                        f"{year_field} must be a valid year, 'NA', or None, got {year_value}"
                    )

        # Validate year ordering (convert to int for comparison)
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year != "NA"
            and self.end_year != "NA"
        ):
            try:
                start_int = int(self.start_year)
                end_int = int(self.end_year)
                if start_int > end_int:
                    raise ValidationError(
                        "start_year must be less than or equal to end_year"
                    )
            except (ValueError, TypeError):
                pass  # Skip comparison if years can't be converted to int


@dataclass
class RemoteDataset(SchemaBase):
    """
    Abstract base schema for remote dataset definitions.

    This serves as the parent class for specific dataset types like GEE datasets,
    providing common fields and validation logic for spatial/temporal metadata,
    licensing, and accessibility information.
    """

    # Required fields
    name: str
    data_source: str
    spatial_extent: SpatialExtent
    temporal_extent: TemporalExtent
    units: str
    license: str
    source: str

    # Optional fields with defaults
    description: str = ""
    dataset_url: typing.Optional[str] = None
    license_url: typing.Optional[str] = None
    citation: typing.Optional[str] = None
    comments: typing.Optional[str] = None
    downloadable: bool = True

    def __post_init__(self):
        """Validate dataset after initialization."""
        if len(self.name) == 0 or len(self.name) > 200:
            raise ValidationError("name must be between 1 and 200 characters")
        if len(self.data_source) > 500:
            raise ValidationError("data_source must be less than 500 characters")
        if len(self.description) > 2000:
            raise ValidationError("description must be less than 2000 characters")
        if len(self.units) > 100:
            raise ValidationError("units must be less than 100 characters")
        if len(self.license) > 200:
            raise ValidationError("license must be less than 200 characters")
        if len(self.source) > 1000:
            raise ValidationError("source must be less than 1000 characters")

        # Validate URLs if provided
        if self.dataset_url:
            validate_url_format(self.dataset_url)
        if self.license_url:
            validate_url_format(self.license_url)

        # Check citation length
        if self.citation and len(self.citation) > 2000:
            raise ValidationError("citation must be less than 2000 characters")
        if self.comments and len(self.comments) > 1000:
            raise ValidationError("comments must be less than 1000 characters")


@dataclass
class GEEDataset(RemoteDataset):
    """
    Google Earth Engine dataset schema.

    Extends RemoteDataset with GEE-specific fields and validation.
    """

    # GEE-specific required field
    gee_dataset: str = ""

    # Optional fields for specific dataset types
    source_code: typing.Optional[str] = None
    lags: typing.Optional[typing.List[int]] = None

    def __post_init__(self):
        """Validate GEE dataset after initialization."""
        super().__post_init__()

        if len(self.gee_dataset) == 0:
            raise ValidationError("gee_dataset is required")
        if len(self.gee_dataset) > 200:
            raise ValidationError("gee_dataset must be less than 200 characters")

        # Validate GEE dataset path format
        if not (
            self.gee_dataset.startswith("users/")
            or self.gee_dataset.startswith("projects/")
            or "/" in self.gee_dataset
        ):
            raise ValidationError(
                "gee_dataset must be a valid GEE asset path (e.g., users/username/asset or projects/project/asset)"
            )

        # Validate source code length if provided
        if self.source_code and len(self.source_code) > 200:
            raise ValidationError("source_code must be less than 200 characters")

        # Validate lags if provided
        if self.lags:
            for lag in self.lags:
                if not (1 <= lag <= 120):
                    raise ValidationError("Each lag must be between 1 and 120")

    @classmethod
    def from_gee_json(
        cls, category: str, name: str, dataset_data: dict
    ) -> "GEEDataset":
        """Create GEEDataset from GEE JSON format."""

        # Handle coordinate conversion (string to float)
        def convert_coord(value):
            if isinstance(value, str):
                return float(value)
            return value

        # Handle year conversion (string "NA" to None, otherwise int)
        def convert_year(value):
            if value in [None, "NA", ""]:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Parse spatial resolution
        def parse_spatial_resolution(resolution_str):
            if not resolution_str or resolution_str == "unknown":
                return 1, "m"  # Default fallback

            # Extract number and unit (e.g., "250 m" -> 250, "m")
            match = re.match(r"^(\d+(?:\.\d+)?)\s*(m|km)$", resolution_str.strip())
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return value, unit
            return 1, "m"  # Fallback

        # Parse temporal resolution
        def parse_temporal_resolution(resolution_str):
            if not resolution_str:
                return None, "one-time"

            # Handle special cases
            if resolution_str == "one-time":
                return None, "one-time"
            elif resolution_str == "annual":
                return 1, "year"
            elif resolution_str == "monthly":
                return 1, "month"
            elif resolution_str == "16-day":
                return 16, "day"
            elif resolution_str == "5 years":
                return 5, "year"
            else:
                # Try to parse "X unit" format
                match = re.match(r"^(\d+)(?:-|\s+)(day|month|year)s?$", resolution_str)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)
                    return value, unit
                # Fallback
                return None, "one-time"

        # Handle both old and new format
        if "Spatial Resolution Value" in dataset_data:
            # New separated format
            spatial_value = dataset_data.get("Spatial Resolution Value", 1)
            spatial_unit = dataset_data.get("Spatial Resolution Unit", "m")
        else:
            # Old combined format
            spatial_value, spatial_unit = parse_spatial_resolution(
                dataset_data.get("Spatial Resolution", "")
            )

        if "Temporal Resolution Unit" in dataset_data:
            # New separated format
            temporal_value = dataset_data.get("Temporal Resolution Value")
            temporal_unit = dataset_data.get("Temporal Resolution Unit", "one-time")
        else:
            # Old combined format
            temporal_value, temporal_unit = parse_temporal_resolution(
                dataset_data.get("Temporal resolution", "")
            )

        return cls(
            name=name,
            data_source=dataset_data.get("Data source", ""),
            spatial_extent=SpatialExtent(
                spatial_resolution_value=spatial_value,
                spatial_resolution_unit=spatial_unit,
                min_latitude=convert_coord(dataset_data.get("Min Latitude", 0)),
                max_latitude=convert_coord(dataset_data.get("Max Latitude", 0)),
                min_longitude=convert_coord(dataset_data.get("Min Longitude", 0)),
                max_longitude=convert_coord(dataset_data.get("Max Longitude", 0)),
            ),
            temporal_extent=TemporalExtent(
                temporal_resolution_value=temporal_value,
                temporal_resolution_unit=temporal_unit,
                start_year=convert_year(dataset_data.get("Start year")),
                end_year=convert_year(dataset_data.get("End year")),
            ),
            units=dataset_data.get("Units", ""),
            license=dataset_data.get("License", ""),
            source=dataset_data.get("Source", ""),
            description=dataset_data.get("Description", ""),
            dataset_url=dataset_data.get("Link to Dataset", ""),
            gee_dataset=dataset_data.get("GEE Dataset", ""),
            citation=dataset_data.get("Citation", ""),
            downloadable=dataset_data.get("downloadable", False),
        )


@dataclass
class DatasetCategory(SchemaBase):
    """Schema for dataset category containing multiple datasets."""

    name: str
    datasets: typing.Optional[typing.Dict[str, GEEDataset]] = None

    def __post_init__(self):
        """Initialize datasets if not provided."""
        if self.datasets is None:
            self.datasets = {}


@dataclass
class GEEDatasetCollection(SchemaBase):
    """
    Schema for the complete GEE dataset collection.

    Represents the structure of the gee_datasets.json file with
    nested categories and datasets.
    """

    categories: typing.Optional[typing.Dict[str, typing.Dict[str, GEEDataset]]] = None

    def __post_init__(self):
        """Validate collection after initialization."""
        if self.categories is None:
            self.categories = {}

        # Ensure we have at least one category
        if not self.categories:
            raise ValidationError(
                "Dataset collection must contain at least one category"
            )

        # Validate categories structure
        for category_name, datasets in self.categories.items():
            if not isinstance(datasets, dict):
                raise ValidationError(
                    f"Category {category_name} must contain a dictionary of datasets"
                )

    @classmethod
    def from_gee_json(cls, raw_data: dict) -> "GEEDatasetCollection":
        """Create GEEDatasetCollection from raw GEE JSON data."""
        categories = {}

        for category_name, datasets_dict in raw_data.items():
            datasets = {}
            for dataset_name, dataset_data in datasets_dict.items():
                datasets[dataset_name] = GEEDataset.from_gee_json(
                    category_name, dataset_name, dataset_data
                )
            categories[category_name] = datasets

        return cls(categories=categories)


# Convenience functions for loading and validating dataset files


def transform_gee_data_structure(raw_data: dict) -> dict:
    """
    Transform raw GEE dataset JSON structure to match our schema.

    Converts the flat structure with string coordinates and years to
    proper types and nested structures.
    """
    transformed = {"categories": {}}

    for category_name, datasets in raw_data.items():
        transformed_datasets = {}

        for dataset_name, dataset_data in datasets.items():
            # Transform coordinates to float
            spatial_extent = {
                "min_latitude": float(dataset_data.get("Min Latitude", -90)),
                "max_latitude": float(dataset_data.get("Max Latitude", 90)),
                "min_longitude": float(dataset_data.get("Min Longitude", -180)),
                "max_longitude": float(dataset_data.get("Max Longitude", 180)),
            }

            # Transform years to int or None
            start_year = dataset_data.get("Start year")
            if start_year == "NA" or start_year is None:
                start_year = None
            else:
                start_year = int(start_year)

            end_year = dataset_data.get("End year")
            if end_year == "NA" or end_year is None:
                end_year = None
            else:
                end_year = int(end_year)

            temporal_extent = {
                "start_year": start_year,
                "end_year": end_year,
                "temporal_resolution": dataset_data.get(
                    "Temporal resolution", "one-time"
                ),
            }

            # Build transformed dataset
            transformed_dataset = {
                "name": dataset_name,
                "data_source": dataset_data.get("Data source", ""),
                "description": dataset_data.get("Description", ""),
                "spatial_extent": spatial_extent,
                "temporal_extent": temporal_extent,
                "spatial_resolution": dataset_data.get("Spatial Resolution", ""),
                "units": dataset_data.get("Units", ""),
                "dataset_url": dataset_data.get("Link to Dataset")
                if dataset_data.get("Link to Dataset")
                and dataset_data.get("Link to Dataset") != "None available"
                else None,
                "gee_dataset": dataset_data.get("GEE Dataset", ""),
                "source_code": dataset_data.get("Source code") or None,
                "license": dataset_data.get("License", ""),
                "license_url": dataset_data.get("License URL") or None,
                "source": dataset_data.get("Source", ""),
                "citation": dataset_data.get("Citation") or None,
                "comments": dataset_data.get("Comments") or None,
                "downloadable": dataset_data.get("downloadable", True),
                "lags": dataset_data.get("Lags") or None,
            }

            transformed_datasets[dataset_name] = transformed_dataset

        transformed["categories"][category_name] = transformed_datasets

    return transformed


def load_gee_dataset_collection(data: dict) -> GEEDatasetCollection:
    """
    Load and validate a GEE dataset collection from dictionary data.

    Args:
        data: Dictionary representation of the dataset collection

    Returns:
        Validated GEEDatasetCollection instance

    Raises:
        ValidationError: If data doesn't match schema or validation fails
    """
    # Transform the raw data structure
    if "categories" not in data:
        data = transform_gee_data_structure(data)

    # Convert nested dictionaries to dataclass instances
    categories = {}
    for category_name, datasets_dict in data["categories"].items():
        datasets = {}
        for dataset_name, dataset_data in datasets_dict.items():
            # Create SpatialExtent
            spatial_extent = SpatialExtent(**dataset_data["spatial_extent"])
            # Create TemporalExtent
            temporal_extent = TemporalExtent(**dataset_data["temporal_extent"])
            # Create GEEDataset
            dataset_data["spatial_extent"] = spatial_extent
            dataset_data["temporal_extent"] = temporal_extent
            datasets[dataset_name] = GEEDataset(**dataset_data)
        categories[category_name] = datasets

    return GEEDatasetCollection(categories=categories)


def validate_gee_dataset_file(file_path: str) -> typing.Tuple[bool, typing.List[str]]:
    """
    Validate a GEE dataset JSON file.

    Args:
        file_path: Path to the JSON file to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    import json

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        load_gee_dataset_collection(data)
        return True, []

    except ValidationError as e:
        error_messages = [str(e)]
        return False, error_messages
    except Exception as e:
        return False, [f"Error loading file: {str(e)}"]
