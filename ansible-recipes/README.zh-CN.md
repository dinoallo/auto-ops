# Ansible Recipes

英文版：`README.md`

这个目录存放可直接执行的 Ansible recipe。每个 recipe 一般是一个独立目录，里面至少包含：

- `playbook.yml`: 可执行的 playbook
- `README.md`: recipe 的用途、变量和示例

## 环境配置

如果你不想把 Ansible 直接装到系统 Python 里，可以在当前目录里基于系统自带的 `python3` 创建一个本地虚拟环境：

```bash
cd ansible-recipes
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ansible
```

安装完成后，可以在虚拟环境里确认命令是否可用：

```bash
ansible --version
ansible-playbook --version
```

之后每次回到这个项目准备执行 recipe 前，先重新激活虚拟环境：

```bash
cd ansible-recipes
source .venv/bin/activate
```

如果要退出虚拟环境：

```bash
deactivate
```

## 使用前准备

执行 recipe 前，需要先准备：

1. 已安装 `ansible-playbook`
2. 一份可用的 inventory，例如 `inventory.ini`
3. 可以连接到目标主机的 SSH 配置和权限

一个最基本的执行形式是：

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

如果需要指定连接时使用的 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  path/to/playbook.yml \
  -e key=value
```

## Kubernetes Root CA 和 ServiceAccount Key 轮转

在仓库根目录按下面顺序执行，可以通过专用 playbook 轮转 Kubernetes
根 CA（`ca.crt` / `ca.key`）以及 ServiceAccount 签名密钥（`sa.key` /
`sa.pub`）。这是高影响操作：会更新控制面静态 Pod manifest，并重启控制面 Pod
和 kubelet。对共享集群执行前，先确认 inventory 并完成备份。

整次轮转应使用同一个 `RENEWAL_ID`。默认值是 `YYYYMMDDHH`；如果轮转跨小时执行，
或者同一小时执行多次轮转，请显式传入同一个值。

1. 生成并分发待激活的 Root CA、CA bundle 和 ServiceAccount key pair：

   ```bash
   RENEWAL_ID=$(date -u +%Y%m%d%H)

   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-ca/playbook.yml \
     -e renewal_id=${RENEWAL_ID}
   ```

2. 进入兼容期。API server 信任 CA bundle，并同时接受新旧
   ServiceAccount 公钥；controller manager 仍然使用旧 key 签发：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e restart_static_pods=true
   ```

3. 记录 ServiceAccount signer 切换时间，并把新 token 签发切到待激活的
   Root CA 和 ServiceAccount key：

   ```bash
   CUTOVER=$(date -u +%Y-%m-%dT%H:%M:%SZ)

   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e ca_cert_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
     -e ca_key_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.key \
     -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
     -e service_account_private_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
     -e restart_static_pods=true
   ```

4. 使用待激活 Root CA 续签控制面的 serving/client 证书以及系统 kubeconfig：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID}
   ```

5. 续签 kubelet client 证书，并在兼容期内让 kubelet 继续信任 CA bundle：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e kubelet_trust_mode=bundle
   ```

6. 重启或等待所有挂载 projected ServiceAccount token 的工作负载刷新 token，
   然后审计确认没有切换前签发的 token 仍在使用：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/audit-service-account-token-retirement/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e sa_key_cutover=${CUTOVER} \
     -e new_ca_file=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt
   ```

7. 将待激活 Root CA 和 ServiceAccount key pair 提升为当前生效文件，并把控制面
   manifest 收敛到只信任新 CA/key：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/activate-k8s-ca/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e sa_key_cutover=${CUTOVER} \
     -e new_ca_file=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
     -e restart_static_pods=true
   ```

8. 重写系统 kubeconfig，使其中只嵌入已提升的 Root CA：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml \
     -e restart_static_pods=true
   ```

9. 将 kubelet 的信任从 CA bundle 收敛到已提升的 Root CA：

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e kubelet_trust_mode=new \
     -e promote_kubelet_ca=true \
     -e renew_kubelet_client_cert=false
   ```

10. 验证控制面 kubeconfig 仍然可以访问 API server：

    ```bash
    ansible-playbook \
      -i inventory.ini \
      ansible-recipes/verify-system-kubeconfig/playbook.yml
    ```

## 当前可用的 Recipes

### activate-etcd-certs

路径：`ansible-recipes/activate-etcd-certs/playbook.yml`

