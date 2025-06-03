import boto3
import subprocess
import os
import shutil
import zipfile
import tempfile
import argparse

def create_lambda_layer(libraries=None, layer_name='', runtime='python3.10', region_name='us-east-1', upload=True, requirements_file=None):
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    package_dir = os.path.join(temp_dir, 'python')
    
    # Create the package directory
    os.makedirs(package_dir)

    try:
        # Install the libraries into the package directory
        if libraries:
            for library in libraries:
                subprocess.check_call([f"pip install {library} -t {package_dir}"], shell=True)

        # Install additional libraries from requirements.txt
        if requirements_file:
            subprocess.check_call([f"pip install -r {requirements_file} -t {package_dir}"], shell=True)

        # Zip the package directory
        zip_file = os.path.join(temp_dir, f"{layer_name}.zip")
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(package_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, temp_dir)
                    zf.write(full_path, relative_path)

        if upload:
            # Upload the zip file to AWS Lambda
            client = boto3.client('lambda', region_name=region_name)
            with open(zip_file, 'rb') as f:
                response = client.publish_layer_version(
                    LayerName=layer_name,
                    Description=f'Lambda layer for {", ".join(libraries) if libraries else "multiple libraries"}',
                    Content={'ZipFile': f.read()},
                    CompatibleRuntimes=[runtime]
                )

            # Print the response
            print(response)
        else:
            print(f"Lambda layer package created at: {zip_file}")

    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Create an AWS Lambda layer from a pip library.')
    parser.add_argument('--libraries', nargs='+', help='The names of the pip libraries to include in the layer.')
    parser.add_argument('--layer-name', type=str, required=True, help='The name of the Lambda layer.')
    parser.add_argument('--runtime', type=str, default='python3.10', help='The runtime for the Lambda layer. Default is python3.10.')
    parser.add_argument('--region', type=str, default='us-east-1', help='The AWS region to create the Lambda layer in. Default is us-east-1.')
    parser.add_argument('--no-upload', action='store_true', help='If specified, the Lambda layer will not be uploaded to AWS.')
    parser.add_argument('--requirements-file', type=str, help='The path to a requirements.txt file to install additional libraries.')

    args = parser.parse_args()

    # Prompt for library names if not provided
    if not args.libraries:
        if not args.requirements_file:
            user_input = input('Please enter the pip library names (separated by spaces): ').strip()
            args.libraries = user_input.split() if user_input else None

    create_lambda_layer(args.libraries, args.layer_name, args.runtime, args.region, not args.no_upload, args.requirements_file)

if __name__ == '__main__':
    main()
