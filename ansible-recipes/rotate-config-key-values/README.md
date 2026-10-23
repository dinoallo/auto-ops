# Rotate TOML/YAML Key-Values

Chinese version: `README.zh-CN.md`

This recipe replaces scalar values in an existing TOML or YAML configuration file while preserving the rest of the file. It is intended for rotating registry credentials, passwords, addresses, and similar key/value settings without rendering the whole configuration from a template.

## Files

- `playbook.yml`: the executable recipe
- `library/replace_config_key_values.py`: the Ansible module entrypoint
- `module_utils/config_key_value_editor.py`: the format-preserving editor

## Requirements

- Ansible installed on the control machine
- PyYAML available on the control machine; it is normally installed with Ansible
- SSH access and permission to read and replace the remote configuration file
- A target host Python interpreter supported by Ansible

The target host does not need a separate TOML or YAML command-line tool. The file is read from the target host, edited on the control machine, and written back using Ansible's atomic copy mechanism.

## Variables

Required variables:

- `config_file`: remote TOML or YAML file to update
- `config_format`: either `toml` or `yaml`
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

String path segments select mapping keys. Values can be strings, booleans, integers, floats, or `null` for YAML. TOML does not support `null`.

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

Selectors must match exactly one list item. A missing or ambiguous match fails before the file is written.

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

- Every requested path must resolve to exactly one scalar value. The recipe fails before writing if a key is missing or ambiguous.
- YAML updates use PyYAML node locations but write only the selected scalar span, preserving comments and surrounding layout.
- YAML input must contain one document. Multi-line target values are not supported.
- TOML table paths and quoted keys are supported. A target assignment must be a single-line value and must occur exactly once.
- The recipe preserves the existing file owner, group, and mode and uses Ansible's atomic `copy` operation.
- A backup is enabled by default; set `backup_on_replace: false` only when backups are handled elsewhere.
- The recipe only changes the configuration file. Restart or reload the service separately after validating the new credential.

## Validation

Run the syntax check before using the recipe:

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-config-key-values/playbook.yml
```

Test against a non-production inventory, use `--check` first, and confirm that the affected service accepts the resulting configuration before restarting it.
