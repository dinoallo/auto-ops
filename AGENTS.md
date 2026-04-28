# Repository Guidelines

## Project Structure & Module Organization
This repository is a small collection of executable Ansible recipes.

- `ansible-recipes/README.md`: primary usage guide for all recipes
- `ansible-recipes/README.zh-CN.md`: Chinese translation of the main guide
- `ansible-recipes/<recipe-name>/playbook.yml`: executable playbook for one recipe
- `ansible-recipes/<recipe-name>/README.md`: English recipe documentation
- `ansible-recipes/<recipe-name>/README.zh-CN.md`: Chinese recipe documentation when provided

Keep each recipe self-contained in its own directory. Use kebab-case for recipe directory names, for example `safely-copying-files`.

## Build, Test, and Development Commands
Create a local Ansible environment from `ansible-recipes/`:

```bash
cd ansible-recipes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip ansible
```

Common validation and run commands:

```bash
ansible-playbook --syntax-check rotate-k8s-files/playbook.yml
ansible-playbook -i inventory.ini safely-copying-files/playbook.yml -e source_file=./files/app.conf -e dest_file=/etc/myapp/app.conf
ansible-playbook -i inventory.ini rotate-k8s-files/playbook.yml --check
```

Use `--check` only where the recipe behavior supports a dry run.

## Coding Style & Naming Conventions
Use 2-space YAML indentation and keep playbooks readable with short, imperative task names.

- Prefer fully qualified module names such as `ansible.builtin.copy`
- Use `true` and `false`, not `yes` and `no`
- Keep entrypoint filenames as `playbook.yml`
- Use Jinja defaults explicitly, for example `{{ target_hosts | default('all') }}`

Update English and Chinese READMEs together when behavior changes.

## Testing Guidelines
There is no dedicated automated test suite in this repository. Minimum validation for every change:

1. Run `ansible-playbook --syntax-check` on the changed playbook.
2. Execute against a non-production inventory.
3. Use `--check` when safe and supported.

Document any manual verification steps in the PR when a recipe is interactive or modifies cluster state.

## Commit & Pull Request Guidelines
Follow the existing commit style: short imperative subjects with an optional type/scope prefix, for example `chore(docs): add environment setup to README`.

PRs should include:

- what changed and why
- affected recipe paths
- example command used for validation
- any required variables, inventory assumptions, or SSH requirements

## Security & Configuration Tips
Do not commit inventory files with real hosts, private keys, tokens, or environment-specific secrets. Keep examples generic and redact sensitive paths, IPs, and credentials from documentation and PR text.
