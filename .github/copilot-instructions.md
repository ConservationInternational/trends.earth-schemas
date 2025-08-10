# Copilot Instructions for trends.earth-schemas

## Repository Overview

`trends.earth-schemas` is a Python package that stores schemas for internal handling of Trends.Earth analysis results. Trends.Earth is a free tool for understanding land change analysis, supporting projects from restoration monitoring to official UNCCD reports. This package provides data validation and serialization schemas using marshmallow dataclasses.

**Key Facts:**
- **Type:** Python package (~3,174 lines of code)
- **Languages:** Python 3.7-3.13 supported
- **Main Framework:** marshmallow for schema definition and validation
- **Size:** ~13MB repository, minimal complexity
- **Dependencies:** defusedxml, marshmallow, marshmallow-dataclass, GDAL (for geo-spatial functionality)
- **Downstream Dependencies:** `conservationinternational/trends.earth-algorithms` repository relies on these schemas

## Build and Testing Instructions

### Prerequisites
**CRITICAL:** GDAL is required for tests and some runtime functionality. Always install GDAL before running tests:

```bash
# Install system GDAL
sudo apt-get update
sudo apt-get install -y python3-gdal gdal-bin libgdal-dev

# Install Python GDAL bindings
pip install GDAL==`gdal-config --version`
```

**Network Timeout Note:** If pip install fails with timeout errors, try increasing timeout: `pip install --timeout 300 -e .` or install dependencies individually.

### Standard Development Workflow

1. **Install package in development mode:**
   ```bash
   pip install -e .
   ```

2. **Install test dependencies:**
   ```bash
   pip install pytest
   ```

3. **Run tests (requires GDAL):**
   ```bash
   pytest -v
   ```
   - **Expected:** 20 tests should pass in ~0.5 seconds
   - **If tests fail:** Check GDAL installation first

4. **Lint code:**
   ```bash
   pip install ruff
   ruff check --output-format=github .
   ```
   - **Expected:** No output (clean code)

5. **Format code:**
   ```bash
   ruff format
   ```

6. **Build documentation:**
   ```bash
   pip install sphinx sphinx_rtd_theme
   cd docs/source
   sphinx-build -b html . ../build
   ```

### Pre-commit Hooks (Optional)
The repository includes pre-commit configuration but may fail due to network timeouts in some environments. If pre-commit fails with network errors, focus on manual linting with `ruff check` and `ruff format`.

## CI/CD and Validation

### GitHub Actions Workflows
- **test.yaml:** Runs pytest on Python 3.9-3.13 with GDAL installation
- **ruff.yaml:** Runs `ruff check --output-format=github .` for linting

### Validation Checklist
Before making changes, always:
1. Install GDAL dependencies
2. Run `pip install -e .` to install in development mode
3. Run `pytest -v` to ensure tests pass
4. Run `ruff check` for linting
5. Run `ruff format` for formatting

### Breaking Changes Considerations
**IMPORTANT:** The `conservationinternational/trends.earth-algorithms` repository depends on these schemas. When making changes:
- **Schema modifications:** Changes to field names, types, or required fields may break downstream consumers
- **API changes:** Modifications to schema methods or validation logic should be backward-compatible
- **New fields:** Adding optional fields is generally safe; adding required fields may break existing code
- **Deprecations:** Consider deprecation warnings before removing schema fields or methods
- **Version impact:** Major schema changes may require coordinated updates in the algorithms repository

## Project Architecture

### Directory Structure
```
├── .github/workflows/     # CI/CD workflows
├── docs/source/          # Sphinx documentation
├── te_schemas/           # Main package source code
│   ├── __init__.py       # Package initialization with SchemaBase
│   ├── schemas.py        # Core schema definitions and validation
│   ├── aoi.py           # Area of Interest schemas (requires GDAL)
│   ├── results.py       # Analysis results schemas
│   ├── land_cover.py    # Land cover classification schemas
│   ├── productivity.py   # Productivity analysis schemas
│   ├── reporting.py     # Reporting schemas
│   ├── algorithms.py    # Algorithm parameter schemas
│   ├── jobs.py          # Job execution schemas
│   ├── datafile.py      # Data file handling schemas
│   └── error_recode.py  # Error handling schemas
├── tests/               # Test suite
│   ├── test_aoi.py      # AOI tests (requires GDAL)
│   ├── test_land_cover.py
│   ├── test_results.py
│   └── data/            # Test data files
├── pyproject.toml       # Modern Python packaging configuration
├── .pre-commit-config.yaml # Pre-commit hooks configuration
└── tasks.py            # Invoke task automation (version management)
```

### Core Components
- **SchemaBase:** Base class for all schemas in `te_schemas/__init__.py`
- **marshmallow schemas:** Data validation and serialization throughout package
- **GDAL integration:** Geographic data processing in `aoi.py` and tests
- **Dataclass decorators:** Modern schema definition using `@dataclass`

### Key Configuration Files
- **pyproject.toml:** Package configuration, dependencies, and metadata
- **.pre-commit-config.yaml:** ruff linting and formatting rules
- **docs/source/conf.py:** Sphinx documentation configuration
- **.readthedocs.yaml:** ReadTheDocs build configuration

## Common Pitfalls and Solutions

### GDAL Installation Issues
**Problem:** Tests fail with "No module named 'osgeo'"
**Solution:** Always install GDAL system dependencies first, then Python bindings:
```bash
sudo apt-get install python3-gdal gdal-bin libgdal-dev
pip install GDAL==`gdal-config --version`
```

### Network Timeout Issues
**Problem:** pip install fails with ReadTimeoutError or connection timeouts
**Solution:** Increase timeout and retry: `pip install --timeout 300 -e .` or install dependencies individually

### Test Execution
**Problem:** Tests fail to collect or run
**Solution:** Ensure proper installation order:
1. Install GDAL system packages
2. Install Python GDAL bindings
3. Install package in development mode: `pip install -e .`
4. Install test dependencies: `pip install pytest`
5. Run tests: `pytest -v`

### Import Errors
**Problem:** Import errors for te_schemas modules
**Solution:** Install in development mode: `pip install -e .`

### Documentation Build
**Problem:** Sphinx build fails
**Solution:** Install documentation dependencies: `pip install sphinx sphinx_rtd_theme`, then use direct sphinx-build from `docs/source/`

### Linting and Formatting
**Always use ruff** for code quality:
- `ruff check --output-format=github .` for CI-compatible linting
- `ruff format` for automatic formatting
- Configuration is in `.pre-commit-config.yaml`

## Trust These Instructions

These instructions are comprehensive and validated. **Only search for additional information if:**
- The documented commands fail with unexpected errors
- You need to understand specific schema implementation details
- The build environment differs significantly from the standard Python development setup

**Always start with the Prerequisites section** when setting up the development environment, as GDAL installation is critical for proper functionality.