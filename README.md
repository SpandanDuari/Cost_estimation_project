# Cost_estimation_project

Simple Flask-based cost estimation web app (UI in `templates/`). This repository is prepared for containerized CI/CD deployments using Docker, Kubernetes, Jenkins, AWS, Ansible, and Terraform.

## Quick start (local)

Prerequisites: Python 3.8+, virtualenv

Windows (PowerShell):

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The app serves at `http://localhost:5000` by default.

## Local development with Docker Compose

Requires: Docker and Docker Compose

```bash
docker compose up --build
```

This starts the Flask app on http://localhost:5000.

To stop: `docker compose down`

## Container / CI notes

- `Dockerfile`: multi-stage build, containerizes the Flask app
- `docker-compose.yml`: local dev stack for the Flask app
- `k8s/`: Kubernetes manifests (Deployment, Service)
- `Jenkinsfile`: CI/CD pipeline for building, pushing, and deploying
- `requirements.txt`: Flask only

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed DevOps guidance, database migration notes, and examples.

---
**Next steps**: Set up Jenkins and EKS, then push the container image to ECR.
