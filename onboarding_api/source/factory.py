"""
DataSourceFactory — config-driven data source instantiation.

Usage
-----
    from source.factory import DataSourceFactory

    source = DataSourceFactory.create(config)   # full config dict
    files  = source.download()

Supported sources
-----------------
    local       → LocalFileSource      (local filesystem path)
    s3          → S3Source             (AWS S3)
    azure_blob  → AzureBlobSource      (Azure Blob Storage)
    gdrive      → GDriveSource         (Google Drive)
    sharepoint  → SharePointSource     (Microsoft SharePoint)
    web         → WebSource            (HTTP/HTTPS URLs)
"""

import importlib
from typing import Type

from source.base import DataSource
from config.logger import setup_logger

logger = setup_logger(__name__)

# ── Registry: source type key → dotted class path ─────────────────────────────
# Classes are imported lazily so heavy SDKs (azure, google, boto3) are only
# loaded when the corresponding source type is actually configured.

_REGISTRY: dict[str, str] = {
    "local":       "source.local_source.LocalFileSource",
    "s3":          "source.s3_source.S3Source",
    "azure_blob":  "source.azure_blob_source.AzureBlobSource",
    "gdrive":      "source.gdrive_source.GDriveSource",
    "sharepoint":  "source.sharepoint_source.SharePointSource",
    "web":         "source.web_source.WebSource",
}


def _import_class(dotted_path: str) -> Type[DataSource]:
    """Lazily import a DataSource subclass from a dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class DataSourceFactory:
    """
    Registry-based factory for DataSource implementations.

    The factory is stateless (no caching).  The application layer is
    responsible for instance lifecycle management.
    """

    @staticmethod
    def create(config: dict) -> DataSource:
        """
        Instantiate the appropriate DataSource from a raw config dict.

        Args:
            config: Full application config dict.  The factory reads
                    ``config["source"]["type"]`` to determine the class.

        Returns:
            A concrete DataSource instance.

        Raises:
            ValueError:  Unknown source type key.
            ImportError: Required SDK not installed for that source.
        """
        source_type = config["source"]["type"].lower().strip()

        if source_type not in _REGISTRY:
            supported = ", ".join(sorted(_REGISTRY.keys()))
            logger.warning(
                f"Unsupported source type requested: {source_type}"
            )
            raise ValueError(
                f"Unsupported source type: {source_type!r}.\n"
                f"Supported types: {supported}"
            )

        source_class = _import_class(_REGISTRY[source_type])
        logger.info(
            f"Creating source provider: {source_class.__name__}"
        )

        logger.debug(
            f"Source type requested: {source_type}"
        )
        return source_class(config)

    # Keep backward-compatible alias used by the old main.py
    @staticmethod
    def create_source(config: dict) -> DataSource:
        """Alias for :meth:`create` — kept for backward compatibility."""
        return DataSourceFactory.create(config)

    @staticmethod
    def list_sources() -> list[str]:
        """Return a sorted list of all registered source type keys."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def register(source_key: str, dotted_class_path: str) -> None:
        """
        Register a custom / third-party DataSource at runtime.

        Args:
            source_key:         Key used in ``config.yaml`` (e.g. ``"my_source"``)
            dotted_class_path:  e.g. ``"mypackage.mymodule.MySource"``

        Example::

            DataSourceFactory.register(
                "ftp",
                "myapp.sources.ftp_source.FTPSource"
            )
        """
        _REGISTRY[source_key.lower()] = dotted_class_path
        logger.info(
            f"Registered custom source: {source_key}"
        )