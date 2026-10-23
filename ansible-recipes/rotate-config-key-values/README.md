# Rotate TOML/YAML/JSON Key-Values

Chinese version: `README.zh-CN.md`

This recipe replaces scalar values in an existing TOML, YAML, or JSON configuration file while preserving the rest of the file. It is intended for rotating registry credentials, passwords, addresses, and similar key/value settings without rendering the whole configuration from a template.

## Files

- `playbook.yml`: the executable recipe
- `library/replace_config_key_values.py`: the Ansible module entrypoint
- `module_utils/config_key_value_editor.py`: the format-preserving editor

## Requirements

- Ansible installed on the control machine
- PyYAML available on the control machine; it is normally installed with Ansible
- Python's standard-library JSON support on the control machine
- SSH access and permission to read and replace the remote configuration file
- A target host Python interpreter supported by Ansible

The target host does not need a separate TOML, YAML, or JSON command-line tool. The file is read from the target host, edited on the control machine, and written back using Ansible's atomic copy mechanism.

## Variables

Required variables:

- `config_file`: remote TOML, YAML, or JSON file to update
- `config_format`: `toml`, `yaml`, or `json`
- `config_updates`: non-empty list of updates

Optional variables:

- `target_hosts`: target inventory group, defaults to `all`
- `config_become`: whether to use privilege escalation, defaults to `true`
- `backup_on_replace`: create an Ansible backup before replacing the file, defaults to `true`

Each update has a path list and a scalar value:

```yaml
config_updates:
  - path:
      - top_level_key
      - nested_key
    value: "new value"
```

String path segments select mapping/object keys. Values can be strings, booleans, integers, floats, or `null` for YAML and JSON. TOML does not support `null`.

### Selecting YAML list elements

Use `select` to identify one mapping in a list by exact scalar fields. This is safer than relying on a list index when registry order can change:

```yaml
config_updates:
  - path:
      - registries
      - select:
          address: "https://hub.usw-1.sealos.io"
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

Use `index` only when the list position is deliberately part of the configuration contract:

```yaml
config_updates:
  - path:
      - registries
      - index: 0
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

Selectors are applied only when they match exactly one list item. Missing or ambiguous selectors are skipped; if every update is skipped, the file is left unchanged.

## TOML example

For this configuration:

```toml
[plugins."io.containerd.grpc.v1.cri".registry.configs."sealos.hub:5000".auth]
username = "admin"
password = "passw0rd"
```

Use one path segment for each TOML key. Quoted TOML keys containing dots or colons must remain one path segment:

```yaml
config_file: /etc/containerd/config.toml
config_format: toml
config_updates:
  - path:
      - plugins
      - io.containerd.grpc.v1.cri
      - registry
      - configs
      - sealos.hub:5000
      - auth
      - password
    value: "{{ registry_password }}"
```

The recipe also supports multiple updates in one pass, for example updating both `username` and `password` under the same table.

## YAML example

For this configuration:

```yaml
registries:
  - address: https://hub.usw-1.sealos.io
    auth: admin:anotherpassw0rd
```

Use a selector for the registry and update the `auth` scalar:

```yaml
config_file: /etc/registry/config.yaml
config_format: yaml
config_updates:
  - path:
      - registries
      - select:
          address: "https://hub.usw-1.sealos.io"
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

Changed strings are emitted as safely escaped double-quoted scalars. Existing comments and unrelated formatting remain in place.

## JSON example

Standard JSON does not allow comments. A Docker config with an inline registry credential can look like this:

```json
{
  "auths": {
    "hub.usw-1.sealos.io": {
      "auth": "YWRtaW46b2xkLXBhc3M="
    }
  }
}
```

The registry hostname is one path segment even though it contains dots:

```yaml
config_file: /path/to/.docker/config.json
config_format: json
config_updates:
  - path:
      - auths
      - hub.usw-1.sealos.io
      - auth
    value: "{{ docker_auth }}"

docker_auth: "{{ (registry_username ~ ':' ~ registry_password) | b64encode }}"
```

The `auth` value is the base64 encoding of `username:password`, not the plaintext credential. JSON arrays can use the same `index` and `select` path segments described above.

## Usage

Keep credentials in an Ansible Vault-encrypted variables file instead of putting them directly on the command line:

```bash
ansible-vault encrypt rotate-registry-vars.yml

ansible-playbook \
  -i inventory.ini \
  --ask-vault-pass \
  -e @rotate-registry-vars.yml \
  ansible-recipes/rotate-config-key-values/playbook.yml
```

Check the planned change first:

```bash
ansible-playbook \
  -i inventory.ini \
  --check \
  -e @rotate-registry-vars.yml \
  ansible-recipes/rotate-config-key-values/playbook.yml
```

The editing and file-write tasks use `no_log` so the new credential is not printed in normal Ansible output. Do not use `--diff` for credential updates.

## Behavior and limitations

- Each update is evaluated independently. A path is applied only when it resolves to exactly one safely replaceable scalar value; missing, ambiguous, non-scalar, or unsupported target values are skipped.
- If at least one update changes a value, all applicable updates are written in one atomic operation. If no update applies, the file is left unchanged.
- YAML updates use PyYAML node locations but write only the selected scalar span, preserving comments and surrounding layout.
- JSON must be standard JSON without comments. A target object key is applied only when it occurs exactly once and points to a scalar value.
- JSON updates use Python's standard library and write only the selected scalar token, preserving surrounding whitespace and object order.
- YAML input must contain one document. Multi-line target values are not supported.
- TOML table paths and quoted keys are supported. A single-line target assignment is applied only when it occurs exactly once.
- The recipe preserves the existing file owner, group, and mode and uses Ansible's atomic `copy` operation.
- A backup is enabled by default; set `backup_on_replace: false` only when backups are handled elsewhere.
- The recipe only changes the configuration file. Restart or reload the service separately after validating the new credential.

## Validation

Run the syntax check before using the recipe:

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-config-key-values/playbook.yml
```

Test against a non-production inventory, use `--check` first, and confirm that the affected service accepts the resulting configuration before restarting it.
