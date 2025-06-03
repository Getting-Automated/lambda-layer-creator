# AWS Lambda Layer Creator

This Python script allows you to create an AWS Lambda layer from a specified pip library. The script can optionally upload the created Lambda layer to AWS.

## Features

- Install one or more specified pip libraries **or** everything listed in a `requirements.txt` file and package them into a single AWS Lambda layer.
- Optionally upload the created layer to AWS Lambda.
- Specify the runtime (default `python3.10`) and AWS region for the layer.
- Fully command-line driven with interactive fall-back when no libraries and no requirements file are provided.
- Clean up temporary build artifacts automatically.

## Prerequisites

- Python 3.8 or later
- AWS CLI configured with the necessary permissions to create and upload Lambda layers
- `boto3` and `argparse` Python libraries

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/aws-lambda-layer-creator.git
   cd aws-lambda-layer-creator
   ```

2. **Install the required Python libraries**:
   ```bash
   pip install boto3 argparse
   ```

3. **Configure AWS CLI** (if not already configured):
   ```bash
   aws configure
   ```

## Usage

### Command-Line Arguments

- `--libraries`: Space-separated list of pip libraries to include in the layer (optional if `--requirements-file` is provided).
- `--requirements-file`: Path to a `requirements.txt` file containing the dependencies to package (optional if `--libraries` is provided).
- `--layer-name`: The name of the Lambda layer (required).
- `--runtime`: The runtime for the Lambda layer (default is `python3.10`).
- `--region`: The AWS region to create the Lambda layer in (default is `us-east-1`).
- `--no-upload`: If specified, the Lambda layer will **not** be uploaded to AWS.

### Examples

#### Create and Upload a Layer with Multiple Libraries

```bash
python create_lambda_layer.py \
  --libraries numpy pandas scipy \
  --layer-name data-science-layer \
  --runtime python3.10
```

#### Create and Upload a Layer from a requirements.txt File

```bash
python create_lambda_layer.py \
  --requirements-file ./requirements.txt \
  --layer-name shared-deps-layer
```

#### Build Locally Without Uploading

```bash
python create_lambda_layer.py --libraries pillow --layer-name image-utils --no-upload
```

## Script Details

### `create_lambda_layer` Function

The main function that handles the creation of the Lambda layer:

- **Parameters**:
  - `libraries` (List[str] | None): A list of pip libraries to include (optional).
  - `layer_name` (str): The name of the Lambda layer.
  - `runtime` (str): The runtime for the Lambda layer (default is `python3.10`).
  - `region_name` (str): The AWS region to create the Lambda layer in (default is `us-east-1`).
  - `upload` (bool): Whether to upload the layer to AWS (default is `True`).
  - `requirements_file` (str | None): Path to a `requirements.txt` file whose contents should be installed (optional).

- **Workflow**:
  1. Creates a temporary build directory.
  2. Installs the requested libraries and/or requirements file into the directory.
  3. Packages the directory into a zip file compatible with AWS Lambda layers.
  4. Optionally uploads the zip file to AWS Lambda.

### `main` Function

The function that sets up command-line argument parsing and prompts the user for input if necessary.

## CI/CD with Jenkins

Below is an example Declarative Pipeline that builds the layer inside Jenkins. It demonstrates how to parameterize the job so each run can supply either a list of libraries **or** a `requirements.txt` file.

```groovy
pipeline {
    agent any

    /* -------- Job Parameters -------- */
    parameters {
        string(name: 'LAYER_NAME',        defaultValue: 'my-shared-layer', description: 'Name of the Lambda layer to create/update')
        choice(name: 'INSTALL_MODE', choices: ['LIBRARIES', 'REQUIREMENTS_FILE'], description: 'Choose how dependencies are supplied')
        string(name: 'LIBRARIES', defaultValue: 'numpy pandas', description: 'Space-separated list of libraries (used when INSTALL_MODE=LIBRARIES)')
        file(name: 'REQUIREMENTS_FILE', description: 'Upload requirements.txt (used when INSTALL_MODE=REQUIREMENTS_FILE)')
        booleanParam(name: 'UPLOAD', defaultValue: true, description: 'Upload the finished layer to AWS')
        string(name: 'AWS_REGION',      defaultValue: 'us-east-1', description: 'AWS Region for the layer')
        string(name: 'PYTHON_RUNTIME',  defaultValue: 'python3.10', description: 'Lambda runtime version')
        string(name: 'ASSUME_ROLE_ARN', defaultValue: '', description: 'ARN of the IAM role to assume for the build')
    }

    /* -------- Environment -------- */
    environment {
        AWS_DEFAULT_REGION = "${params.AWS_REGION}"
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install Script Deps') {
            steps { sh 'pip install boto3' }
        }

        stage('Build Layer') {
            steps {
                withAWS(role: params.ASSUME_ROLE_ARN, roleSessionName: "layer-build-${env.BUILD_NUMBER}") {
                    script {
                        if (params.INSTALL_MODE == 'LIBRARIES') {
                            sh """
                                python create_lambda_layer.py \
                                    --libraries ${params.LIBRARIES} \
                                    --layer-name ${params.LAYER_NAME} \
                                    --runtime ${params.PYTHON_RUNTIME} \
                                    --region ${params.AWS_REGION} ${params.UPLOAD ? '' : '--no-upload'}
                            """
                        } else {
                            sh """
                                python create_lambda_layer.py \
                                    --requirements-file ${params.REQUIREMENTS_FILE} \
                                    --layer-name ${params.LAYER_NAME} \
                                    --runtime ${params.PYTHON_RUNTIME} \
                                    --region ${params.AWS_REGION} ${params.UPLOAD ? '' : '--no-upload'}
                            """
                        }
                    }
                }
            }
        }

        stage('Archive') {
            when { expression { params.UPLOAD == false } }
            steps { archiveArtifacts artifacts: '**/*.zip', fingerprint: true }
        }
    }
}

### How it Works

1. **Parameters** allow a Jenkins user (or an automated trigger) to decide at run-time whether dependencies are supplied as a list of libraries or a `requirements.txt` file.  
2. **File Parameter** (`REQUIREMENTS_FILE`) is stored by Jenkins inside the workspace and its path is passed to the script via `--requirements-file`.  
3. **withAWS** step from the AWS Pipeline plugin assumes the provided IAM role and injects temporary credentials for the duration of the build.  
4. The same script is reused locally and in CI with _zero_ modifications because it already supports both `--libraries` and `--requirements-file` flags.

Feel free to tailor the pipeline (e.g., use a Docker agent with Python pre-installed, add automated tests, etc.).
