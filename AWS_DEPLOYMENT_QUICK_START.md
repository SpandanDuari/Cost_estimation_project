# Quick Start: AWS Deployment with Jenkins, Terraform, and Ansible

This project now includes a complete production-ready DevOps pipeline for deploying a Flask cost estimator app to AWS EKS.

## What You Get

✅ **Terraform** — Provisions EKS, VPC, security groups, NAT gateways, and IAM roles  
✅ **Jenkins Pipeline** — Automates: Git checkout → Docker build → ECR push → EKS deploy → Ansible config  
✅ **Ansible Playbook** — Installs Prometheus monitoring, Grafana, NGINX ingress controller  
✅ **GitHub Webhook** — Auto-triggers Jenkins on code push  
✅ **Helm Integration** — Deploys cloud-native tools automatically  

## Quick Start (5 minutes)

### 1. Setup AWS Credentials

```bash
aws configure
# Enter: Access Key, Secret Key, Region (ap-south-1), Output format (json)
```

### 2. Start Jenkins

```bash
docker run -d -p 8080:8080 -p 50000:50000 \
  -v jenkins-data:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.aws:/root/.aws \
  jenkins/jenkins:lts

# Get password:
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 3. Complete Setup

Follow the detailed guide: [JENKINS_TERRAFORM_ANSIBLE_SETUP.md](JENKINS_TERRAFORM_ANSIBLE_SETUP.md)

## Key Files

| File | Purpose |
|------|---------|
| `Jenkinsfile` | Pipeline orchestration (build → push → deploy) |
| `infra/terraform/*.tf` | EKS infrastructure provisioning |
| `playbooks/post-deploy.yml` | Monitoring & ingress controller setup |
| `inventory/aws_ec2.yml` | Dynamic AWS resource discovery |
| `JENKINS_TERRAFORM_ANSIBLE_SETUP.md` | Complete step-by-step guide |

## Parameter Reference

Jenkins pipeline accepts parameters:
- `AWS_REGION` — Default: `ap-south-1`
- `TERRAFORM_ACTION` — `plan`, `apply`, or `skip`
- `IMAGE_TAG` — Docker image tag (default: build number)
- `ENABLE_ANSIBLE` — Run post-deploy config (true/false)

## Estimated Cost

- EKS Cluster: ~$20/month
- EC2 nodes: ~$30/month  
- Load Balancer: ~$15/month
- Monitoring storage: ~$10/month
- **Total: ~$75-90/month** (ap-south-1 region)

## Architecture

```
Code Push (GitHub)
    ↓
Webhook Trigger
    ↓
Jenkins Pipeline
├── Terraform: Provision EKS
├── Docker: Build image
├── ECR: Push to registry
├── kubectl: Deploy app
└── Ansible: Install monitoring
    ↓
EKS Cluster (Production)
├── 2x t3.small nodes
├── Cost Estimator App
├── Prometheus + Grafana
└── NGINX Ingress Controller
```

## Next Steps

1. **Read the guide**: [JENKINS_TERRAFORM_ANSIBLE_SETUP.md](JENKINS_TERRAFORM_ANSIBLE_SETUP.md)
2. **Configure AWS credentials**: Run `aws configure`
3. **Start Jenkins**: Use Docker command above
4. **Add credentials to Jenkins**: AWS Access Key + Secret Key
5. **Create pipeline job**: Point to this repo's Jenkinsfile
6. **Trigger build**: Click "Build with Parameters"
7. **Monitor**: Watch console output as pipeline executes

Get started now! 🚀
