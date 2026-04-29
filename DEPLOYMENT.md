# Deployment Guide

This project is now a stateless Flask cost calculator. It does not use login, reports, SQLite, RDS, or file storage.

## What you deploy

- Flask app in a Docker container
- Docker image pushed to Amazon ECR
- Kubernetes deployment on EKS
- Jenkins pipeline to build, push, and deploy

## Local run

```powershell
cd "C:\Users\SAMAMITA\OneDrive\Documents\GitHub\Cost_estimation_project"
docker compose up --build
```

Open `http://localhost:5000`.

## AWS flow

1. Create ECR repository for the image.
2. Create or reuse an EKS cluster.
3. Set up Jenkins with AWS access.
4. Build the image in Jenkins.
5. Push the image to ECR.
6. Update the Kubernetes deployment image.
7. Apply the manifests to EKS.

## Jenkins pipeline

The [Jenkinsfile](Jenkinsfile) now does three things:

- build the Docker image
- push it to ECR
- deploy `k8s/deployment.yaml` and `k8s/service.yaml` to EKS

## Kubernetes manifests

- [k8s/deployment.yaml](k8s/deployment.yaml): runs the app container
- [k8s/service.yaml](k8s/service.yaml): exposes the app with a LoadBalancer

No ConfigMap or Secret is needed for this version.

## Terraform

If you still want infrastructure as code, keep only the AWS resources you need for the demo:

- ECR
- EKS
- VPC and security groups

You do not need RDS for this version.

## Notes

- Keep the image tag updated in `k8s/deployment.yaml`.
- Store AWS credentials securely in Jenkins credentials or an IAM role.
- Do not add database or auth services back unless you want persistence again.
