# Upgrading Ubuntu Packages

Chinese version: `README.zh-CN.md`

This recipe upgrades installed operating system packages on Ubuntu hosts with `apt`. It currently supports Ubuntu only and runs one host at a time to reduce the blast radius of package changes and optional reboots.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Validates that the target hosts are Ubuntu systems that use `apt`.
2. Refreshes the local apt package index.
3. Upgrades installed packages with a regular upgrade by default.
4. Optionally runs `autoremove` and `autoclean`.
5. Checks whether `/var/run/reboot-required` exists after the upgrade.
6. Optionally reboots the host when a reboot is required.

## Requirements

- Ubuntu target hosts
- SSH access to the target hosts
- Privilege escalation rights for package operations and optional reboot
- Working access from the target hosts to their configured Ubuntu package repositories

No additional variables are required for a basic run.

## Optional Variables

- `target_hosts`: target host group, defaults to `all`
- `upgrade_mode`: apt upgrade mode, allowed values are `yes` and `dist`, defaults to `yes`
- `apt_cache_valid_time`: seconds before Ansible refreshes apt metadata again, defaults to `3600`
- `apt_lock_timeout`: seconds to wait for the apt/dpkg lock, defaults to `300`
- `autoremove_packages`: whether to run `apt autoremove`, defaults to `false`
- `autoclean_packages`: whether to run `apt autoclean`, defaults to `false`
- `reboot_if_required`: whether to reboot when `/var/run/reboot-required` exists, defaults to `false`
- `reboot_timeout`: seconds to wait for the host to come back after a reboot, defaults to `1800`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/upgrade-os-packages/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu
```

To use `dist-upgrade` semantics and remove packages that are no longer required:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu \
  -e upgrade_mode=dist \
  -e autoremove_packages=true
```

To reboot hosts automatically when the upgrade requires it:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu \
  -e reboot_if_required=true
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu
```

## Important Warnings

- This recipe currently supports Ubuntu hosts only. It fails fast on other Linux distributions.
- The playbook runs with `serial: 1`, so hosts are upgraded one at a time by design.
- `upgrade_mode=dist` can install or remove packages to satisfy dependencies. Use it intentionally.
- By default the recipe does not reboot the host even when the upgrade leaves `/var/run/reboot-required` behind.
