pipeline {
    agent any

    environment {
        REGISTRY = "registry.digitalocean.com/enterprise-ai-registry"
        IMAGE = "enterprise-ai"
        TAG = "local-${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                docker build -t $REGISTRY/$IMAGE:$TAG -f infrastructure/Dockerfile .
                docker tag $REGISTRY/$IMAGE:$TAG $REGISTRY/$IMAGE:latest
                """
            }
        }

        stage('Login to DO Registry') {
            steps {
                sh """
                doctl registry login --expiry-seconds 1200
                """
            }
        }

        stage('Push Image') {
            steps {
                sh """
                docker push $REGISTRY/$IMAGE:$TAG
                docker push $REGISTRY/$IMAGE:latest
                """
            }
        }

        stage('Done') {
            steps {
                echo "Pipeline completed successfully"
            }
        }
    }
}