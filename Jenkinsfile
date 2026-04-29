pipeline {
    agent any

    parameters {
        string(name: 'AWS_REGION', defaultValue: 'ap-south-1', description: 'AWS Region')
        string(name: 'TERRAFORM_ACTION', defaultValue: 'apply', description: 'Terraform action: plan, apply, or skip')
        string(name: 'IMAGE_NAME', defaultValue: 'devopsproject', description: 'Docker image name')
        string(name: 'IMAGE_TAG', defaultValue: '${BUILD_NUMBER}', description: 'Docker image tag')
        string(name: 'ENABLE_ANSIBLE', defaultValue: 'true', description: 'Run Ansible post-deploy (true/false)')
    }

    environment {
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        AWS_REGION = "${params.AWS_REGION}"
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_REPO_NAME = "${params.IMAGE_NAME}"
        IMAGE_TAG = "${params.IMAGE_TAG}"
        REPOSITORY_URI = "${ECR_REGISTRY}/${IMAGE_REPO_NAME}"
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
                    sh '''
                        terraform init
                        terraform validate
                        
                        if [ "${TERRAFORM_ACTION}" == "plan" ]; then
                            terraform plan -out=tfplan
                        elif [ "${TERRAFORM_ACTION}" == "apply" ]; then
                            terraform apply -auto-approve -input=false
                        fi
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${REPOSITORY_URI}:${IMAGE_TAG} .
                    docker tag ${REPOSITORY_URI}:${IMAGE_TAG} ${REPOSITORY_URI}:latest
                '''
            }
        }

        stage('Push to ECR') {
            steps {
                sh '''
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker push ${REPOSITORY_URI}:${IMAGE_TAG}
                    docker push ${REPOSITORY_URI}:latest
                    echo "Image pushed: ${REPOSITORY_URI}:${IMAGE_TAG}"
                '''
            }
        }

        stage('Configure kubectl') {
            steps {
                sh '''
                    aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}
                    kubectl cluster-info
                '''
            }
        }

        stage('Deploy to EKS') {
            steps {
                sh '''
                    # Update deployment manifest with new image
                    sed -i "s|YOUR_ECR_REGISTRY/cost-estimation:latest|${REPOSITORY_URI}:${IMAGE_TAG}|g" k8s/deployment.yaml
                    sed -i "s|image: .*|image: ${REPOSITORY_URI}:${IMAGE_TAG}|" k8s/deployment.yaml
                    
                    # Apply manifests
                    kubectl apply -f k8s/deployment.yaml
                    kubectl apply -f k8s/service.yaml
                    
                    # Wait for rollout
                    kubectl rollout status deployment/cost-estimation-app --timeout=5m
                    
                    # Show deployment status
                    echo "Deployment Status:"
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
                sh '''
                    # Get EKS cluster endpoint and nodes
                    CLUSTER_ENDPOINT=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --query 'cluster.endpoint' --output text)
                    
                    # Run Ansible playbook for post-deployment configuration
                    if [ -f "playbooks/post-deploy.yml" ]; then
                        echo "Running Ansible playbook..."
                        ansible-playbook playbooks/post-deploy.yml \
                            -e "cluster_name=${CLUSTER_NAME}" \
                            -e "aws_region=${AWS_REGION}" \
                            -e "cluster_endpoint=${CLUSTER_ENDPOINT}" \
                            -i inventory/aws_ec2.yml
                    else
                        echo "Warning: Ansible playbook not found at playbooks/post-deploy.yml"
                    fi
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    echo "=== Deployment Summary ==="
                    echo "Cluster: ${CLUSTER_NAME}"
                    echo "Region: ${AWS_REGION}"
                    echo "Image: ${REPOSITORY_URI}:${IMAGE_TAG}"
                    echo ""
                    echo "=== Running Pods ==="
                    kubectl get pods -A
                    echo ""
                    echo "=== Services ==="
                    kubectl get svc -A
                '''
            }
        }
    }

    post {
        success {
            echo "✓ Pipeline completed successfully!"
            echo "Application deployed at: ${REPOSITORY_URI}:${IMAGE_TAG}"
        }
        failure {
            echo "✗ Pipeline failed. Check logs above."
        }
        always {
            sh 'kubectl get all -A || true'
        }
    }
}
