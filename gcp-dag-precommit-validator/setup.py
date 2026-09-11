from setuptools import setup, find_packages

setup(
    name="gcp-dag-validator",
    version="2.1.7", # <--- BUMP THIS VERSION For Every New Release
    description="Pre-commit hook for GCP DAG Disaster Recovery Compliance",
    author="Data Engineering Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "gcp_dag_validator.rules": ["*.yaml"],
    },
    install_requires=[
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "gcp-dag-validator=gcp_dag_validator.cli:main",
        ],
    },
)