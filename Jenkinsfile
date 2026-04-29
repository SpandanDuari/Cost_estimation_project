pipeline {
    agent any

    parameters {
        string(name: 'AWS_REGION', defaultValue: 'ap-south-1', description: 'AWS Region')
        choice(name: 'TERRAFORM_ACTION', choices: ['skip', 'plan', 'apply'], description: 'Terraform action: plan, apply, or skip')
        string(name: 'IMAGE_NAME', defaultValue: 'devopsproject', description: 'Docker image name')
        string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Docker image tag')
        string(name: 'ENABLE_ANSIBLE', defaultValue: 'true', description: 'Run Ansible post-deploy (true/false)')
    }

    environment {
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        AWS_REGION = "${params.AWS_REGION}"
        IMAGE_REPO_NAME = "${params.IMAGE_NAME}"
        IMAGE_TAG = "${params.IMAGE_TAG}"
        CLUSTER_NAME = "cost-estimation-cluster"
        TF_VAR_aws_region = "${AWS_REGION}"
        TF_VAR_environment = "production"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Terraform Plan/Apply') {
            when {
                expression { params.TERRAFORM_ACTION != 'skip' }
            }
            steps {
                dir('infra/terraform') {
                    bat '''
                        @echo on
                        setlocal enabledelayedexpansion
                        terraform init
                        terraform validate

                        rem Import resources if they already exist in AWS but not in state
                        terraform import aws_ecr_repository.app cost-estimation || echo ECR repository already in state or not found.
                        terraform import aws_iam_role.eks_cluster_role cost-estimation-eks-cluster-role || echo EKS cluster role already in state or not found.
                        terraform import aws_iam_role.eks_node_role cost-estimation-eks-node-role || echo EKS node role already in state or not found.
                        terraform import aws_eks_cluster.main cost-estimation-cluster || echo EKS cluster already in state or not found.
                        terraform import aws_eks_node_group.main cost-estimation-cluster:cost-estimation-node-group || echo EKS node group already in state or not found.

                        if /I "%TERRAFORM_ACTION%"=="plan" (
                            terraform plan -out=tfplan
                        ) else if /I "%TERRAFORM_ACTION%"=="apply" (
                            terraform apply -auto-approve -input=false
                        ) else (
                            echo Skipping Terraform execution.
                        )
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                    @echo on
                    setlocal enabledelayedexpansion
                    set "ECR_REGISTRY=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com"
                    set "REPOSITORY_URI=!ECR_REGISTRY!/%IMAGE_REPO_NAME%"
                    docker build -t !REPOSITORY_URI!:%IMAGE_TAG% .
                    docker tag !REPOSITORY_URI!:%IMAGE_TAG% !REPOSITORY_URI!:latest
                '''
            }
        }

        stage('Push to ECR') {
            steps {
                bat '''
                    @echo on
                    setlocal enabledelayedexpansion
                    set "ECR_REGISTRY=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com"
                    set "REPOSITORY_URI=!ECR_REGISTRY!/%IMAGE_REPO_NAME%"
                    aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin !ECR_REGISTRY!
                    docker push !REPOSITORY_URI!:%IMAGE_TAG%
                    docker push !REPOSITORY_URI!:latest
                    echo Image pushed: !REPOSITORY_URI!:%IMAGE_TAG%
                '''
            }
        }

        stage('Configure kubectl') {
            steps {
                bat '''
                    @echo on
                    aws eks update-kubeconfig --region %AWS_REGION% --name %CLUSTER_NAME%
                    kubectl cluster-info
                '''
            }
        }

        stage('Deploy to EKS') {
            steps {
                bat '''
                    @echo on
                    setlocal enabledelayedexpansion
                    set "ECR_REGISTRY=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com"
                    set "REPOSITORY_URI=!ECR_REGISTRY!/%IMAGE_REPO_NAME%"
                    kubectl apply -f k8s/deployment.yaml
                    kubectl apply -f k8s/service.yaml
                    kubectl rollout restart deployment/cost-estimation-app
                    kubectl rollout status deployment/cost-estimation-app --timeout=5m
                    echo Deployment Status:
                    kubectl get pods -l app=cost-estimation -o wide
                    kubectl get svc cost-estimation-service
                '''
            }
        }

        stage('Run Ansible Playbook') {
            when {
                expression { params.ENABLE_ANSIBLE == 'true' }
            }
            steps {
                bat '''
                    @echo on
                    if exist playbooks\\post-deploy.yml (
                        ansible-playbook --version >nul 2>&1
                        if errorlevel 1 (
                            echo ansible-playbook is not available on this Jenkins node. Skipping Ansible stage.
                        ) else (
                            for /f "usebackq delims=" %%A in (`aws eks describe-cluster --name %CLUSTER_NAME% --region %AWS_REGION% --query "cluster.endpoint" --output text`) do set "CLUSTER_ENDPOINT=%%A"
                            ansible-playbook playbooks\\post-deploy.yml -e "cluster_name=%CLUSTER_NAME%" -e "aws_region=%AWS_REGION%" -e "cluster_endpoint=%CLUSTER_ENDPOINT%" -i inventory\\aws_ec2.yml
                        )
                    ) else (
                        echo Warning: Ansible playbook not found at playbooks\\post-deploy.yml
                    )
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                bat '''
                    @echo on
                    setlocal enabledelayedexpansion
                    set "ECR_REGISTRY=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com"
                    set "REPOSITORY_URI=!ECR_REGISTRY!/%IMAGE_REPO_NAME%"
                    echo === Deployment Summary ===
                    echo Cluster: %CLUSTER_NAME%
                    echo Region: %AWS_REGION%
                    echo Image: !REPOSITORY_URI!:%IMAGE_TAG%
                    echo.
                    echo === Running Pods ===
                    kubectl get pods -A
                    echo.
                    echo === Services ===
                    kubectl get svc -A
                '''
            }
        }
    }

    post {
        success {
            echo "✓ Pipeline completed successfully!"
            echo "Application deployed successfully."
        }
        failure {
            echo "✗ Pipeline failed. Check logs above."
        }
        always {
            bat '''
                @echo on
                kubectl get all -A || echo Unable to list Kubernetes resources from this node.
            '''
        }
    }
}
