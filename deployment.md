# Expense Manager Deployment Guide (AWS)

This guide provides step-by-step instructions for deploying the `expense_manager` application onto an AWS EC2 instance (Ubuntu), using S3 for static/media files, RDS for the database, and CloudWatch for logging.

## Architecture Overview

- **EC2 (Ubuntu)**: Hosts the application using Gunicorn (WSGI) and Nginx (Reverse Proxy).
- **RDS (PostgreSQL)**: Serves as the production relational database.
- **S3**: Stores and serves static files (CSS, JS, images) and user-uploaded media files.
- **CloudWatch**: Centralized application logging for monitoring and debugging.
- **IAM**: Provides secure access from the EC2 instance to S3 and CloudWatch without hardcoding AWS credentials.

---

## Step 1: AWS Infrastructure Provisioning

### 1.1 Create the RDS Instance
1. Go to the **RDS Console** -> Create Database.
2. Select **PostgreSQL**.
3. Under Templates, select **Free tier** or your desired level.
4. Set DB instance identifier (e.g., `expense-manager-db`).
5. Configure Master username (e.g., `db_user`) and Master password (e.g., `db_password`).
6. Set Public access to **No**.
7. Create a new VPC security group allowing port **5432** inbound from your EC2 security group (which we will create next).
8. Once created, note the **Endpoint endpoint URL**.

### 1.2 Create the S3 Bucket
1. Go to the **S3 Console** -> Create bucket.
2. Enter a unique bucket name (e.g., `expense-manager-assets-1234`).
3. Under **Object Ownership**, select **ACLs enabled** (or leave as bucket policies and configure accordingly) if required, but modern S3 prefers policies. Let's uncheck "Block all public access" if you want public read access to static/media files.
4. Acknowledge the warning and Create Bucket.

### 1.3 Create IAM Role
1. Go to the **IAM Console** -> Roles -> Create role.
2. Select **AWS service** -> **EC2**.
3. Attach the following policies:
   - `AmazonS3FullAccess` (Or restrict to the specific S3 bucket created above).
   - `CloudWatchLogsFullAccess`
4. Name the role (e.g., `ExpenseManagerEC2Role`) and save.

### 1.4 Launch the EC2 Instance
1. Go to the **EC2 Console** -> Launch instances.
2. Name: `expense-manager-web`.
3. Select **Ubuntu Server** (22.04 or 24.04 LTS).
4. Instance type: `t2.micro` (or larger depending on needs).
5. Storage: Configure 8GB-20GB gp3.
6. Under **Advanced details**, select the **IAM instance profile** (`ExpenseManagerEC2Role`) created above.
7. Configure Security Group:
   - Allow SSH (Port 22) from your IP.
   - Allow HTTP (Port 80) and HTTPS (Port 443) from Anywhere.
8. Launch the instance and note the public IP address.

---

## Step 2: Server Setup (EC2)

SSH into your freshly created EC2 instance:
```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 2.1 Install System Dependencies
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev libpq-dev postgresql-contrib nginx curl -y
```

### 2.2 Clone the Repository
```bash
# Clone directly if you have pushed it to GitHub
git clone https://github.com/your-username/expense_manager.git
cd expense_manager
```

### 2.3 Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.4 Configure Environment Variables
Copy the `.env.example` file to create a `.env` file.
```bash
cp .env.example .env
nano .env
```
Update all placeholders in `.env` with actual AWS credentials and the RDS connection string:
- `DATABASE_URL`: `postgres://db_user:db_password@<rds-endpoint>:5432/expense_manager_db` (or default postgres db name)
- `USE_S3=True`
- `AWS_STORAGE_BUCKET_NAME=<your-s3-bucket-name>`
- `USE_CLOUDWATCH=True`

*(Note: If you are using the IAM Role correctly, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` can optionally be omitted as the `boto3` library natively fetches credentials from the EC2 instance profile metadata!)*

### 2.5 Run Migrations and Collect Static Files
```bash
# Run Django Migrations (Creates tables in RDS)
python manage.py migrate

# Collect static files (Uploads them to your S3 Bucket)
python manage.py collectstatic --noinput

# Create a superuser
python manage.py createsuperuser
```

---

## Step 3: Application Server Configuration

### 3.1 Setup Gunicorn Systemd Service
Create a systemd service file for Gunicorn.
```bash
sudo nano /etc/systemd/system/gunicorn.service
```
Insert the following configuration:
```ini
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/expense_manager
ExecStart=/home/ubuntu/expense_manager/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          expense_manager.wsgi:application

[Install]
WantedBy=multi-user.target
```

Create a Gunicorn socket file:
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

Start and enable Gunicorn:
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl restart gunicorn
```

### 3.2 Setup Nginx
Configure Nginx as a reverse proxy passing HTTP traffic into the Gunicorn socket.
```bash
sudo nano /etc/nginx/sites-available/expense_manager
```
Insert the following configuration:
```nginx
server {
    listen 80;
    server_name <your-ec2-ip-or-domain>;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # We do not define /static/ because static files are served entirely from AWS S3

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```
Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/expense_manager /etc/nginx/sites-enabled
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## Customizing Logging
Currently, Django has been configured via `settings.py` so that if `USE_CLOUDWATCH=True` in `.env`, it uses the `watchtower` package to emit logs to the AWS CloudWatch log group named `expense_manager_production_logs`.
Ensure your EC2 IAM configuration includes CloudWatch execution permissions! By default, standard logs printed via `logger.info()` or Django errors will now reliably sit inside AWS CloudWatch.

## Success
You have successfully deployed Expense Manager onto a robust combination of AWS infrastructure:
1. **EC2** handles Django.
2. **RDS** manages PostgreSQL queries safely.
3. **S3** acts as your resilient static & media asset pipeline.
4. **CloudWatch** monitors activities remotely.
