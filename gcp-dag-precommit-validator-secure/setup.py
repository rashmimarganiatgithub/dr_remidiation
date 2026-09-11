import os
from setuptools import setup, find_packages, Extension
from setuptools.command.build_py import build_py

# 1. Determine if Cython should be used (Dual-Approach)
USE_CYTHON = os.environ.get('USE_CYTHON', '0') == '1'
ext_modules = []

# Dynamic class to strip ALL .py files from the package assembly area
class BinaryOnlyBuild(build_py):
    def run(self):
        # 1. First, perform the standard build (copies everything to build/lib)
        super().run()
        
        if USE_CYTHON:
            print("DYNAMIC STRIPPING: Removing all .py source files from the binary package...")
            # self.build_lib points to the temporary folder where the wheel is being assembled
            for root, dirs, files in os.walk(self.build_lib):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        os.remove(file_path)
                        print(f"STIPPED: {file_path}")

if USE_CYTHON:
    try:
        from Cython.Build import cythonize
        
        # We define all code-bearing files as extensions to ensure they are compiled
        # If we don't compile a file but delete the .py, that logic will be lost.
        extensions = [
            Extension("secure_gcp_dag_validator.cli", 
                      [os.path.join("secure_gcp_dag_validator", "cli.py")]),
            Extension("secure_gcp_dag_validator.core.rule_engine", 
                      [os.path.join("secure_gcp_dag_validator", "core", "rule_engine.py")]),
            Extension("secure_gcp_dag_validator.core.ast_parser", 
                      [os.path.join("secure_gcp_dag_validator", "core", "ast_parser.py")]),
        ]
        
        ext_modules = cythonize(
            extensions, 
            compiler_directives={'language_level': "3"},
            build_dir=os.path.join("build", "cythonized")
        )
        print("SUCCESS: Cython compilation prepared.")
    except ImportError:
        print("WARNING: Cython requested but not found. Falling back to pure Python.")

setup(
    name="secure-dag-validator",
    version="2.1.7",
    description="Secure Pre-commit hook for GCP DAG DR Compliance",
    author="Data Engineering Team",
    packages=find_packages(),
    include_package_data=True,
    # Hook in the dynamic stripper
    cmdclass={'build_py': BinaryOnlyBuild}, 
    package_data={
        "secure_gcp_dag_validator.rules": ["*.yaml"],
    },
    install_requires=[
        "pyyaml>=6.0",
    ],
    ext_modules=ext_modules,
    entry_points={
        "console_scripts": [
            "secure-dag-validator=secure_gcp_dag_validator.cli:main",
        ],
    },
)