# Infrastructure as Code (Terraform + Ansible)

## Directory structure

```
infra/
├── terraform/          # Terraform IaC for AWS resources
│   ├── provider.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── vpc.tf
│   ├── eks.tf
│   ├── ecr.tf
│   ├── terraform.tfvars.example
│   └── .terraform/     (auto-generated)
└── ansible/            # Ansible playbooks (optional)
    └── playbooks/
```

## Quick Start

### Using Terraform

```bash
cd terraform

# 1. Initialize
terraform init

# 2. Plan (review changes)
terraform plan

# 3. Apply (provision infrastructure)
terraform apply

# 4. Get outputs
terraform output
```

### Variables

All configurable in `terraform.tfvars`:

- `aws_region` — AWS region (default: us-east-1)
- `project_name` — Used for naming resources
- `environment` — dev/staging/production
- `eks_cluster_version` — Kubernetes version

### Outputs

After `terraform apply`, retrieve:

```bash
terraform output eks_cluster_name
terraform output rds_endpoint
terraform output configure_kubectl
```

## Using Ansible (Optional)

Ansible can configure post-deploy tasks:
- Database migrations
- ConfigMap/Secret management
- Application settings

See `ansible/playbooks/` for examples.

## Destroy Infrastructure

```bash
terraform destroy
```

**WARNING**: Deletes all AWS resources. Verify before confirming!

## Troubleshooting

### Terraform plan shows errors
```bash
terraform validate
terraform fmt -recursive
```

### Can't connect to EKS
```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name cost-estimation-cluster

# Verify nodes
kubectl get nodes
```

### RDS not accessible from pods
- ChEKS pods not starting
- Check Security Group rules
- Verify nodes are registered and healthy
## Cost Estimation

- **EKS**: ~$73/month
- **EC2** (2x t3.small): ~$30/month
- **RDS** (db.t3.micro): ~$15/month
- **Other** (ECR, data): ~$10-20/month

**Total**: ~$115-135
Use Spot instances to reduce EC2 costs by 70%.
