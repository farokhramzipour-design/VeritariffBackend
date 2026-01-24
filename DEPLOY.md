
# Deployment Guide for Veritariff Backend

This guide assumes you have a Linux server (Ubuntu/Debian) with Docker and Docker Compose installed.

## Prerequisites on Server

1.  **Update System**:
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

2.  **Install Docker**:
    ```bash
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

3.  **Install Docker Compose**:
    ```bash
    sudo apt install -y docker-compose
    ```

## Deployment Steps

1.  **Clone the Repository**:
    SSH into your server and clone your project.
    ```bash
    git clone <your-repo-url>
    cd VeritariffBackend
    ```

2.  **Configure Environment Variables**:
    Create a `.env` file in the root directory.
    ```bash
    nano .env
    ```
    Paste your production configuration:
    ```ini
    PROJECT_NAME="Veritariff Backend"
    
    # Database (These match the docker-compose db service)
    POSTGRES_SERVER=db
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=secure_production_password
    POSTGRES_DB=veritariff
    
    # Google Auth
    GOOGLE_CLIENT_ID=your-google-client-id
    GOOGLE_CLIENT_SECRET=your-google-client-secret
    GOOGLE_REDIRECT_URI=https://api.veritariffai.co/api/v1/login/google/callback
    
    # Domain
    DOMAIN=api.veritariffai.co
    ```

3.  **Build and Run**:
    ```bash
    sudo docker-compose up -d --build
    ```
    This will start the backend and the database in the background.

4.  **Verify Status**:
    ```bash
    sudo docker-compose ps
    ```
    You should see both `web` and `db` services running.

## Setting up Nginx with SSL (HTTPS)

To serve your API securely at `https://api.veritariffai.co`, use Nginx and Certbot.

1.  **Install Nginx**:
    ```bash
    sudo apt install -y nginx
    ```

2.  **Configure Nginx**:
    Create a config file:
    ```bash
    sudo nano /etc/nginx/sites-available/veritariff
    ```
    Paste the following (replace `api.veritariffai.co` with your actual domain):
    ```nginx
    server {
        server_name api.veritariffai.co;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

3.  **Enable Site**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/veritariff /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    ```

4.  **Install Certbot (SSL)**:
    ```bash
    sudo apt install -y certbot python3-certbot-nginx
    ```

5.  **Obtain SSL Certificate**:
    ```bash
    sudo certbot --nginx -d api.veritariffai.co
    ```
    Follow the prompts. Certbot will automatically update your Nginx config to use HTTPS.

## Updating the Application

When you have new code changes:

1.  **Pull changes**:
    ```bash
    git pull origin main
    ```

2.  **Rebuild and Restart**:
    ```bash
    sudo docker-compose up -d --build
    ```
