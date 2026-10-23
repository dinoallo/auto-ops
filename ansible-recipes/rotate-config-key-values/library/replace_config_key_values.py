#!/usr/bin/python

"""Ansible module wrapper for the local TOML/YAML/JSON scalar editor."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.config_key_value_editor import (
    ConfigEditError,
    replace_config_values,
)


DOCUMENTATION = r"""
---
module: replace_config_key_values
short_description: Replace scalar values in TOML, YAML, or JSON text
description:
  - Resolves all requested paths before returning edited configuration text.
  - The caller is responsible for writing the returned content.
options:
  content:
    description: Configuration file contents.
    required: true
    type: str
  config_format:
    description: Configuration format.
    required: true
    choices: [toml, yaml, json]
    type: str
  updates:
    description: Paths and scalar values to replace.
    required: true
    type: list
"""


RETURN = r"""
content:
  description: Updated configuration file contents.
  returned: always
  type: str
updated_paths:
  description: Paths whose serialized value changed.
  returned: always
  type: list
"""


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "content": {"type": "str", "required": True},
            "config_format": {
                "type": "str",
                "required": True,
                "choices": ["toml", "yaml", "json"],
            },
            "updates": {"type": "list", "required": True},
        },
        supports_check_mode=True,
    )

    try:
        updated_content, updated_paths = replace_config_values(
            module.params["content"],
            module.params["config_format"],
            module.params["updates"],
        )
    except ConfigEditError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(
        changed=bool(updated_paths),
        content=updated_content,
        updated_paths=updated_paths,
    )


if __name__ == "__main__":
    main()
