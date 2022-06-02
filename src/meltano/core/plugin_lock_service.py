"""Plugin Lockfile Service."""

from __future__ import annotations

import json
from pathlib import Path

from structlog.stdlib import get_logger

from meltano.core.plugin.base import BasePlugin, PluginRef, StandalonePlugin, Variant
from meltano.core.project import Project

logger = get_logger(__name__)


class LockfileAlreadyExistsError(Exception):
    """Raised when a plugin lockfile already exists."""

    def __init__(self, message: str, path: Path, plugin: PluginRef):
        """Create a new LockfileAlreadyExistsError.

        Args:
            message: The error message.
            path: The path to the existing lockfile.
            plugin: The plugin that was locked.
        """
        self.path = path
        self.plugin = plugin
        super().__init__(message)


class PluginLockService:
    """Plugin Lockfile Service."""

    def __init__(self, project: Project):
        """Create a new Plugin Lockfile Service.

        Args:
            project: The Meltano project.
        """
        self.projet = project

    def save(
        self,
        plugin: BasePlugin,
        *,
        overwrite: bool = False,
        exists_ok: bool = False,
    ):
        """Save the plugin lockfile.

        Args:
            plugin: The plugin definition to save.
            overwrite: Whether to overwrite the lockfile if it already exists.
            exists_ok: Whether raise an exception if the lockfile already exists.

        Raises:
            LockfileAlreadyExistsError: If the lockfile already exists and is not
                flagged for overwriting.
        """
        variant = None if plugin.variant == Variant.DEFAULT_NAME else plugin.variant

        logger.info(f"Locking a {type(plugin)}")

        plugin_def = plugin.definition
        path = self.projet.plugin_lock_path(
            plugin_def.type,
            plugin_def.name,
            variant_name=variant,
        )

        if path.exists() and not overwrite and not exists_ok:
            raise LockfileAlreadyExistsError(
                f"Lockfile already exists: {path}",
                path,
                plugin,
            )

        variant = plugin_def.find_variant(plugin.variant)
        locked_def = StandalonePlugin.from_variant(
            variant,
            plugin.name,
            plugin.namespace,
            plugin.type,
            label=plugin.label,
        )

        with path.open("w") as lockfile:
            json.dump(locked_def.canonical(), lockfile, indent=2)

        logger.debug("Locked plugin definition", path=path)