更详细的说明见 `ansible-recipes/activate-etcd-certs/README.md`。

### configure-etcd-ca-bundle

路径：`ansible-recipes/configure-etcd-ca-bundle/playbook.yml`

更详细的说明见 `ansible-recipes/configure-etcd-ca-bundle/README.md`。

### configure-front-proxy-ca-bundle

路径：`ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml`

更详细的说明见 `ansible-recipes/configure-front-proxy-ca-bundle/README.md`。

### configure-front-proxy-client-certs

路径：`ansible-recipes/configure-front-proxy-client-certs/playbook.yml`

更详细的说明见 `ansible-recipes/configure-front-proxy-client-certs/README.md`。

### configure-k8s-ca-bundle

路径：`ansible-recipes/configure-k8s-ca-bundle/playbook.yml`

更详细的说明见 `ansible-recipes/configure-k8s-ca-bundle/README.md`。

### activate-k8s-ca

路径：`ansible-recipes/activate-k8s-ca/playbook.yml`

更详细的说明见 `ansible-recipes/activate-k8s-ca/README.md`。

### audit-service-account-token-retirement

路径：`ansible-recipes/audit-service-account-token-retirement/playbook.yml`

更详细的说明见 `ansible-recipes/audit-service-account-token-retirement/README.md`。

### archive-renewed-k8s-pki

路径：`ansible-recipes/archive-renewed-k8s-pki/playbook.yml`

更详细的说明见 `ansible-recipes/archive-renewed-k8s-pki/README.zh-CN.md`。

### configure-kubepods-io-limit

路径：`ansible-recipes/configure-kubepods-io-limit/playbook.yml`

更详细的说明见 `ansible-recipes/configure-kubepods-io-limit/README.md`。

### backup-k8s-data

路径：`ansible-recipes/backup-k8s-data/playbook.yml`

更详细的说明见 `ansible-recipes/backup-k8s-data/README.md`。

### backup-etcd-data

路径：`ansible-recipes/backup-etcd-data/playbook.yml`

更详细的说明见 `ansible-recipes/backup-etcd-data/README.md`。

### change-k8s-privilege-group

路径：`ansible-recipes/change-k8s-privilege-group/playbook.yml`

更详细的说明见 `ansible-recipes/change-k8s-privilege-group/README.md`。

### upgrade-os-packages

路径：`ansible-recipes/upgrade-os-packages/playbook.yml`

更详细的说明见 `ansible-recipes/upgrade-os-packages/README.md`。

### safely-copying-files

路径：`ansible-recipes/safely-copying-files/playbook.yml`

更详细的说明见 `ansible-recipes/safely-copying-files/README.md`。

### renew-etcd-ca

路径：`ansible-recipes/renew-etcd-ca/playbook.yml`

更详细的说明见 `ansible-recipes/renew-etcd-ca/README.md`。

### renew-k8s-ca

路径：`ansible-recipes/renew-k8s-ca/playbook.yml`

更详细的说明见 `ansible-recipes/renew-k8s-ca/README.md`。

### renew-k8s-certs

路径：`ansible-recipes/renew-k8s-certs/playbook.yml`

更详细的说明见 `ansible-recipes/renew-k8s-certs/README.md`。

### renew-k8s-kubelet-certs

路径：`ansible-recipes/renew-k8s-kubelet-certs/playbook.yml`

更详细的说明见 `ansible-recipes/renew-k8s-kubelet-certs/README.md`。

### converge-k8s-kubeconfig-ca

路径：`ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml`

更详细的说明见 `ansible-recipes/converge-k8s-kubeconfig-ca/README.md`。

### restart-k8s

路径：`ansible-recipes/restart-k8s/playbook.yml`

更详细的说明见 `ansible-recipes/restart-k8s/README.md`。

### verify-system-kubeconfig

路径：`ansible-recipes/verify-system-kubeconfig/playbook.yml`

更详细的说明见 `ansible-recipes/verify-system-kubeconfig/README.md`。

### renew-etcd-files

路径：`ansible-recipes/renew-etcd-files/playbook.yml`

更详细的说明见 `ansible-recipes/renew-etcd-files/README.md`。

### rotate-k8s-files

路径：`ansible-recipes/rotate-k8s-files/playbook.yml`

更详细的说明见 `ansible-recipes/rotate-k8s-files/README.md`。
