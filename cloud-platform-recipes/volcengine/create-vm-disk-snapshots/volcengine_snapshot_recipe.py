#!/usr/bin/env python3
"""Volcengine ECS disk snapshot workflow for Ansible."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from volcenginesdkcore.api_client import ApiClient
from volcenginesdkcore.configuration import Configuration
from volcenginesdkcore.rest import ApiException
from volcenginesdkecs.api.ecs_api import ECSApi
from volcenginesdkecs.models.describe_instances_request import DescribeInstancesRequest
from volcenginesdkstorageebs.api.storage_ebs_api import STORAGEEBSApi
from volcenginesdkstorageebs.models.create_snapshot_group_request import CreateSnapshotGroupRequest
from volcenginesdkstorageebs.models.create_snapshot_request import CreateSnapshotRequest
from volcenginesdkstorageebs.models.describe_snapshot_groups_request import DescribeSnapshotGroupsRequest
from volcenginesdkstorageebs.models.describe_snapshots_request import DescribeSnapshotsRequest
from volcenginesdkstorageebs.models.describe_volumes_request import DescribeVolumesRequest
from volcenginesdkstorageebs.models.tag_for_create_snapshot_group_input import TagForCreateSnapshotGroupInput
from volcenginesdkstorageebs.models.tag_for_create_snapshot_input import TagForCreateSnapshotInput

POLL_INTERVAL_DEFAULT = 10
READY_TIMEOUT_DEFAULT = 1800
MATERIALIZE_TIMEOUT_DEFAULT = 60
API_PAGE_SIZE = 100


class RecipeError(RuntimeError):
    """User-facing validation or workflow error."""


def main() -> int:
    try:
        request = load_request()
        validate_request(request)
        clients = build_clients(request["region"])

        instances = describe_instances(clients["ecs"], request)
        volumes = describe_attached_volumes(clients["ebs"], request)
        selected_volumes = select_volumes(
            target_instances=request["target_instances"],
            volumes=volumes,
            include_boot_disk=request["include_boot_disk"],
            requested_data_disk_ids=request["data_disk_ids"],
        )

        if request["use_consistency_group_snapshot"]:
            result = create_snapshot_group(clients["ebs"], request, instances, selected_volumes)
        else:
            result = create_individual_snapshots(clients["ebs"], request, instances, selected_volumes)

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RecipeError as exc:
        print(f"recipe error: {exc}", file=sys.stderr)
        return 2
    except ApiException as exc:
        print(f"volcengine api error: {exc}", file=sys.stderr)
        return 3


def load_request() -> Dict[str, Any]:
    return {
        "region": env_required("VOLCENGINE_REGION"),
        "project_name": os.environ.get("RECIPE_VOLCENGINE_PROJECT_NAME") or None,
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
        raise RecipeError("target_instances must contain only non-empty instance ID strings.")
    if request["data_disk_ids"] is not None:
        if not isinstance(request["data_disk_ids"], list):
            raise RecipeError("data_disk_ids must be a JSON list when provided.")
        if not all(isinstance(item, str) and item for item in request["data_disk_ids"]):
            raise RecipeError("data_disk_ids must contain only non-empty disk ID strings.")
    if request["use_consistency_group_snapshot"] and len(request["target_instances"]) != 1:
        raise RecipeError(
            "Volcengine snapshot consistency groups apply to disks from one ECS instance. "
            "Set target_instances to a single instance when use_consistency_group_snapshot=true."
        )
    request["snapshot_tags"] = normalize_tags(request["snapshot_tags"])


def build_clients(region: str) -> Dict[str, Any]:
    access_key = os.environ.get("VOLCENGINE_ACCESS_KEY", "")
    secret_key = os.environ.get("VOLCENGINE_SECRET_KEY", "")
    session_token = os.environ.get("VOLCENGINE_SESSION_TOKEN") or None
    if not access_key or not secret_key:
        raise RecipeError(
            "Set Volcengine credentials with VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY, "
            "or pass volcengine_access_key and volcengine_secret_key into the playbook."
        )

    configuration = Configuration()
    configuration.ak = access_key
    configuration.sk = secret_key
    configuration.session_token = session_token
    configuration.region = region
    api_client = ApiClient(configuration)
    return {
        "ecs": ECSApi(api_client),
        "ebs": STORAGEEBSApi(api_client),
    }


def describe_instances(client: ECSApi, request: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    instance_map: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks(list(request["target_instances"]), API_PAGE_SIZE):
        response = client.describe_instances(
            DescribeInstancesRequest(
                instance_ids=chunk,
                max_results=len(chunk),
                project_name=request["project_name"],
            )
        )
        for instance in list(response.instances or []):
            normalized = normalize_instance(instance)
            instance_map[normalized["instance_id"]] = normalized
    missing = [instance_id for instance_id in request["target_instances"] if instance_id not in instance_map]
    if missing:
        raise RecipeError(
            "The following Volcengine ECS instances were not found in the target region: " + ", ".join(missing)
        )
    return instance_map


def describe_attached_volumes(client: STORAGEEBSApi, request: Dict[str, Any]) -> List[Dict[str, Any]]:
    volumes: List[Dict[str, Any]] = []
    for instance_id in request["target_instances"]:
        page_number = 1
        while True:
            response = client.describe_volumes(
                DescribeVolumesRequest(
                    instance_id=instance_id,
                    page_number=page_number,
                    page_size=API_PAGE_SIZE,
                    project_name=request["project_name"],
                )
            )
            batch = [normalize_volume(volume) for volume in list(response.volumes or [])]
            volumes.extend(batch)
            total_count = int(response.total_count or len(batch))
            if page_number * API_PAGE_SIZE >= total_count or not batch:
                break
            page_number += 1
    return volumes


def select_volumes(
    *,
    target_instances: Sequence[str],
    volumes: Sequence[Dict[str, Any]],
    include_boot_disk: bool,
    requested_data_disk_ids: Optional[Sequence[str]],
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    discovered_data_disk_ids: set[str] = set()
    wanted_data_disk_ids = set(requested_data_disk_ids or []) if requested_data_disk_ids is not None else None
    instance_rank = {instance_id: index for index, instance_id in enumerate(target_instances)}

    for volume in sorted(
        volumes,
        key=lambda item: (
            instance_rank.get(item.get("instance_id", ""), len(instance_rank)),
            0 if item.get("disk_usage") == "boot" else 1,
            item.get("disk_id", ""),
        ),
    ):
        if volume.get("disk_usage") == "boot":
            if include_boot_disk:
                selected.append(volume)
            continue
        if wanted_data_disk_ids is None:
            selected.append(volume)
            continue
        if volume.get("disk_id") in wanted_data_disk_ids or volume.get("disk_name") in wanted_data_disk_ids:
            selected.append(volume)
            if volume.get("disk_id") in wanted_data_disk_ids:
                discovered_data_disk_ids.add(volume["disk_id"])
            if volume.get("disk_name") in wanted_data_disk_ids:
                discovered_data_disk_ids.add(volume["disk_name"])

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
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    instances: Dict[str, Dict[str, Any]],
    volumes: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    created: List[Dict[str, Any]] = []
    timestamp = utc_timestamp()
    tags = build_snapshot_tags(request["snapshot_tags"])

    for volume in volumes:
        snapshot_name = build_snapshot_name(
            request["snapshot_name_prefix"],
            volume.get("instance_id"),
            volume.get("disk_id"),
            timestamp,
        )
        response = client.create_snapshot(
            CreateSnapshotRequest(
                volume_id=volume["disk_id"],
                snapshot_name=snapshot_name,
                description=request["snapshot_description"] or None,
                project_name=request["project_name"],
                tags=tags or None,
            )
        )
        created.append(
            {
                "disk": volume,
                "instance": instances[volume["instance_id"]],
                "snapshot_id": response.snapshot_id,
                "snapshot_name": snapshot_name,
            }
        )

    snapshots = get_or_wait_for_snapshots(
        client,
        request,
        [item["snapshot_id"] for item in created],
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    )
    snapshot_map = {snapshot["snapshot_id"]: snapshot for snapshot in snapshots}

    return {
        "provider": "volcengine",
        "region": request["region"],
        "consistency_mode": "independent_snapshots",
        "consistency_group_id": None,
        "requested_instance_ids": list(request["target_instances"]),
        "created_snapshot_count": len(created),
        "results": [
            build_result_item(
                instance=item["instance"],
                disk=item["disk"],
                snapshot=snapshot_map.get(item["snapshot_id"], {}),
                snapshot_id=item["snapshot_id"],
                snapshot_name=item["snapshot_name"],
                consistency_mode="independent_snapshots",
                consistency_group_id=None,
            )
            for item in created
        ],
    }


def create_snapshot_group(
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    instances: Dict[str, Dict[str, Any]],
    volumes: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    instance_id = request["target_instances"][0]
    group_name = build_snapshot_name(request["snapshot_name_prefix"], instance_id, "group", utc_timestamp())
    response = client.create_snapshot_group(
        CreateSnapshotGroupRequest(
            instance_id=instance_id,
            name=group_name,
            description=request["snapshot_description"] or None,
            volume_ids=[volume["disk_id"] for volume in volumes],
            project_name=request["project_name"],
            tags=build_snapshot_group_tags(request["snapshot_tags"]) or None,
        )
    )
    snapshot_group_id = response.snapshot_group_id

    snapshot_group = get_or_wait_for_snapshot_group(
        client,
        request,
        snapshot_group_id=snapshot_group_id,
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    )
    group_snapshots = snapshot_group.get("snapshots", [])
    snapshot_ids = [snapshot["snapshot_id"] for snapshot in group_snapshots if snapshot.get("snapshot_id")]
    snapshots = (
        get_or_wait_for_snapshots(
            client,
            request,
            snapshot_ids,
            wait_for_ready=request["wait_for_snapshot_ready"],
            ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
            poll_interval_seconds=request["snapshot_poll_interval_seconds"],
        )
        if snapshot_ids
        else []
    )
    snapshot_map = {snapshot["snapshot_id"]: snapshot for snapshot in snapshots}
    snapshot_by_disk = {
        snapshot.get("source_disk_id"): snapshot
        for snapshot in snapshots
        if snapshot.get("source_disk_id")
    }

    results: List[Dict[str, Any]] = []
    for volume in volumes:
        group_snapshot = next(
            (item for item in group_snapshots if item.get("source_disk_id") == volume["disk_id"]),
            {},
        )
        snapshot = snapshot_by_disk.get(volume["disk_id"], snapshot_map.get(group_snapshot.get("snapshot_id"), {}))
        results.append(
            build_result_item(
                instance=instances[volume["instance_id"]],
                disk=volume,
                snapshot=snapshot or group_snapshot,
                snapshot_id=group_snapshot.get("snapshot_id") or snapshot.get("snapshot_id"),
                snapshot_name=snapshot.get("snapshot_name") or group_name,
                consistency_mode="snapshot_group",
                consistency_group_id=snapshot_group_id,
            )
        )

    return {
        "provider": "volcengine",
        "region": request["region"],
        "consistency_mode": "snapshot_group",
        "consistency_group_id": snapshot_group_id,
        "snapshot_group_name": group_name,
        "snapshot_group_state": snapshot_group.get("status"),
        "requested_instance_ids": list(request["target_instances"]),
        "created_snapshot_count": len(results),
        "results": results,
    }


def get_or_wait_for_snapshots(
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    snapshot_ids: Sequence[str],
    *,
    wait_for_ready: bool,
    ready_timeout_seconds: int,
    poll_interval_seconds: int,
) -> List[Dict[str, Any]]:
    if not snapshot_ids:
        return []
    timeout = ready_timeout_seconds if wait_for_ready else MATERIALIZE_TIMEOUT_DEFAULT
    deadline = time.time() + timeout
    while True:
        snapshots = describe_snapshots_by_ids(client, request, snapshot_ids)
        snapshot_map = {snapshot["snapshot_id"]: snapshot for snapshot in snapshots}
        all_visible = all(snapshot_id in snapshot_map for snapshot_id in snapshot_ids)
        if all_visible and not wait_for_ready:
            return [snapshot_map[snapshot_id] for snapshot_id in snapshot_ids]
        if all_visible and all(snapshot_is_ready(snapshot_map[snapshot_id]) for snapshot_id in snapshot_ids):
            return [snapshot_map[snapshot_id] for snapshot_id in snapshot_ids]
        if time.time() >= deadline:
            states = {
                snapshot_id: snapshot_map.get(snapshot_id, {}).get("snapshot_state", "NOT_VISIBLE")
                for snapshot_id in snapshot_ids
            }
            raise RecipeError(f"Timed out while waiting for snapshots to become ready: {states}")
        time.sleep(poll_interval_seconds)


def get_or_wait_for_snapshot_group(
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    *,
    snapshot_group_id: str,
    wait_for_ready: bool,
    ready_timeout_seconds: int,
    poll_interval_seconds: int,
) -> Dict[str, Any]:
    timeout = ready_timeout_seconds if wait_for_ready else MATERIALIZE_TIMEOUT_DEFAULT
    deadline = time.time() + timeout
    while True:
        snapshot_group = describe_snapshot_group_by_id(client, request, snapshot_group_id)
        if snapshot_group is not None:
            has_snapshots = bool(snapshot_group.get("snapshots"))
            if has_snapshots and not wait_for_ready:
                return snapshot_group
            if has_snapshots and snapshot_group_is_ready(snapshot_group):
                return snapshot_group
        if time.time() >= deadline:
            state = None if snapshot_group is None else snapshot_group.get("status")
            raise RecipeError(
                "Timed out while waiting for snapshot group metadata to become visible. "
                f"snapshot_group_id={snapshot_group_id}, state={state}"
            )
        time.sleep(poll_interval_seconds)


def describe_snapshots_by_ids(
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    snapshot_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    response = client.describe_snapshots(
        DescribeSnapshotsRequest(
            snapshot_ids=list(snapshot_ids),
            page_number=1,
            page_size=len(snapshot_ids),
            project_name=request["project_name"],
        )
    )
    return [normalize_snapshot(snapshot) for snapshot in list(response.snapshots or [])]


def describe_snapshot_group_by_id(
    client: STORAGEEBSApi,
    request: Dict[str, Any],
    snapshot_group_id: str,
) -> Optional[Dict[str, Any]]:
    response = client.describe_snapshot_groups(
        DescribeSnapshotGroupsRequest(
            snapshot_group_ids=[snapshot_group_id],
            page_number=1,
            page_size=1,
            project_name=request["project_name"],
        )
    )
    groups = list(response.snapshot_groups or [])
    if not groups:
        return None
    return normalize_snapshot_group(groups[0])


def normalize_instance(instance: Any) -> Dict[str, Any]:
    return {
        "instance_id": getattr(instance, "instance_id", None),
        "instance_name": getattr(instance, "instance_name", None),
        "zone": getattr(instance, "zone_id", None),
    }


def normalize_volume(volume: Any) -> Dict[str, Any]:
    return {
        "disk_id": getattr(volume, "volume_id", None),
        "disk_name": getattr(volume, "volume_name", None),
        "instance_id": getattr(volume, "instance_id", None),
        "disk_usage": classify_volume_usage(getattr(volume, "kind", None)),
        "disk_type": getattr(volume, "volume_type", None),
        "zone": getattr(volume, "zone_id", None),
        "status": getattr(volume, "status", None),
        "kind": getattr(volume, "kind", None),
    }


def normalize_snapshot(snapshot: Any) -> Dict[str, Any]:
    return {
        "snapshot_id": getattr(snapshot, "snapshot_id", None),
        "snapshot_name": getattr(snapshot, "snapshot_name", None),
        "source_disk_id": getattr(snapshot, "volume_id", None),
        "snapshot_state": getattr(snapshot, "status", None),
        "snapshot_percent": getattr(snapshot, "progress", None),
    }


def normalize_snapshot_group(snapshot_group: Any) -> Dict[str, Any]:
    return {
        "snapshot_group_id": getattr(snapshot_group, "snapshot_group_id", None),
        "instance_id": getattr(snapshot_group, "instance_id", None),
        "name": getattr(snapshot_group, "name", None),
        "status": getattr(snapshot_group, "status", None),
        "snapshots": [normalize_group_snapshot(snapshot) for snapshot in list(getattr(snapshot_group, "snapshots", []) or [])],
    }


def normalize_group_snapshot(snapshot: Any) -> Dict[str, Any]:
    return {
        "snapshot_id": getattr(snapshot, "snapshot_id", None),
        "source_disk_id": getattr(snapshot, "volume_id", None),
        "snapshot_name": getattr(snapshot, "snapshot_name", None),
        "snapshot_state": getattr(snapshot, "status", None),
        "snapshot_percent": getattr(snapshot, "progress", None),
    }


def classify_volume_usage(kind: Optional[str]) -> str:
    lowered = str(kind or "").lower()
    if lowered in {"system", "boot", "root"}:
        return "boot"
    return "data"


def snapshot_is_ready(snapshot: Dict[str, Any]) -> bool:
    state = str(snapshot.get("snapshot_state", "")).lower()
    percent = int(snapshot.get("snapshot_percent") or 0)
    return state in {"available", "accomplished", "normal"} or percent >= 100


def snapshot_group_is_ready(snapshot_group: Dict[str, Any]) -> bool:
    snapshots = snapshot_group.get("snapshots", [])
    if not snapshots:
        return False
    state = str(snapshot_group.get("status", "")).lower()
    return state in {"available", "accomplished", "normal"} or all(snapshot_is_ready(snapshot) for snapshot in snapshots)


def build_result_item(
    *,
    instance: Dict[str, Any],
    disk: Dict[str, Any],
    snapshot: Dict[str, Any],
    snapshot_id: Optional[str],
    snapshot_name: Optional[str],
    consistency_mode: str,
    consistency_group_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "instance_id": instance.get("instance_id"),
        "instance_name": instance.get("instance_name"),
        "disk_id": disk.get("disk_id"),
        "disk_name": disk.get("disk_name"),
        "disk_usage": disk.get("disk_usage"),
        "disk_type": disk.get("disk_type"),
        "zone": disk.get("zone"),
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot_name,
        "snapshot_state": snapshot.get("snapshot_state"),
        "snapshot_percent": snapshot.get("snapshot_percent"),
        "consistency_mode": consistency_mode,
        "consistency_group_id": consistency_group_id,
    }


def normalize_tags(raw_tags: Any) -> List[Dict[str, str]]:
    if raw_tags in (None, ""):
        return []
    if isinstance(raw_tags, dict):
        return [{"key": str(key), "value": str(value)} for key, value in sorted(raw_tags.items())]
    if isinstance(raw_tags, list):
        normalized: List[Dict[str, str]] = []
        for item in raw_tags:
            if not isinstance(item, dict):
                raise RecipeError("snapshot_tags list entries must be objects with key/value pairs.")
            key = item.get("Key", item.get("key"))
            value = item.get("Value", item.get("value", ""))
            if not isinstance(key, str) or not key:
                raise RecipeError("snapshot_tags entries must include a non-empty Key or key field.")
            normalized.append({"key": key, "value": str(value)})
        return normalized
    raise RecipeError("snapshot_tags must be a JSON object or a JSON list of {Key, Value} items.")


def build_snapshot_tags(raw_tags: Sequence[Dict[str, str]]) -> List[TagForCreateSnapshotInput]:
    return [TagForCreateSnapshotInput(key=tag["key"], value=tag["value"]) for tag in raw_tags]


def build_snapshot_group_tags(raw_tags: Sequence[Dict[str, str]]) -> List[TagForCreateSnapshotGroupInput]:
    return [TagForCreateSnapshotGroupInput(key=tag["key"], value=tag["value"]) for tag in raw_tags]


def build_snapshot_name(prefix: str, *parts: Optional[str]) -> str:
    normalized_parts = [part for part in parts if part]
    return "-".join([prefix] + normalized_parts)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%SZ")


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


def chunks(values: Sequence[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


if __name__ == "__main__":
    sys.exit(main())
