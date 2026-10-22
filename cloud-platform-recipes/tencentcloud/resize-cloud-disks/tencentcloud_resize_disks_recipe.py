#!/usr/bin/env python3
"""Resize multiple Tencent Cloud CBS disks for an Ansible recipe.

The script reads its input from environment variables so the playbook can avoid
passing structured JSON through a shell command line.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence

from tencentcloud.cbs.v20170312 import cbs_client, models as cbs_models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

POLL_INTERVAL_DEFAULT = 10
READY_TIMEOUT_DEFAULT = 1800
DESCRIBE_LIMIT = 100
EXPANDING_STATE = "EXPANDING"
FAILURE_STATES = {"ERROR", "ROLLBACK"}


class RecipeError(RuntimeError):
    """User-facing validation or workflow error."""


def main() -> int:
    try:
        request = load_request()
        validate_request(request)
        cred = load_credentials()
        cbs = cbs_client.CbsClient(cred, request["region"])

        disk_ids = [item["disk_id"] for item in request["resize_requests"]]
        discovered = describe_disks(cbs, disk_ids)
        plan = build_resize_plan(request["resize_requests"], discovered)

        submissions: Dict[str, Dict[str, Any]] = {}
        for item in plan:
            if item["status"] != "resize_required":
                continue
            response = resize_disk(cbs, item["disk_id"], item["target_size_gb"])
            submissions[item["disk_id"]] = response

        final_disks = discovered
        if submissions and request["wait_for_disk_ready"]:
            final_disks = wait_for_disks(
                cbs,
                target_sizes={item["disk_id"]: item["target_size_gb"] for item in plan},
                disk_ids=list(submissions),
                ready_timeout_seconds=request["disk_ready_timeout_seconds"],
                poll_interval_seconds=request["disk_poll_interval_seconds"],
            )

        result = build_result(
            request=request,
            plan=plan,
            final_disks=final_disks,
            submissions=submissions,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RecipeError as exc:
        print(f"recipe error: {exc}", file=sys.stderr)
        return 2
    except TencentCloudSDKException as exc:
        print(f"tencentcloud sdk error: {exc}", file=sys.stderr)
        return 3


def load_request() -> Dict[str, Any]:
    raw_resize_requests = env_json_optional("RECIPE_DISK_RESIZE_REQUESTS_JSON")
    raw_disk_ids = env_json_optional("RECIPE_DISK_IDS_JSON")
    uniform_target_size = env_int_optional("RECIPE_TARGET_DISK_SIZE_GB")

    if raw_resize_requests is not None:
        resize_requests = raw_resize_requests
    else:
        if raw_disk_ids is None or uniform_target_size is None:
            raise RecipeError(
                "Provide disk_resize_requests, or provide both disk_ids and target_disk_size_gb."
            )
        if not isinstance(raw_disk_ids, list):
            raise RecipeError("disk_ids must be a JSON list when provided.")
        resize_requests = [
            {"disk_id": disk_id, "target_size_gb": uniform_target_size} for disk_id in raw_disk_ids
        ]

    if raw_resize_requests is not None and (raw_disk_ids is not None or uniform_target_size is not None):
        raise RecipeError(
            "Use either disk_resize_requests or disk_ids with target_disk_size_gb, not both."
        )

    return {
        "region": env_required("TENCENTCLOUD_REGION"),
        "resize_requests": resize_requests,
        "wait_for_disk_ready": env_bool("RECIPE_WAIT_FOR_DISK_READY", True),
        "disk_ready_timeout_seconds": env_int(
            "RECIPE_DISK_READY_TIMEOUT_SECONDS", READY_TIMEOUT_DEFAULT
        ),
        "disk_poll_interval_seconds": env_int(
            "RECIPE_DISK_POLL_INTERVAL_SECONDS", POLL_INTERVAL_DEFAULT
        ),
    }


def validate_request(request: Dict[str, Any]) -> None:
    resize_requests = request["resize_requests"]
    if not isinstance(resize_requests, list) or not resize_requests:
        raise RecipeError("disk_resize_requests must be a non-empty JSON list.")

    seen_disk_ids: set[str] = set()
    for index, item in enumerate(resize_requests):
        if not isinstance(item, dict):
            raise RecipeError(
                f"disk_resize_requests[{index}] must be an object with disk_id and target_size_gb."
            )
        disk_id = item.get("disk_id")
        if not isinstance(disk_id, str) or not disk_id.strip():
            raise RecipeError(f"disk_resize_requests[{index}].disk_id must be a non-empty string.")
        normalized_disk_id = disk_id.strip()
        if normalized_disk_id in seen_disk_ids:
            raise RecipeError(f"disk_resize_requests contains duplicate disk_id: {normalized_disk_id}")
        seen_disk_ids.add(normalized_disk_id)
        item["disk_id"] = normalized_disk_id
        item["target_size_gb"] = positive_int(
            item.get("target_size_gb"),
            f"disk_resize_requests[{index}].target_size_gb",
        )

    if not isinstance(request["wait_for_disk_ready"], bool):
        raise RecipeError("wait_for_disk_ready must be a boolean.")


def load_credentials() -> credential.Credential:
    secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID", "")
    secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
    token = os.environ.get("TENCENTCLOUD_TOKEN") or None
    if not secret_id or not secret_key:
        raise RecipeError(
            "Set Tencent Cloud credentials with TENCENTCLOUD_SECRET_ID and "
            "TENCENTCLOUD_SECRET_KEY, or pass tencentcloud_secret_id and "
            "tencentcloud_secret_key into the playbook."
        )
    return credential.Credential(secret_id, secret_key, token)


def describe_disks(client: cbs_client.CbsClient, disk_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    disks: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks(list(disk_ids), DESCRIBE_LIMIT):
        payload = {"DiskIds": chunk, "Limit": len(chunk)}
        response = cbs_call(client, "DescribeDisks", cbs_models.DescribeDisksRequest, payload)
        for disk in response.get("DiskSet", []):
            disk_id = disk.get("DiskId")
            if disk_id:
                disks[disk_id] = disk

    missing = [disk_id for disk_id in disk_ids if disk_id not in disks]
    if missing:
        raise RecipeError(
            "The following cloud disks were not found in the target region: " + ", ".join(missing)
        )
    return disks


def build_resize_plan(
    resize_requests: Sequence[Dict[str, Any]],
    discovered: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for item in resize_requests:
        disk_id = item["disk_id"]
        disk = discovered[disk_id]
        current_size = positive_int(disk.get("DiskSize"), f"DescribeDisks.DiskSize for {disk_id}")
        target_size = item["target_size_gb"]
        disk_state = disk.get("DiskState")

        if disk_state in FAILURE_STATES:
            raise RecipeError(f"Disk {disk_id} is in failure state {disk_state}.")
        if disk_state == EXPANDING_STATE:
            raise RecipeError(
                f"Disk {disk_id} is already expanding. Wait for the current operation to finish "
                "before running this recipe again."
            )
        if current_size > target_size:
            raise RecipeError(
                f"Disk {disk_id} is {current_size} GB, which is larger than the requested "
                f"target of {target_size} GB. Tencent Cloud disk capacity cannot be reduced."
            )

        plan.append(
            {
                "disk_id": disk_id,
                "disk": disk,
                "current_size_gb": current_size,
                "target_size_gb": target_size,
                "status": "already_at_target" if current_size == target_size else "resize_required",
            }
        )
    return plan


def resize_disk(client: cbs_client.CbsClient, disk_id: str, target_size_gb: int) -> Dict[str, Any]:
    payload = {
        "DiskId": disk_id,
        "DiskSize": target_size_gb,
        "ClientToken": uuid.uuid4().hex,
    }
    return cbs_call(client, "ResizeDisk", cbs_models.ResizeDiskRequest, payload)


def wait_for_disks(
    client: cbs_client.CbsClient,
    *,
    target_sizes: Dict[str, int],
    disk_ids: Sequence[str],
    ready_timeout_seconds: int,
    poll_interval_seconds: int,
) -> Dict[str, Dict[str, Any]]:
    deadline = time.time() + ready_timeout_seconds
    last_disks: Dict[str, Dict[str, Any]] = {}
    while True:
        last_disks = describe_disks(client, disk_ids)
        pending: List[str] = []
        for disk_id in disk_ids:
            disk = last_disks.get(disk_id, {})
            state = disk.get("DiskState")
            current_size = integer_or_none(disk.get("DiskSize"))
            if state in FAILURE_STATES:
                raise RecipeError(
                    f"Disk {disk_id} entered failure state {state} while expanding."
                )
            if current_size is None or current_size < target_sizes[disk_id] or state == EXPANDING_STATE:
                pending.append(disk_id)

        if not pending:
            return last_disks
        if time.time() >= deadline:
            states = {
                disk_id: {
                    "disk_size_gb": integer_or_none(last_disks.get(disk_id, {}).get("DiskSize")),
                    "disk_state": last_disks.get(disk_id, {}).get("DiskState", "NOT_VISIBLE"),
                    "target_size_gb": target_sizes[disk_id],
                }
                for disk_id in pending
            }
            raise RecipeError(f"Timed out while waiting for disks to finish expanding: {states}")
        time.sleep(poll_interval_seconds)


def build_result(
    *,
    request: Dict[str, Any],
    plan: Sequence[Dict[str, Any]],
    final_disks: Dict[str, Dict[str, Any]],
    submissions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for item in plan:
        disk_id = item["disk_id"]
        disk = final_disks.get(disk_id, item["disk"])
        status = item["status"]
        if status == "resize_required":
            status = "resized" if request["wait_for_disk_ready"] else "resize_submitted"
        response = submissions.get(disk_id, {})
        results.append(
            {
                "disk_id": disk_id,
                "disk_name": disk.get("DiskName"),
                "disk_type": disk.get("DiskType"),
                "disk_usage": disk.get("DiskUsage"),
                "zone": (disk.get("Placement") or {}).get("Zone"),
                "previous_size_gb": item["current_size_gb"],
                "target_size_gb": item["target_size_gb"],
                "observed_size_gb": integer_or_none(disk.get("DiskSize")),
                "disk_state": disk.get("DiskState"),
                "status": status,
                "request_id": response.get("RequestId"),
            }
        )

    resized_count = sum(1 for item in plan if item["status"] == "resize_required")
    return {
        "provider": "tencentcloud",
        "region": request["region"],
        "wait_for_disk_ready": request["wait_for_disk_ready"],
        "requested_disk_count": len(plan),
        "resized_count": resized_count,
        "skipped_count": len(plan) - resized_count,
        "results": results,
    }


def cbs_call(
    client: cbs_client.CbsClient,
    method_name: str,
    request_cls: Any,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    request = request_cls()
    request.from_json_string(json.dumps(payload))
    response = getattr(client, method_name)(request)
    return json.loads(response.to_json_string())


def positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise RecipeError(f"{field_name} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RecipeError(f"{field_name} must be a positive integer.") from exc
    if parsed <= 0 or str(value).strip() != str(parsed):
        raise RecipeError(f"{field_name} must be a positive integer.")
    return parsed


def integer_or_none(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def env_required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RecipeError(f"Missing required environment variable: {name}")
    return value


def env_json_optional(name: str) -> Any:
    value = os.environ.get(name)
    if value is None or value == "" or value == "null":
        return None
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
    return positive_int(value, name)


def env_int_optional(name: str) -> Optional[int]:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return positive_int(value, name)


def chunks(items: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


if __name__ == "__main__":
    sys.exit(main())
