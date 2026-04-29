# Terraform Setup

This folder contains the AWS infrastructure for the stateless Flask calculator app.

## Included

- ECR repository
- EKS cluster
- VPC, subnets, and security groups

## Not included

- RDS
- Database secrets
- Application-side persistent storage

## Commands

```bash
cd terraform
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```
