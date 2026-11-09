# Turnstone Cluster

[![CI](https://github.com/geerlingguy/turnstone-cluster/actions/workflows/ci.yml/badge.svg)](https://github.com/geerlingguy/turnstone-cluster/actions/workflows/ci.yml)

A local AI cluster configuration to run [Turnstone](https://github.com/turnstonelabs/turnstone) on computers I have in the studio.

| Host | Hardware | Role | Model | Runtime |
| --- | --- | --- | --- | --- |
| `ai-server.mmoffice.net` | Ryzen 9 9950X, 64 GB, 2x Radeon AI PRO R9700 (Ubuntu) | Turnstone + LLM | `qwen3.8-27b-r9700` | [Radiance](https://forum.level1techs.com/t/ultimate-2x-r9700-guide-for-qwen-3-8-27b-mxfp4-200t-s-c-1-500t-s-at-c-8/257789) (Docker) |

The playbook (`main.yml`) has four plays:

  1. **Security**: Applies [`geerlingguy.security`](https://github.com/geerlingguy/ansible-role-security) to every node (SSH keys only, no root login, fail2ban, automatic security updates), and [`geerlingguy.firewall`](https://github.com/geerlingguy/ansible-role-firewall) (iptables; replaces ufw and firewalld). SSH and mDNS are open to all; everything else only to `firewall_allowed_networks` (your LAN by default).
  2. **AI nodes**: Sets up an OpenAI-compatible LLM server on port 8000 on each node (installing Docker if needed). Per-node model settings live in `host_vars/`.
  3. **Turnstone node**: Checks out Turnstone, generates its secrets, maps its workspace to `~/turnstone-workspace`, and runs it with Docker Compose. Repos in `turnstone_workspace_repos` (by default, just the Markdown from my blog) are cloned into the workspace and pulled every 6 hours. The dashboard is served on port 443.
  4. **Monitoring**: Installs `node_exporter` (CPU, RAM, AMD GPUs) and `nvidia_gpu_exporter` (NVIDIA GPUs) on every node, and runs Prometheus (30 days of history) and Grafana on the Turnstone node. See [Monitoring](#monitoring).

## Setup

  1. Install Ansible on your computer: `pip3 install ansible`
  2. Install an OS on each node:
     - **R9700 server**: Ubuntu 26.04 LTS. In the BIOS, enable Above 4G Decoding and Resizable BAR, and put the GPUs in the two CPU-attached x16 slots (x8/x8), so the cards can use peer-to-peer transfers. The playbook installs Docker.
  3. Make sure you can SSH into each node with your SSH key, as a user with `sudo` privileges. The playbook disables password logins.
  4. Clone this repository and install the required roles and collections:

     ```
     git clone https://github.com/geerlingguy/turnstone-cluster.git
     cd turnstone-cluster
     ansible-galaxy install -r requirements.yml
     ```

  5. Copy the example inventory and config files, then edit them to match your setup (if you reach the cluster over a VPN, add its subnet to `firewall_allowed_networks`):

     ```
     cp example.hosts.ini hosts.ini
     cp example.config.yml config.yml
     ```

  6. (Optional) Adjust the models each node runs in `host_vars/`.
  7. Make sure Ansible can reach every node: `ansible all -m ping`
  8. Run the playbook (`-K` prompts for your sudo password):

     ```
     ansible-playbook main.yml -K
     ```

     First runs take a long time: models are downloaded before the LLM servers start. To set up just one node, use `--limit`, e.g. `--limit ai-server.mmoffice.net`.

  9. Open the Turnstone dashboard at `https://ai-server.mmoffice.net` and log in. Then, under **System → Models**, add the model using the alias, base URL, and concurrency printed at the end of the playbook run, and make it the default (Settings → Model → `default_alias`). Leave the roles empty so they use the default.

     Turn on the **Tools**, **Vision**, **Server-side reasoning parser**, and **Reasoning-effort control** capabilities as appropriate for each model.

  10. (Optional) Add integrations in the dashboard: the GitHub MCP server (**Extensions → MCP Servers**, `https://api.githubcopilot.com/mcp/readonly` with a read-only PAT), and tool policies under **Governance → Policies** (e.g. allow `web_*`).

To upgrade Turnstone, change `turnstone_version` in `config.yml` (back up the database first with `docker exec turnstone-postgres-1 sh -c 'pg_dumpall -U "$POSTGRES_USER"' > turnstone-backup-$(date +%F).sql`) and run the playbook again.

## Monitoring

Open `http://<turnstone-node-ip>:3000` (the playbook prints the URL) for the **Turnstone Cluster** dashboard. It's read-only and needs no login. It shows cluster-wide totals at the top, a **Turnstone** row (workstreams, tool calls, judge calls and latency, and token usage across every model, including cloud models like Claude), then one row per node with CPU, RAM, GPU utilization and power, decode/prefill tokens/s, running/waiting requests, and KV cache usage.

Prometheus recording rules (`files/monitoring/rules.yml`) put vLLM and Radiance metrics under the same names (`llm:*`, `gpu:*`, `node:*`), so every node's row looks the same regardless of runtime. Each node's `llm_metrics_type` (`vllm` or `radiance`) tells Prometheus how to scrape it. Radiance's `/stats` JSON is converted by `json_exporter`.

Prometheus itself listens only on `127.0.0.1:9090` on the Turnstone node. To edit dashboards in Grafana, log in as `admin` (set `grafana_admin_password` in `config.yml`). The provisioned dashboard is read-only, so save edits as a copy, or edit `files/monitoring/grafana/generate_dashboard.py` and regenerate `turnstone-cluster.json` with it.

## License

GPLv3 or later. See [LICENSE](LICENSE).

## AI Disclaimer

Much of the code in this project was initially generated by, or modified by, AI tools. Part of the reason for this project's existence is to see how much of my infrastructure automation process I can manage with the assistance of LLMs.

## Author

[Jeff Geerling](https://www.jeffgeerling.com).
