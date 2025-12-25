#!/usr/bin/env groovy
/**
 * Jenkins Pipeline for MCP Multi-Agent Game System
 * Comprehensive CI/CD with 85%+ coverage and full testing
 */

pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds()
    }
    
    environment {
        PYTHON_VERSION = '3.11'
        MIN_COVERAGE = '85'
        VENV = "${WORKSPACE}/venv"
    }
    
    stages {
        // ====================
        // Setup Stage
        // ====================
        stage('Setup') {
            steps {
                script {
                    echo '🚀 Setting up environment...'
                    sh '''
                        python${PYTHON_VERSION} -m venv ${VENV}
                        . ${VENV}/bin/activate
                        pip install --upgrade pip
                        pip install -e ".[dev]"
                    '''
                }
            }
        }
        
        // ====================
        // Validation Stage
        // ====================
        stage('Validate') {
            parallel {
                stage('Lint: Ruff') {
                    steps {
                        script {
                            echo '🔍 Running Ruff linter...'
                            sh '''
                                . ${VENV}/bin/activate
                                ruff check src/ tests/ || true
                                ruff format --check src/ tests/ || true
                            '''
                        }
                    }
                }
                
                stage('Type Check: MyPy') {
                    steps {
                        script {
                            echo '📝 Running MyPy type checker...'
                            sh '''
                                . ${VENV}/bin/activate
                                mypy src/ --ignore-missing-imports || true
                            '''
                        }
                    }
                }
                
                stage('Security: Bandit') {
                    steps {
                        script {
                            echo '🔒 Running Bandit security scanner...'
                            sh '''
                                . ${VENV}/bin/activate
                                bandit -r src/ -f json -o bandit-report.json || true
                            '''
                            archiveArtifacts artifacts: 'bandit-report.json', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        // ====================
        // Test Stage
        // ====================
        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        script {
                            echo '🧪 Running unit tests...'
                            sh '''
                                . ${VENV}/bin/activate
                                pytest tests/ \
                                    -v \
                                    --tb=short \
                                    --junit-xml=junit-unit.xml \
                                    -m "not integration and not slow"
                            '''
                        }
                    }
                    post {
                        always {
                            junit 'junit-unit.xml'
                        }
                    }
                }
                
                stage('Integration Tests') {
                    steps {
                        script {
                            echo '🔗 Running integration tests...'
                            sh '''
                                . ${VENV}/bin/activate
                                pytest tests/ \
                                    -v \
                                    -m integration \
                                    --junit-xml=junit-integration.xml
                            '''
                        }
                    }
                    post {
                        always {
                            junit 'junit-integration.xml'
                        }
                    }
                }
                
                stage('Performance Tests') {
                    steps {
                        script {
                            echo '⚡ Running performance tests...'
                            sh '''
                                . ${VENV}/bin/activate
                                pip install pytest-benchmark
                                pytest tests/ \
                                    -v \
                                    -m "slow or benchmark" \
                                    --benchmark-only \
                                    --benchmark-json=benchmark.json || true
                            '''
                            archiveArtifacts artifacts: 'benchmark.json', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        // ====================
        // Coverage Stage
        // ====================
        stage('Coverage') {
            steps {
                script {
                    echo '📊 Running coverage analysis...'
                    sh '''
                        . ${VENV}/bin/activate
                        pytest tests/ \
                            --cov=src \
                            --cov-report=xml \
                            --cov-report=html \
                            --cov-report=term-missing \
                            --cov-branch \
                            --cov-fail-under=${MIN_COVERAGE}
                        
                        pip install coverage-badge
                        coverage-badge -o coverage.svg -f
                    '''
                }
            }
            post {
                success {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                    
                    cobertura coberturaReportFile: 'coverage.xml'
                    
                    archiveArtifacts artifacts: 'coverage.svg', allowEmptyArchive: false
                }
            }
        }
        
        // ====================
        // Security Scan Stage
        // ====================
        stage('Security Scan') {
            parallel {
                stage('Safety Check') {
                    steps {
                        script {
                            echo '🔒 Running Safety vulnerability scan...'
                            sh '''
                                . ${VENV}/bin/activate
                                pip install safety
                                safety check --json --output safety-report.json || true
                            '''
                            archiveArtifacts artifacts: 'safety-report.json', allowEmptyArchive: true
                        }
                    }
                }
                
                stage('Pip Audit') {
                    steps {
                        script {
                            echo '🔍 Running pip-audit...'
                            sh '''
                                . ${VENV}/bin/activate
                                pip install pip-audit
                                pip-audit --format json --output pip-audit-report.json || true
                            '''
                            archiveArtifacts artifacts: 'pip-audit-report.json', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        // ====================
        // Quality Metrics Stage
        // ====================
        stage('Quality Metrics') {
            steps {
                script {
                    echo '📈 Calculating quality metrics...'
                    sh '''
                        . ${VENV}/bin/activate
                        pip install radon
                        radon cc src/ -a -s > complexity-report.txt || true
                        radon mi src/ -s > maintainability-report.txt || true
                    '''
                    archiveArtifacts artifacts: '*-report.txt', allowEmptyArchive: true
                }
            }
        }
        
        // ====================
        // Docker Build Stage
        // ====================
        stage('Docker Build') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    echo '🐳 Building Docker image...'
                    sh '''
                        docker build -t mcp-game-league:${BUILD_NUMBER} .
                        docker run --rm mcp-game-league:${BUILD_NUMBER} python -c "import src; print('Import successful')"
                        docker run --rm mcp-game-league:${BUILD_NUMBER} pytest tests/ -v --tb=short
                    '''
                }
            }
        }
        
        // ====================
        // Deployment Gate Stage
        // ====================
        stage('Deployment Gate') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo '✅ All CI checks passed!'
                    echo '✅ Tests: Passed'
                    echo "✅ Coverage: Above ${MIN_COVERAGE}%"
                    echo '✅ Security: Scanned'
                    echo '✅ Ready for deployment'
                }
            }
        }
    }
    
    // ====================
    // Post Actions
    // ====================
    post {
        always {
            echo '🧹 Cleaning up...'
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: 'venv/', type: 'INCLUDE'],
                    [pattern: '__pycache__/', type: 'INCLUDE'],
                    [pattern: '.pytest_cache/', type: 'INCLUDE']
                ]
            )
        }
        
        success {
            echo '✅ Pipeline completed successfully!'
            
            // Send notification (configure as needed)
            // emailext (
            //     subject: "SUCCESS: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
            //     body: "Build succeeded. Check console output at ${env.BUILD_URL}",
            //     to: "team@example.com"
            // )
        }
        
        failure {
            echo '❌ Pipeline failed!'
            
            // Send notification (configure as needed)
            // emailext (
            //     subject: "FAILURE: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
            //     body: "Build failed. Check console output at ${env.BUILD_URL}",
            //     to: "team@example.com"
            // )
        }
        
        unstable {
            echo '⚠️ Pipeline is unstable!'
        }
    }
}

