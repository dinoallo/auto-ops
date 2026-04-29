#!/usr/bin/env python3
"""GCP Compute Engine disk snapshot workflow for Ansible."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import google.auth.exceptions
from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import compute_v1

POLL_INTERVAL_DEFAULT = 10
READY_TIMEOUT_DEFAULT = 1800
MATERIALIZE_TIMEOUT_DEFAULT = 60
NAME_MAX_LENGTH = 63


class RecipeError(RuntimeError):
    """User-facing validation or workflow error."""


def main() -> int:
    try:
        request = load_request()
        validate_request(request)
        clients = build_clients()

        instances = resolve_instances(clients["instances"], request["project"], request["target_instances"])
        disks = describe_attached_disks(
            project=request["project"],
            instances=instances,
            disks_client=clients["disks"],
            region_disks_client=clients["region_disks"],
        )
        selected_disks = select_disks(
            target_instances=request["target_instances"],
            disks=disks,
            include_boot_disk=request["include_boot_disk"],
            requested_data_disk_ids=request["data_disk_ids"],
        )

        result = create_individual_snapshots(
            request=request,
            instances=instances,
            disks=selected_disks,
            disks_client=clients["disks"],
            region_disks_client=clients["region_disks"],
            snapshots_client=clients["snapshots"],
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RecipeError as exc:
        print(f"recipe error: {exc}", file=sys.stderr)
        return 2
    except google.auth.exceptions.DefaultCredentialsError as exc:
        print(f"gcp credentials error: {exc}", file=sys.stderr)
        return 3
    except GoogleAPICallError as exc:
        print(f"gcp api error: {exc}", file=sys.stderr)
        return 4


def load_request() -> Dict[str, Any]:
    return {
        "project": env_required("GOOGLE_CLOUD_PROJECT"),
        "target_instances": env_json_required("RECIPE_TARGET_INSTANCES_JSON"),
        "snapshot_name_prefix": env_required("RECIPE_SNAPSHOT_NAME_PREFIX"),
        "include_boot_disk": env_bool("RECIPE_INCLUDE_BOOT_DISK", True),
        "data_disk_ids": env_json_optional("RECIPE_DATA_DISK_IDS_JSON"),
        "use_consistency_group_snapshot": env_bool("RECIPE_USE_CONSISTENCY_GROUP_SNAPSHOT", False),
        "wait_for_snapshot_ready": env_bool("RECIPE_WAIT_FOR_SNAPSHOT_READY", True),
        "snapshot_description": os.environ.get("RECIPE_SNAPSHOT_DESCRIPTION", ""),
        "snapshot_tags": env_json_optional("RECIPE_SNAPSHOT_TAGS_JSON"),
        "snapshot_ready_timeout_seconds": env_int("RECIPE_SNAPSHOT_READY_TIMEOUT_SECONDS", READY_TIMEOUT_DEFAULT),
        "snapshot_poll_interval_seconds": env_int("RECIPE_SNAPSHOT_POLL_INTERVAL_SECONDS", POLL_INTERVAL_DEFAULT),
    }


def validate_request(request: Dict[str, Any]) -> None:
    if not isinstance(request["target_instances"], list) or not request["target_instances"]:
        raise RecipeError("target_instances must be a non-empty JSON list.")
    if not all(isinstance(item, str) and item for item in request["target_instances"]):
        raise RecipeError("target_instances must contain only non-empty instance reference strings.")
    if request["data_disk_ids"] is not None:
        if not isinstance(request["data_disk_ids"], list):
            raise RecipeError("data_disk_ids must be a JSON list when provided.")
        if not all(isinstance(item, str) and item for item in request["data_disk_ids"]):
            raise RecipeError("data_disk_ids must contain only non-empty disk identifier strings.")
    if request["use_consistency_group_snapshot"]:
        raise RecipeError(
            "GCP standard disk snapshots do not expose a provider-native consistency group snapshot feature. "
            "Leave use_consistency_group_snapshot=false for this recipe."
        )
    request["snapshot_tags"] = normalize_labels(request["snapshot_tags"])


def build_clients() -> Dict[str, Any]:
    return {
        "instances": compute_v1.InstancesClient(),
        "disks": compute_v1.DisksClient(),
        "region_disks": compute_v1.RegionDisksClient(),
        "snapshots": compute_v1.SnapshotsClient(),
    }


def resolve_instances(
    client: compute_v1.InstancesClient,
    project: str,
    target_instances: Sequence[str],
) -> Dict[str, Dict[str, Any]]:
    resolved: Dict[str, Dict[str, Any]] = {}
    for reference in target_instances:
        zone, instance_name = parse_instance_reference(reference)
        if zone is not None:
            instance = client.get(project=project, zone=zone, instance=instance_name)
            resolved[reference] = normalize_instance(instance, requested_reference=reference, zone=zone)
            continue

        matches: List[Dict[str, Any]] = []
        pager = client.aggregated_list(project=project)
        for scope, scoped_list in pager:
            for item in list(scoped_list.instances or []):
                if item.name == instance_name:
                    matches.append(normalize_instance(item, requested_reference=reference, zone=extract_scope_name(scope)))
        if not matches:
            raise RecipeError(
                "Could not find a Compute Engine instance matching reference "
                f"{reference!r}. Use an instance name, a zone/name pair, or a full self-link."
            )
        if len(matches) > 1:
            zones = ", ".join(sorted(item["zone"] for item in matches if item.get("zone")))
            raise RecipeError(
                f"Instance reference {reference!r} is ambiguous across zones: {zones}. "
                "Use zone/name or a full self-link instead."
            )
        resolved[reference] = matches[0]
    return resolved


def describe_attached_disks(
    *,
    project: str,
    instances: Dict[str, Dict[str, Any]],
    disks_client: compute_v1.DisksClient,
    region_disks_client: compute_v1.RegionDisksClient,
) -> List[Dict[str, Any]]:
    disks: List[Dict[str, Any]] = []
    for instance in instances.values():
        for attached_disk in instance["attached_disks"]:
            source = attached_disk.get("source")
            if not source:
                continue
            scope_type, scope_name, disk_name = parse_disk_reference(source)
            if scope_type == "zone":
                disk = disks_client.get(project=project, zone=scope_name, disk=disk_name)
            else:
                disk = region_disks_client.get(project=project, region=scope_name, disk=disk_name)
            disks.append(
                normalize_disk(
                    disk,
                    instance=instance,
                    attached_disk=attached_disk,
                    scope_type=scope_type,
                    scope_name=scope_name,
                )
            )
    return disks


def select_disks(
    *,
    target_instances: Sequence[str],
    disks: Sequence[Dict[str, Any]],
    include_boot_disk: bool,
    requested_data_disk_ids: Optional[Sequence[str]],
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    discovered_data_disk_ids: set[str] = set()
    wanted_data_disk_ids = set(requested_data_disk_ids or []) if requested_data_disk_ids is not None else None
    instance_rank = {instance_ref: index for index, instance_ref in enumerate(target_instances)}

    for disk in sorted(
        disks,
        key=lambda item: (
            instance_rank.get(item.get("requested_instance_reference", ""), len(instance_rank)),
            0 if item.get("disk_usage") == "boot" else 1,
            item.get("disk_name", ""),
        ),
    ):
        if disk.get("disk_usage") == "boot":
            if include_boot_disk:
                selected.append(disk)
            continue
        if wanted_data_disk_ids is None:
            selected.append(disk)
            continue
        if any(identifier in wanted_data_disk_ids for identifier in disk_identifier_candidates(disk)):
            selected.append(disk)
            discovered_data_disk_ids.update(
                identifier for identifier in disk_identifier_candidates(disk) if identifier in wanted_data_disk_ids
            )

    if wanted_data_disk_ids is not None:
        missing = sorted(wanted_data_disk_ids - discovered_data_disk_ids)
        if missing:
            raise RecipeError(
                "The following data_disk_ids are not attached data disks on the selected instances: "
                + ", ".join(missing)
            )
    if not selected:
        raise RecipeError("No attached disks matched the requested snapshot scope.")
    return selected


def create_individual_snapshots(
    *,
    request: Dict[str, Any],
    instances: Dict[str, Dict[str, Any]],
    disks: Sequence[Dict[str, Any]],
    disks_client: compute_v1.DisksClient,
    region_disks_client: compute_v1.RegionDisksClient,
    snapshots_client: compute_v1.SnapshotsClient,
) -> Dict[str, Any]:
    created: List[Dict[str, Any]] = []
    timestamp = utc_timestamp()

    for disk in disks:
        instance = disk["instance"]
        snapshot_name = build_snapshot_name(
            request["snapshot_name_prefix"],
            instance.get("instance_name"),
            disk.get("disk_name"),
            timestamp,
        )
        snapshot_resource = compute_v1.Snapshot(
            name=snapshot_name,
            description=request["snapshot_description"] or None,
        )
        if request["snapshot_tags"]:
            snapshot_resource.labels = request["snapshot_tags"]

        if disk["scope_type"] == "zone":
            operation = disks_client.create_snapshot(
                project=request["project"],
                zone=disk["scope_name"],
                disk=disk["disk_name"],
                snapshot_resource=snapshot_resource,
            )
        else:
            operation = region_disks_client.create_snapshot(
                project=request["project"],
                region=disk["scope_name"],
                disk=disk["disk_name"],
                snapshot_resource=snapshot_resource,
            )

        wait_for_extended_operation(
            operation,
            timeout_seconds=request["snapshot_ready_timeout_seconds"],
            description=f"create snapshot for disk {disk['disk_name']}",
        )
        created.append(
            {
                "disk": disk,
                "instance": instance,
                "snapshot_name": snapshot_name,
            }
        )

    snapshots = get_or_wait_for_snapshots(
        snapshots_client,
        request["project"],
        [item["snapshot_name"] for item in created],
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    )
    snapshot_map = {snapshot["snapshot_name"]: snapshot for snapshot in snapshots}

    return {
        "provider": "gcp",
        "project": request["project"],
        "consistency_mode": "independent_snapshots",
        "consistency_group_id": None,
        "requested_instance_ids": list(request["target_instances"]),
        "created_snapshot_count": len(created),
        "results": [
            build_result_item(
                instance=item["instance"],
                disk=item["disk"],
                snapshot=snapshot_map.get(item["snapshot_name"], {}),
                snapshot_name=item["snapshot_name"],
            )
            for item in created
        ],
    }


def get_or_wait_for_snapshots(
    client: compute_v1.SnapshotsClient,
    project: str,
    snapshot_names: Sequence[str],
    *,
    wait_for_ready: bool,
    ready_timeout_seconds: int,
    poll_interval_seconds: int,
) -> List[Dict[str, Any]]:
    timeout = ready_timeout_seconds if wait_for_ready else MATERIALIZE_TIMEOUT_DEFAULT
    deadline = time.time() + timeout
    while True:
        snapshots: List[Dict[str, Any]] = []
        visible: set[str] = set()
        for snapshot_name in snapshot_names:
            try:
                snapshot = client.get(project=project, snapshot=snapshot_name)
            except NotFound:
                continue
            normalized = normalize_snapshot(snapshot)
            snapshots.append(normalized)
            visible.add(snapshot_name)
        all_visible = len(visible) == len(snapshot_names)
        if all_visible and not wait_for_ready:
            snapshot_map = {snapshot["snapshot_name"]: snapshot for snapshot in snapshots}
            return [snapshot_map[name] for name in snapshot_names]
        if all_visible and all(snapshot_is_ready(snapshot) for snapshot in snapshots):
            snapshot_map = {snapshot["snapshot_name"]: snapshot for snapshot in snapshots}
            return [snapshot_map[name] for name in snapshot_names]
        if time.time() >= deadline:
            states = {snapshot["snapshot_name"]: snapshot.get("snapshot_state") for snapshot in snapshots}
            for snapshot_name in snapshot_names:
                states.setdefault(snapshot_name, "NOT_VISIBLE")
            raise RecipeError(f"Timed out while waiting for snapshots to become ready: {states}")
        time.sleep(poll_interval_seconds)


def normalize_instance(instance: compute_v1.Instance, *, requested_reference: str, zone: str) -> Dict[str, Any]:
    return {
        "requested_reference": requested_reference,
        "instance_id": str(instance.id),
        "instance_name": instance.name,
        "zone": zone,
        "attached_disks": [normalize_attached_disk(disk) for disk in list(instance.disks or [])],
    }


def normalize_attached_disk(attached_disk: compute_v1.AttachedDisk) -> Dict[str, Any]:
    return {
        "source": attached_disk.source,
        "device_name": attached_disk.device_name,
        "boot": bool(attached_disk.boot),
        "mode": attached_disk.mode,
        "type": attached_disk.type_,
    }


def normalize_disk(
    disk: compute_v1.Disk,
    *,
    instance: Dict[str, Any],
    attached_disk: Dict[str, Any],
    scope_type: str,
    scope_name: str,
) -> Dict[str, Any]:
    return {
        "instance": instance,
        "requested_instance_reference": instance["requested_reference"],
        "instance_id": instance["instance_id"],
        "instance_name": instance["instance_name"],
        "disk_id": str(disk.id),
        "disk_name": disk.name,
        "disk_self_link": disk.self_link,
        "disk_usage": "boot" if attached_disk.get("boot") else "data",
        "disk_type": last_path_component(disk.type_),
        "scope_type": scope_type,
        "scope_name": scope_name,
        "zone": scope_name,
        "labels": dict(disk.labels or {}),
    }


def normalize_snapshot(snapshot: compute_v1.Snapshot) -> Dict[str, Any]:
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.name,
        "snapshot_state": snapshot.status,
        "source_disk": snapshot.source_disk,
        "labels": dict(snapshot.labels or {}),
        "storage_locations": list(snapshot.storage_locations or []),
    }


def snapshot_is_ready(snapshot: Dict[str, Any]) -> bool:
    return str(snapshot.get("snapshot_state", "")).upper() == "READY"


def build_result_item(
    *,
    instance: Dict[str, Any],
    disk: Dict[str, Any],
    snapshot: Dict[str, Any],
    snapshot_name: str,
) -> Dict[str, Any]:
    return {
        "instance_id": instance.get("instance_id"),
        "instance_name": instance.get("instance_name"),
        "disk_id": disk.get("disk_id"),
        "disk_name": disk.get("disk_name"),
        "disk_usage": disk.get("disk_usage"),
        "disk_type": disk.get("disk_type"),
        "zone": disk.get("zone"),
        "snapshot_id": snapshot.get("snapshot_id"),
        "snapshot_name": snapshot_name,
        "snapshot_state": snapshot.get("snapshot_state"),
        "consistency_mode": "independent_snapshots",
        "consistency_group_id": None,
    }


def wait_for_extended_operation(operation: Any, *, timeout_seconds: int, description: str) -> None:
    operation.result(timeout=timeout_seconds)
    if getattr(operation, "error_code", None):
        raise RecipeError(
            f"Failed to {description}: {operation.error_code} {getattr(operation, 'error_message', '')}".strip()
        )
    exception = operation.exception()
    if exception is not None:
        raise RecipeError(f"Failed to {description}: {exception}")


def parse_instance_reference(reference: str) -> Tuple[Optional[str], str]:
    if reference.startswith("https://") and "/zones/" in reference and "/instances/" in reference:
        match = re.search(r"/zones/([^/]+)/instances/([^/]+)$", reference)
        if not match:
            raise RecipeError(f"Unsupported Compute Engine instance self-link: {reference}")
        return match.group(1), match.group(2)
    if "/" in reference and not reference.startswith("projects/"):
        zone, instance_name = reference.split("/", 1)
        if zone and instance_name:
            return zone, instance_name
    return None, reference


def parse_disk_reference(reference: str) -> Tuple[str, str, str]:
    zone_match = re.search(r"/zones/([^/]+)/disks/([^/]+)$", reference)
    if zone_match:
        return "zone", zone_match.group(1), zone_match.group(2)
    region_match = re.search(r"/regions/([^/]+)/disks/([^/]+)$", reference)
    if region_match:
        return "region", region_match.group(1), region_match.group(2)
    raise RecipeError(f"Unsupported disk reference for snapshotting: {reference}")


def extract_scope_name(scope_key: str) -> str:
    return scope_key.split("/", 1)[-1]


def disk_identifier_candidates(disk: Dict[str, Any]) -> List[str]:
    candidates = [disk.get("disk_name"), disk.get("disk_id"), disk.get("disk_self_link")]
    return [candidate for candidate in candidates if candidate]


def normalize_labels(raw_tags: Any) -> Dict[str, str]:
    if raw_tags in (None, ""):
        return {}
    if isinstance(raw_tags, dict):
        return {str(key): str(value) for key, value in raw_tags.items()}
    if isinstance(raw_tags, list):
        labels: Dict[str, str] = {}
        for item in raw_tags:
            if not isinstance(item, dict):
                raise RecipeError("snapshot_tags list entries must be objects with key/value pairs.")
            key = item.get("Key", item.get("key"))
            value = item.get("Value", item.get("value", ""))
            if not isinstance(key, str) or not key:
                raise RecipeError("snapshot_tags entries must include a non-empty Key or key field.")
            labels[key] = str(value)
        return labels
    raise RecipeError("snapshot_tags must be a JSON object or a JSON list of {Key, Value} items.")


def build_snapshot_name(prefix: str, *parts: Optional[str]) -> str:
    tokens = [sanitize_name_token(prefix)] + [sanitize_name_token(part) for part in parts if part]
    joined = "-".join(token for token in tokens if token)
    joined = re.sub(r"-+", "-", joined).strip("-")
    if not joined:
        joined = "snapshot"
    if not joined[0].isalpha():
        joined = f"s-{joined}"
    joined = joined[:NAME_MAX_LENGTH].rstrip("-")
    if not joined[-1].isalnum():
        joined = f"{joined[:-1]}0" if len(joined) > 1 else "snapshot0"
    return joined


def sanitize_name_token(value: Optional[str]) -> str:
    token = re.sub(r"[^a-z0-9-]+", "-", str(value or "").lower())
    return token.strip("-")


def last_path_component(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.rsplit("/", 1)[-1]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%SZ").lower()


def env_required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RecipeError(f"Missing required environment variable: {name}")
    return value


def env_json_required(name: str) -> Any:
    value = os.environ.get(name)
    if value is None:
        raise RecipeError(f"Missing required environment variable: {name}")
    return parse_json_env(name, value)


def env_json_optional(name: str) -> Any:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return parse_json_env(name, value)


def parse_json_env(name: str, value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RecipeError(f"Environment variable {name} does not contain valid JSON: {exc}") from exc


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise RecipeError(f"Environment variable {name} must be a boolean string, got: {value}")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RecipeError(f"Environment variable {name} must be an integer, got: {value}") from exc
    if parsed <= 0:
        raise RecipeError(f"Environment variable {name} must be positive, got: {value}")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
