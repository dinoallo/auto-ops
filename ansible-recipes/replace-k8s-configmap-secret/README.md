# Replacing Kubernetes ConfigMap or Secret Values

Chinese version: `README.zh-CN.md`

This recipe uses local kubeconfig files to patch one Kubernetes ConfigMap or
Secret in multiple clusters. It discovers every regular file directly under
`kc_dir` and runs one `kubectl patch` command for each file.

The patch contains only the supplied key/value pairs, so other keys in the
resource are preserved. ConfigMaps use `data`; Secrets use `stringData`, which
lets the caller provide the replacement values as plaintext strings.

## Files

- `playbook.yml`: the recipe playbook

## Requirements

- Ansible and `kubectl` available on the local Ansible control node
- A readable kubeconfig file for every target cluster under `kc_dir`
- The target ConfigMap or Secret already exists in the selected namespace
- Kubernetes permissions to patch the resource in every target cluster

The playbook runs on `localhost` with a local connection. It does not SSH to
Kubernetes nodes.

## Variables

- `kc_dir`: local directory containing kubeconfig files, defaults to `kc/` next
  to `playbook.yml`
- `kubectl_command`: kubectl executable or absolute path, defaults to `kubectl`
- `resource_kind`: `configmap` or `secret`, defaults to `configmap`
- `resource_name`: target ConfigMap or Secret name; required
- `namespace`: target namespace, defaults to `default`
- `cluster_resources`: optional mapping from a kubeconfig basename to a
  per-cluster resource override; supported fields are `resource_kind`,
  `resource_name`, and `namespace`, and omitted fields inherit the global
  value
- `key_values`: optional common mapping applied to every cluster
- `cluster_key_values`: optional mapping from each kubeconfig basename to that
  cluster's mapping; these values override the common `key_values`

Each per-cluster map must use the kubeconfig filename as its key. For example,
`cluster-a.kubeconfig` refers to `kc/cluster-a.kubeconfig`. A kubeconfig uses
the global resource target unless it has an entry in `cluster_resources`.
Every kubeconfig must receive at least one value from either `key_values` or
`cluster_key_values`.

## Usage

Validate the playbook syntax:

```bash
ansible-playbook --syntax-check \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml
```

Given this local directory:

```text
kc/
├── cluster-a.kubeconfig
└── cluster-b.kubeconfig
```

patch different values in each cluster:

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e kc_dir="$PWD/kc" \
  -e resource_kind=configmap \
  -e resource_name=app-settings \
  -e namespace=demo \
  -e 'cluster_key_values={"cluster-a.kubeconfig":{"APP_ENV":"production","API_URL":"https://api-a.example.invalid"},"cluster-b.kubeconfig":{"APP_ENV":"staging","API_URL":"https://api-b.example.invalid"}}'
```

The command above runs one patch through `cluster-a.kubeconfig` and one
through `cluster-b.kubeconfig`. The two `APP_ENV` values are independent.

To use the global resource for `cluster-a` but a different resource for
`cluster-b`, define a per-cluster resource override. The override can change
only the fields that differ:

```yaml
resource_kind: configmap
resource_name: app-settings
namespace: demo
cluster_resources:
  cluster-b.kubeconfig:
    resource_kind: secret
    resource_name: app-credentials-b
```

`cluster-a.kubeconfig` uses `configmap/app-settings` from the global settings;
`cluster-b.kubeconfig` uses `secret/app-credentials-b`. Both use the global
`demo` namespace.

To apply the same values everywhere and override one key in a specific
cluster:

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e kc_dir="$PWD/kc" \
  -e resource_name=app-settings \
  -e 'key_values={"LOG_LEVEL":"info","FEATURE_FLAG":"disabled"}' \
  -e 'cluster_key_values={"cluster-b.kubeconfig":{"LOG_LEVEL":"debug"}}'
```

For a Secret, use `resource_kind=secret` and keep secret values out of shell
history and process listings. Prefer an Ansible Vault-protected extra-vars
file instead of putting plaintext secrets in `-e` arguments:

```yaml
# secret-values.yml — protect this file with ansible-vault
kc_dir: /secure/path/kc
resource_kind: secret
resource_name: app-credentials
namespace: demo
cluster_key_values:
  cluster-a.kubeconfig:
    username: app-a
    password: "{{ vault_cluster_a_password }}"
  cluster-b.kubeconfig:
    username: app-b
    password: "{{ vault_cluster_b_password }}"
cluster_resources:
  cluster-b.kubeconfig:
    resource_name: app-credentials-b
```

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e @secret-values.yml --ask-vault-pass
```

The playbook hides tasks that contain Secret values with `no_log`. Do not put
real kubeconfigs, tokens, or secret-vars files in the repository.

## Important Warnings

- The recipe executes the mutating `kubectl patch` command; run it against a
  non-production cluster first and verify the result in every cluster.
- It patches only the specified keys and does not delete unspecified keys.
- It fails before patching when no values are defined for a discovered
  kubeconfig.
- `ansible-playbook --check` is not a Kubernetes dry-run for this recipe. Use
  syntax checking and a disposable/non-production cluster for validation.
