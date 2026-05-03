pipeline {
    agent any

    environment {
        REGISTRY = "registry.digitalocean.com/enterprise-ai-registry"
        IMAGE = "enterprise-ai"
        TAG = "local-${BUILD_NUMBER}"
        NAMESPACE = "chatbot-ai"
        RELEASE = "chatbot-prod"
        KUBE_CONFIG = "/var/jenkins_home/.kube/config"
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

        stage('Update Snowflake Secret') {
            steps {
                sh """
                kubectl create secret generic snowflake-secret \
                  --from-literal=SNOWFLAKE_ACCOUNT=SWAMJMQ-PG18723 \
                  --from-literal=SNOWFLAKE_USER=KARAN4949 \
                  --from-literal=SNOWFLAKE_PASSWORD="@Thakur11223344" \
                  --from-literal=SNOWFLAKE_WAREHOUSE=COMPUTE_WH \
                  --from-literal=SNOWFLAKE_DATABASE=CHAT_APP \
                  --from-literal=SNOWFLAKE_SCHEMA=PUBLIC \
                  -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
                """
            }
        }

        stage('Deploy with Helm') {
            steps {
                sh """
                helm upgrade $RELEASE ./infrastructure/chatbot-chart \
                  --namespace $NAMESPACE \
                  -f ./infrastructure/chatbot-chart/values.yaml
                """
            }
        }

        stage('Verify Deployment') {
            steps {
                sh """
                echo "Waiting for pods to be ready..."
                sleep 10
                kubectl get pods -n $NAMESPACE
                echo "Checking pod status..."
                kubectl get pods -n $NAMESPACE -o wide
                """
            }
        }

        stage('Check Logs') {
            steps {
                sh """
                echo "=== API Pod Logs ==="
                kubectl logs -n $NAMESPACE -l app=api --tail=20 || echo "No API logs yet"
                echo ""
                echo "=== Worker Pod Logs ==="
                kubectl logs -n $NAMESPACE -l app=worker --tail=20 || echo "No Worker logs yet"
                """
            }
        }

        stage('Done') {
            steps {
                echo "✅ Pipeline completed successfully!"
                sh "kubectl get pods -n $NAMESPACE"
            }
        }
    }

    post {
        failure {
            echo "❌ Pipeline failed! Debugging info:"
            sh """
            echo "Pod Status:"
            kubectl get pods -n $NAMESPACE
            echo ""
            echo "Pod Descriptions:"
            kubectl describe pods -n $NAMESPACE || true
            """
        }
    }
}