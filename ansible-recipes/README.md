# Ansible Recipes

Chinese version: `README.zh-CN.md`

This directory contains executable Ansible recipes. Each recipe is usually a standalone directory with at least:

- `playbook.yml`: the executable playbook
- `README.md`: usage, variables, and examples

## Environment Setup

If you do not want to install Ansible globally, you can use the system `python3` to create a local virtual environment in this directory:

```bash
cd ansible-recipes
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ansible
```

Verify that the commands are available inside the virtual environment:

```bash
ansible --version
ansible-playbook --version
```

When you come back later, reactivate the environment before running any recipe:

```bash
cd ansible-recipes
source .venv/bin/activate
```

To leave the virtual environment:

```bash
deactivate
```

## Before You Start

Make sure you have:

1. `ansible-playbook` installed
2. A working inventory file such as `inventory.ini`
3. SSH access and the required permissions for the target hosts

The basic invocation pattern is:

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

To use a specific SSH key for the connection:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  path/to/playbook.yml \
  -e key=value
```

## Available Recipes

### safely-copying-files

Path: `ansible-recipes/safely-copying-files/playbook.yml`

For recipe-specific details, see `ansible-recipes/safely-copying-files/README.md`.

### rotate-k8s-files

Path: `ansible-recipes/rotate-k8s-files/playbook.yml`

For recipe-specific details, see `ansible-recipes/rotate-k8s-files/README.md`.
