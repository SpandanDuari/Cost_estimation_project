# Complete AWS Deployment Guide

This guide walks you through the complete DevOps setup: Terraform → Jenkins → Ansible for real AWS EKS deployment.

## Architecture

```
GitHub (code push)
    ↓
Jenkins Pipeline (triggered by webhook)
    ├── Checkout code
    ├── Terraform: Provision EKS cluster & VPC
    ├── Docker: Build image
    ├── ECR: Push image
    ├── kubectl: Deploy to EKS
    └── Ansible: Post-deployment config (monitoring, ingress)
    ↓
EKS Cluster (Running)
```

---

## Prerequisites

- AWS Account with AWS CLI v2 configured
- Jenkins server (local Docker or EC2)
- Terraform installed
- kubectl installed
- Ansible installed
- Docker installed
- GitHub repository with webhook access

---

## Step 1: Setup AWS Credentials

Ensure AWS CLI is configured with your credentials:

```bash
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (ap-south-1), Output format (json)

# Verify:
aws sts get-caller-identity
# Should show your Account ID, User ARN, and Arn field
```

**Get your Account ID** (you'll need this for Jenkins):
```bash
aws sts get-caller-identity --query Account --output text
# Output: 974387521388 (your 12-digit account ID)
```

---

## Step 2: Create Terraform Configuration

### 2a. Copy and Update terraform.tfvars

From the `infra/terraform/` directory:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region          = "ap-south-1"
project_name        = "cost-estimation"
environment         = "production"
eks_cluster_version = "1.28"
```

### 2b. Validate Terraform

```bash
terraform init
terraform validate
terraform plan -out=tfplan
```

If successful, you'll see the resources to be created (VPC, subnets, security groups, IAM roles, EKS cluster, node group).

---

## Step 3: Install and Configure Jenkins

### Option A: Local Jenkins in Docker (Quick Dev Setup)

```bash
# Create persistent Jenkins data directory
mkdir -p ./jenkins-data

# Run Jenkins container
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v ./jenkins-data:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.aws:/root/.aws \
  jenkins/jenkins:lts

# Get initial admin password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Option B: Jenkins on AWS EC2

```bash
# Launch t2.medium EC2 instance (Ubuntu 22.04)
# SSH into instance, then:
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk docker.io git ansible terraform

# Install Jenkins
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
sudo sh -c 'echo deb https://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update
sudo apt-get install -y jenkins

# Start Jenkins
sudo systemctl start jenkins
sudo systemctl enable jenkins

# Get password
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

### Step 3b: Access Jenkins

Open your browser:
- Local Docker: `http://localhost:8080`
- EC2: `http://<EC2_PUBLIC_IP>:8080`

1. Paste the initial admin password
2. Click "Install suggested plugins"
3. Create admin user (e.g., `admin` / `devops123`)
4. Click "Save and Continue"

### Step 3c: Install Jenkins Plugins

Go to **Manage Jenkins** → **Manage Plugins** → **Available** and install:
- Git
- Docker
- AWS Credentials
- CloudBees AWS Credentials
- Kubernetes
- Ansible

Then restart Jenkins.

### Step 3d: Add AWS Credentials to Jenkins

1. Go to **Manage Jenkins** → **Manage Credentials** → **System** → **Global credentials**
2. Click **Add Credentials**
   - **Kind**: AWS Credentials
   - **Scope**: Global
   - **Access Key ID**: `AKIA...` (your IAM access key)
   - **Secret Access Key**: `<your-secret-key>`
   - **ID**: `aws-credentials` (important — used in Jenkinsfile)
3. Click **Create**

3e. Add AWS Account ID:

1. Go to **Manage Jenkins** → **Manage Credentials** → **System** → **Global credentials**
2. Click **Add Credentials**
   - **Kind**: Secret text
   - **Secret**: `974387521388` (your 12-digit account ID)
   - **ID**: `aws-account-id` (important — must match Jenkinsfile)
3. Click **Create**

---

## Step 4: Create Jenkins Pipeline Job

### 4a. Create New Job

1. Click **New Item**
2. Enter **Job name**: `cost-estimation-deploy`
3. Select **Pipeline**
4. Click **OK**

### 4b. Configure Git Repository

Under **Pipeline**:
- **Definition**: Pipeline script from SCM
- **SCM**: Git
- **Repository URL**: `https://github.com/<YOUR_USERNAME>/Cost_estimation_project.git`
- **Branch Specifier**: `*/main` (or your branch)
- **Script Path**: `Jenkinsfile`

### 4c. Save

Click **Save**

### 4d. Run Pipeline Manually

1. Click **Build with Parameters**
2. Set parameters:
   - **AWS_REGION**: `ap-south-1`
   - **TERRAFORM_ACTION**: `apply` (first run to provision EKS)
   - **IMAGE_NAME**: `devopsproject`
   - **IMAGE_TAG**: `1.0.0` (or use `${BUILD_NUMBER}`)
   - **ENABLE_ANSIBLE**: `true`
3. Click **Build**

Monitor the console output. The pipeline will:
1. **Terraform Apply** → Provision EKS, VPC, security groups (~8-10 minutes)
2. **Build Image** → Docker build
3. **Push to ECR** → Upload image to ECR
4. **Deploy to EKS** → Update kubeconfig + kubectl apply
5. **Ansible** → Install monitoring & ingress controller

---

## Step 5: Setup GitHub Webhook (Auto-Trigger)

### 5a. Enable Webhooks in Jenkins

1. Go to **Manage Jenkins** → **Configure Global Security**
2. Under **CSRF Protection**, ensure it's enabled
3. Go to your Jenkins job → **Configure**
4. Under **Build Triggers**, check **GitHub hook trigger for GITScm polling**
5. Click **Save**

### 5b. Configure GitHub Webhook

1. Go to your GitHub repository
2. **Settings** → **Webhooks** → **Add webhook**
3. **Payload URL**: `http://<JENKINS_PUBLIC_IP>:8080/github-webhook/`
4. **Content type**: `application/json`
5. **Events**: Just the push event
6. Click **Add webhook**

Now every `git push` to GitHub will trigger the Jenkins pipeline.

---

## Step 6: Verify Deployment

Once the pipeline completes:

```bash
# Check EKS cluster
aws eks describe-cluster --name cost-estimation-cluster --region ap-south-1

# Get kubeconfig
aws eks update-kubeconfig --region ap-south-1 --name cost-estimation-cluster

# Check pods
kubectl get pods -A

# Check services
kubectl get svc -A

# Port-forward to app
kubectl port-forward svc/cost-estimation-service 8090:80
# Open: http://localhost:8090
```

---

## Step 7: Monitor with Ansible-Installed Components

### Access Prometheus

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Open: http://localhost:9090
```

### Access Grafana

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Open: http://localhost:3000
# Default login: admin / prom-operator
```

### Check NGINX Ingress

```bash
kubectl get svc -n ingress-nginx
# Note the external LoadBalancer IP
```

---

## Troubleshooting

### Terraform State Lock Issues
```bash
cd infra/terraform
terraform force-unlock <LOCK_ID>
```

### EKS Cluster Not Available
```bash
aws eks describe-cluster --name cost-estimation-cluster --region ap-south-1 --query 'cluster.status'
# Wait for status to be ACTIVE
```

### Jenkins No Docker Access
```bash
# Run Jenkins container with docker socket:
docker run -v /var/run/docker.sock:/var/run/docker.sock ...

# Or add Jenkins user to docker group:
sudo usermod -aG docker jenkins
```

### Ansible Playbook Not Found
Create the `playbooks/` and `inventory/` directories in your repo root (already done in this setup).

---

## Next Steps

1. **Create staging environment** — Create separate Terraform workspace for `staging`
2. **Add automated tests** — Add test stage in Jenkinsfile
3. **Setup monitoring alerts** — Configure Prometheus AlertManager
4. **Add auto-scaling policies** — Configure HPA and cluster autoscaler
5. **Implement GitOps** — Use ArgoCD for declarative deployments

---

## Cost Estimation (AWS ap-south-1)

- **EKS Cluster**: ~$20/month
- **2x t3.small EC2 nodes**: ~$30/month
- **Load Balancer**: ~$15/month
- **Data transfer**: ~$5-10/month
- **Monitor storage (Prometheus)**: ~$10/month

**Total**: ~$80-95/month

---

## Quick Reference Commands

```bash
# Terraform
cd infra/terraform
terraform init
terraform plan
terraform apply
terraform destroy  # WARNING: Destroys all resources

# Jenkins
# Start: docker container start jenkins
# Stop: docker container stop jenkins
# Logs: docker logs jenkins

# Kubernetes
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
kubectl get svc -A
kubectl describe node <NODE_NAME>
kubectl logs <POD_NAME> -n <NAMESPACE>

# ECR
aws ecr describe-repositories --region ap-south-1
aws ecr list-images --repository-name devopsproject --region ap-south-1

# EKS
aws eks list-clusters --region ap-south-1
aws eks describe-cluster --name cost-estimation-cluster --region ap-south-1
```

---

**You're now ready for real AWS deployment!** 🚀
