#!/usr/bin/env python3
"""Tencent Cloud VM disk snapshot workflow for Ansible.

The script reads its input from environment variables so the playbook can avoid
passing structured JSON through a shell command line.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cbs.v20170312 import cbs_client, models as cbs_models
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models

POLL_INTERVAL_DEFAULT = 10
READY_TIMEOUT_DEFAULT = 1800
MATERIALIZE_TIMEOUT_DEFAULT = 60


class RecipeError(RuntimeError):
    """User-facing validation or workflow error."""


def main() -> int:
    try:
        request = load_request()
        validate_request(request)
        cred = load_credentials()
        cvm = cvm_client.CvmClient(cred, request["region"])
        cbs = cbs_client.CbsClient(cred, request["region"])

        instances = describe_instances(cvm, request["target_instances"])
        disks = describe_attached_disks(cbs, request["target_instances"])
        selected_disks = select_disks(
            target_instances=request["target_instances"],
            disks=disks,
            include_boot_disk=request["include_boot_disk"],
            requested_data_disk_ids=request["data_disk_ids"],
        )
        validate_snapshot_eligibility(selected_disks)

        if request["use_consistency_group_snapshot"]:
            result = create_snapshot_group(cbs, request, instances, selected_disks)
        else:
            result = create_individual_snapshots(cbs, request, instances, selected_disks)

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RecipeError as exc:
        print(f"recipe error: {exc}", file=sys.stderr)
        return 2
    except TencentCloudSDKException as exc:
        print(f"tencentcloud sdk error: {exc}", file=sys.stderr)
        return 3


def load_request() -> Dict[str, Any]:
    return {
        "region": env_required("TENCENTCLOUD_REGION"),
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
    if request["snapshot_description"]:
        raise RecipeError(
            "snapshot_description is not supported by the Tencent Cloud CBS snapshot APIs used by this recipe."
        )
    if request["use_consistency_group_snapshot"] and len(request["target_instances"]) != 1:
        raise RecipeError(
            "Tencent Cloud snapshot groups require the selected disks to belong to the same CVM instance. "
            "Set target_instances to a single instance when use_consistency_group_snapshot=true."
        )
    request["snapshot_tags"] = normalize_tags(request["snapshot_tags"])


def load_credentials() -> credential.Credential:
    secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID", "")
    secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
    token = os.environ.get("TENCENTCLOUD_TOKEN") or None
    if not secret_id or not secret_key:
        raise RecipeError(
            "Set Tencent Cloud credentials with TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY, "
            "or pass tencentcloud_secret_id and tencentcloud_secret_key into the playbook."
        )
    return credential.Credential(secret_id, secret_key, token)


def describe_instances(client: cvm_client.CvmClient, instance_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    instance_map: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks(list(instance_ids), 100):
        payload = {"InstanceIds": chunk, "Limit": len(chunk)}
        response = cvm_call(client, "DescribeInstances", cvm_models.DescribeInstancesRequest, payload)
        for instance in response.get("InstanceSet", []):
            instance_map[instance["InstanceId"]] = instance
    missing = [instance_id for instance_id in instance_ids if instance_id not in instance_map]
    if missing:
        raise RecipeError(f"The following CVM instances were not found in the target region: {', '.join(missing)}")
    return instance_map


def describe_attached_disks(client: cbs_client.CbsClient, instance_ids: Sequence[str]) -> List[Dict[str, Any]]:
    disks: List[Dict[str, Any]] = []
    for instance_id in instance_ids:
        offset = 0
        while True:
            payload = {
                "Filters": [{"Name": "instance-id", "Values": [instance_id]}],
                "Offset": offset,
                "Limit": 100,
            }
            response = cbs_call(client, "DescribeDisks", cbs_models.DescribeDisksRequest, payload)
            batch = response.get("DiskSet", [])
            disks.extend(batch)
            total = response.get("TotalCount", len(batch))
            offset += len(batch)
            if offset >= total or not batch:
                break
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
    instance_rank = {instance_id: index for index, instance_id in enumerate(target_instances)}

    for disk in sorted(
        disks,
        key=lambda item: (
            instance_rank.get(item.get("InstanceId", ""), len(instance_rank)),
            0 if item.get("DiskUsage") == "SYSTEM_DISK" else 1,
            item.get("DiskId", ""),
        ),
    ):
        usage = disk.get("DiskUsage")
        disk_id = disk.get("DiskId")
        if usage == "SYSTEM_DISK":
            if include_boot_disk:
                selected.append(disk)
            continue
        if wanted_data_disk_ids is None:
            selected.append(disk)
            continue
        if disk_id in wanted_data_disk_ids:
            selected.append(disk)
            discovered_data_disk_ids.add(disk_id)

    if wanted_data_disk_ids is not None:
        missing_data_disk_ids = sorted(wanted_data_disk_ids - discovered_data_disk_ids)
        if missing_data_disk_ids:
            raise RecipeError(
                "The following data_disk_ids are not attached data disks on the selected instances: "
                + ", ".join(missing_data_disk_ids)
            )
    if not selected:
        raise RecipeError("No attached disks matched the requested snapshot scope.")
    return selected


def validate_snapshot_eligibility(disks: Sequence[Dict[str, Any]]) -> None:
    unsupported = [disk["DiskId"] for disk in disks if not disk.get("SnapshotAbility", False)]
    if unsupported:
        raise RecipeError(
            "The following disks do not report snapshot capability through DescribeDisks.SnapshotAbility: "
            + ", ".join(sorted(unsupported))
        )


def create_individual_snapshots(
    client: cbs_client.CbsClient,
    request: Dict[str, Any],
    instances: Dict[str, Dict[str, Any]],
    disks: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    created: List[Dict[str, Any]] = []
    timestamp = utc_timestamp()
    for disk in disks:
        snapshot_name = build_snapshot_name(
            request["snapshot_name_prefix"],
            disk.get("InstanceId"),
            disk.get("DiskId"),
            timestamp,
        )
        payload: Dict[str, Any] = {
            "DiskId": disk["DiskId"],
            "SnapshotName": snapshot_name,
        }
        if request["snapshot_tags"]:
            payload["Tags"] = request["snapshot_tags"]
        response = cbs_call(client, "CreateSnapshot", cbs_models.CreateSnapshotRequest, payload)
        created.append(
            {
                "disk": disk,
                "instance": instances[disk["InstanceId"]],
                "snapshot_id": response["SnapshotId"],
                "snapshot_name": snapshot_name,
            }
        )

    snapshots = get_or_wait_for_snapshots(
        client,
        [item["snapshot_id"] for item in created],
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    )
    snapshot_map = {snapshot["SnapshotId"]: snapshot for snapshot in snapshots}

    return {
        "provider": "tencentcloud",
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
    client: cbs_client.CbsClient,
    request: Dict[str, Any],
    instances: Dict[str, Dict[str, Any]],
    disks: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    instance_id = request["target_instances"][0]
    group_name = build_snapshot_name(request["snapshot_name_prefix"], instance_id, "group", utc_timestamp())
    payload: Dict[str, Any] = {
        "DiskIds": [disk["DiskId"] for disk in disks],
        "SnapshotGroupName": group_name,
    }
    if request["snapshot_tags"]:
        payload["Tags"] = request["snapshot_tags"]
    response = cbs_call(client, "CreateSnapshotGroup", cbs_models.CreateSnapshotGroupRequest, payload)
    snapshot_group_id = response["SnapshotGroupId"]

    snapshot_group = get_or_wait_for_snapshot_group(
        client,
        snapshot_group_id=snapshot_group_id,
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    )
    snapshot_ids = snapshot_group.get("SnapshotIdSet", []) or []
    snapshots = get_or_wait_for_snapshots(
        client,
        snapshot_ids,
        wait_for_ready=request["wait_for_snapshot_ready"],
        ready_timeout_seconds=request["snapshot_ready_timeout_seconds"],
        poll_interval_seconds=request["snapshot_poll_interval_seconds"],
    ) if snapshot_ids else []
    snapshot_map = {snapshot["SnapshotId"]: snapshot for snapshot in snapshots}
    snapshot_ids_by_disk = {snapshot.get("DiskId"): snapshot for snapshot in snapshots}

    results: List[Dict[str, Any]] = []
    for disk in disks:
        snapshot = snapshot_ids_by_disk.get(disk["DiskId"], {})
        results.append(
            build_result_item(
                instance=instances[disk["InstanceId"]],
                disk=disk,
                snapshot=snapshot,
                snapshot_id=snapshot.get("SnapshotId"),
                snapshot_name=snapshot.get("SnapshotName") or group_name,
                consistency_mode="snapshot_group",
                consistency_group_id=snapshot_group_id,
            )
        )

    return {
        "provider": "tencentcloud",
        "region": request["region"],
        "consistency_mode": "snapshot_group",
        "consistency_group_id": snapshot_group_id,
        "snapshot_group_name": group_name,
        "snapshot_group_state": snapshot_group.get("SnapshotGroupState"),
        "snapshot_group_percent": snapshot_group.get("Percent"),
        "snapshot_group_type": snapshot_group.get("SnapshotGroupType"),
        "requested_instance_ids": list(request["target_instances"]),
        "created_snapshot_count": len(results),
        "results": results,
    }


def get_or_wait_for_snapshots(
    client: cbs_client.CbsClient,
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
        snapshots = describe_snapshots_by_ids(client, snapshot_ids)
        snapshot_map = {snapshot["SnapshotId"]: snapshot for snapshot in snapshots}
        all_visible = all(snapshot_id in snapshot_map for snapshot_id in snapshot_ids)
        if all_visible and not wait_for_ready:
            return [snapshot_map[snapshot_id] for snapshot_id in snapshot_ids]
        if all_visible and all(snapshot_map[snapshot_id].get("SnapshotState") == "NORMAL" for snapshot_id in snapshot_ids):
            return [snapshot_map[snapshot_id] for snapshot_id in snapshot_ids]
        if time.time() >= deadline:
            states = {
                snapshot_id: snapshot_map.get(snapshot_id, {}).get("SnapshotState", "NOT_VISIBLE")
                for snapshot_id in snapshot_ids
            }
            raise RecipeError(f"Timed out while waiting for snapshots to become ready: {states}")
        time.sleep(poll_interval_seconds)


def get_or_wait_for_snapshot_group(
    client: cbs_client.CbsClient,
    *,
    snapshot_group_id: str,
    wait_for_ready: bool,
    ready_timeout_seconds: int,
    poll_interval_seconds: int,
) -> Dict[str, Any]:
    timeout = ready_timeout_seconds if wait_for_ready else MATERIALIZE_TIMEOUT_DEFAULT
    deadline = time.time() + timeout
    while True:
        snapshot_group = describe_snapshot_group_by_id(client, snapshot_group_id)
        if snapshot_group is not None:
            has_snapshots = bool(snapshot_group.get("SnapshotIdSet"))
            if has_snapshots and not wait_for_ready:
                return snapshot_group
            if snapshot_group.get("SnapshotGroupState") == "NORMAL" and has_snapshots:
                return snapshot_group
        if time.time() >= deadline:
            state = None if snapshot_group is None else snapshot_group.get("SnapshotGroupState")
            raise RecipeError(
                "Timed out while waiting for snapshot group metadata to become visible. "
                f"snapshot_group_id={snapshot_group_id}, state={state}"
            )
        time.sleep(poll_interval_seconds)


def describe_snapshots_by_ids(client: cbs_client.CbsClient, snapshot_ids: Sequence[str]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for chunk in chunks(list(snapshot_ids), 100):
        payload = {"SnapshotIds": chunk, "Limit": len(chunk)}
        response = cbs_call(client, "DescribeSnapshots", cbs_models.DescribeSnapshotsRequest, payload)
        snapshots.extend(response.get("SnapshotSet", []))
    return snapshots


def describe_snapshot_group_by_id(client: cbs_client.CbsClient, snapshot_group_id: str) -> Optional[Dict[str, Any]]:
    payload = {
        "Filters": [{"Name": "snapshot-group-id", "Values": [snapshot_group_id]}],
        "Limit": 1,
    }
    response = cbs_call(client, "DescribeSnapshotGroups", cbs_models.DescribeSnapshotGroupsRequest, payload)
    snapshot_groups = response.get("SnapshotGroupSet", [])
    if not snapshot_groups:
        return None
    return snapshot_groups[0]


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
        "instance_id": instance.get("InstanceId"),
        "instance_name": instance.get("InstanceName"),
        "disk_id": disk.get("DiskId"),
        "disk_name": disk.get("DiskName"),
        "disk_usage": disk.get("DiskUsage"),
        "disk_type": disk.get("DiskType"),
        "zone": (disk.get("Placement") or {}).get("Zone"),
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot_name,
        "snapshot_state": snapshot.get("SnapshotState"),
        "snapshot_percent": snapshot.get("Percent"),
        "consistency_mode": consistency_mode,
        "consistency_group_id": consistency_group_id,
    }


def normalize_tags(raw_tags: Any) -> List[Dict[str, str]]:
    if raw_tags in (None, ""):
        return []
    if isinstance(raw_tags, dict):
        return [{"Key": str(key), "Value": str(value)} for key, value in sorted(raw_tags.items())]
    if isinstance(raw_tags, list):
        normalized: List[Dict[str, str]] = []
        for item in raw_tags:
            if not isinstance(item, dict):
                raise RecipeError("snapshot_tags list entries must be objects with key/value pairs.")
            key = item.get("Key", item.get("key"))
            value = item.get("Value", item.get("value", ""))
            if not isinstance(key, str) or not key:
                raise RecipeError("snapshot_tags entries must include a non-empty Key or key field.")
            normalized.append({"Key": key, "Value": str(value)})
        return normalized
    raise RecipeError("snapshot_tags must be a JSON object or a JSON list of {Key, Value} items.")


def build_snapshot_name(prefix: str, *parts: Optional[str]) -> str:
    normalized_parts = [part for part in parts if part]
    return "-".join([prefix] + normalized_parts)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%SZ")


def cvm_call(client: cvm_client.CvmClient, method_name: str, request_cls: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = request_cls()
    request.from_json_string(json.dumps(payload))
    response = getattr(client, method_name)(request)
    return json.loads(response.to_json_string())


def cbs_call(client: cbs_client.CbsClient, method_name: str, request_cls: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = request_cls()
    request.from_json_string(json.dumps(payload))
    response = getattr(client, method_name)(request)
    return json.loads(response.to_json_string())


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
        raise RecipeError(f"Environment variable {name} must be greater than zero, got: {parsed}")
    return parsed


def chunks(items: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


if __name__ == "__main__":
    sys.exit(main())
