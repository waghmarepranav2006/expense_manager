pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "expense-manager-app"
        CONTAINER_NAME = "expense-container"
        PORT = "8000"
    }
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'devops', url: 'https://github.com/waghmarepranav2006/expense_manager.git'
            }
        }
        
        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME} ."
            }
        }
        
        stage('Deploy to Container') {
            steps {
                // Stop and remove container if it exists from a previous run
                catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                    sh "docker stop ${CONTAINER_NAME}"
                    sh "docker rm ${CONTAINER_NAME}"
                }
                
                // Run the new container
                sh "docker run -d -p ${PORT}:8000 --name ${CONTAINER_NAME} ${IMAGE_NAME}"
            }
        }
    }
}
