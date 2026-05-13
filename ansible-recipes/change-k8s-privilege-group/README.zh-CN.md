# 修改 Kubernetes 特权组

英文版：`README.md`

这个 recipe 会把 Ansible 控制机上的 patch 版 `kubeadm` 复制到 Kubernetes control plane 节点上，然后用它重签指定证书、更新 kube-apiserver 静态 Pod manifest，并从指定的 ClusterRoleBinding 中移除 `system:masters`。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 确保一次执行至少包含一台 control plane 节点。
2. 校验 Ansible 控制机上的 patch 版 `kubeadm` 文件存在。
3. 为本次执行统一确定一个特权组值。
4. 把这个二进制复制到每个目标远程节点并设置为可执行。
5. 在每个目标节点上备份 `admin.conf`、存在时的 `/root/.kube/config`、kube-apiserver manifest，以及存在时的 `apiserver-kubelet-client` 证书文件。
6. 使用这个 patch 版 `kubeadm`，在每个目标节点上把 `admin.conf` 和 `apiserver-kubelet-client` 重新签发为同一个目标特权组对应的证书组织，并且可以选择额外传入用户指定的证书有效期。
7. 在每个节点上用新的 `admin.conf` 更新 `/root/.kube/config`。
8. 在每个节点的 kube-apiserver 静态 Pod manifest 中设置 `--system-privileged-group`，并更新 kube-apiserver 镜像。
9. 在每个节点上等待 `kubectl get --raw=/healthz` 再次成功。
10. 仅在第一个目标节点上备份当前 ClusterRoleBinding 的 JSON，并在存在时从 subjects 中移除 `system:masters`。

## 前置要求

- 每次执行至少选中一台目标主机
- 目标主机是 kubeadm 管理的 control plane 节点，并使用静态 kube-apiserver manifest
- Ansible 控制机上有一个支持 `certs renew ... --org=...` 的 patch 版 `kubeadm`
- 如果要自定义证书有效期，这个 patch 版 `kubeadm` 还必须支持对应的 renew 参数
- 目标主机上可以使用 `kubectl`
- Ansible 控制机可以通过 SSH 访问目标主机，并具备提权权限

## 必填变量

- `patched_kubeadm_src`: Ansible 控制机上的 patch 版 `kubeadm` 本地路径
- `kube_apiserver_image`: 要替换成的 kube-apiserver 镜像，例如 `repo.example/kube-apiserver:tag`

## 可选变量

- `target_hosts`: control plane 目标主机组，默认 `all`
- `system_privileged_group`: 要写入重签证书和 kube-apiserver manifest 的特权组，默认会生成类似 `system:admin-abc123def456` 的值
- `patched_kubeadm_dest`: patch 版 `kubeadm` 在远程节点上的路径，默认 `'/tmp/kubeadm-patched'`
- `kubeadm_cert_validity_period`: 传给两个 `certs renew` 命令的证书有效期，默认不启用
- `kubeadm_cert_validity_period_flag`: 和 `kubeadm_cert_validity_period` 一起使用的参数名，默认 `'--certificate-validity-period'`
- `kube_apiserver_manifest_path`: kube-apiserver manifest 路径，默认 `'/etc/kubernetes/manifests/kube-apiserver.yaml'`
- `admin_conf_path`: admin kubeconfig 路径，默认 `'/etc/kubernetes/admin.conf'`
- `root_kube_config_path`: root 用户 kubeconfig 路径，默认 `'/root/.kube/config'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `kubectl_command`: kubectl 命令路径或名称，默认 `'kubectl'`
- `clusterrolebinding_name`: 需要 patch 的 ClusterRoleBinding 名称，默认 `'cluster-admin'`
- `initial_restart_wait_seconds`: 修改 kube-apiserver manifest 后的固定等待秒数，默认 `30`
- `healthcheck_retries`: 修改后 API Server 健康检查的重试次数，默认 `20`
- `healthcheck_delay`: 健康检查每次重试之间的等待秒数，默认 `5`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/change-k8s-privilege-group/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

如果要指定固定的特权组，而不是自动生成随机值：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e system_privileged_group=system:admin-custom
```

如果要在重签证书时传入自定义的证书有效期：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_cert_validity_period=8760h
```

如果你的 patch 版 `kubeadm` 用的不是这个有效期参数名，也可以显式覆盖：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_cert_validity_period=8760h \
  -e kubeadm_cert_validity_period_flag=--validity-period
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

## 重要提醒

- 这是一个高风险 recipe，用错后可能直接移除你当前的 cluster-admin 访问能力。
- 这个 recipe 使用 `serial: 1`，会按 control plane 节点逐台滚动执行。
- ClusterRoleBinding patch 步骤只会在第一个目标节点上执行一次。
- 如果被 patch 的 ClusterRoleBinding 里只有 `system:masters` 这一个 subject，那么执行后该 binding 的 `subjects` 会变成空列表。
- 证书有效期这个能力只有在你的 patch 版 `kubeadm` 实际支持所选参数名时才能正常工作。
- 应先在非生产环境或可完整恢复的集群里验证。
- 运行前应确认生成的备份文件可用，不要把这份 recipe 当成唯一的回滚手段。
