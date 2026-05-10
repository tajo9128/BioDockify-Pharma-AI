from setuptools import setup, find_packages

setup(
    name="deep-drive",
    version="1.0.0",
    description="PAN Code Forensics Skill for Agent Zero",
    author="Webis PAN",
    packages=find_packages(),
    py_modules=[],
    install_requires=[
        "pandas",
        "numpy",
        "scikit-learn",
        "tqdm",
    ],
)
