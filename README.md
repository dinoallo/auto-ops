# auto-ops

Chinese version: `README.zh-CN.md`

`auto-ops` is a small collection of operational automation recipes, currently focused on executable Ansible playbooks.

The repository is organized around self-contained recipes under [`ansible-recipes/`](ansible-recipes/). Each recipe keeps its playbook and usage notes together so it can be reviewed and run independently.

## Repository Layout

- `ansible-recipes/README.md`: main usage guide for the recipe collection
- `ansible-recipes/README.zh-CN.md`: Chinese version of the main guide
- `ansible-recipes/<recipe-name>/playbook.yml`: executable playbook
- `ansible-recipes/<recipe-name>/README.md`: recipe-specific documentation when available
- `AGENTS.md`: contributor guidelines for repository structure, style, and validation

## Quick Start

Create a local Ansible environment:

```bash
cd ansible-recipes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip ansible
```

Run a playbook with an inventory:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf
```

Validate syntax before running:

```bash
ansible-playbook --syntax-check ansible-recipes/safely-copying-files/playbook.yml
```

## Available Recipes

### `safely-copying-files`

Copies a local file from the control node to remote hosts. If the destination exists and differs, the playbook prompts before replacing it. See [`ansible-recipes/safely-copying-files/README.md`](ansible-recipes/safely-copying-files/README.md) for variables and examples.

### `rotate-k8s-files`

Backs up Kubernetes control-plane files, regenerates CA and component certificates on master nodes, redistributes shared PKI material, and rejoins worker nodes. This playbook changes cluster identity material and should only be tested against a non-production or fully recoverable cluster first.

## Notes

- Keep inventories, SSH keys, tokens, and real host details out of the repository.
- Update English and Chinese documentation together when recipe behavior changes.
- Use `true` and `false` in YAML instead of `yes` and `no`.

For recipe authoring and contribution expectations, see [`AGENTS.md`](AGENTS.md).
