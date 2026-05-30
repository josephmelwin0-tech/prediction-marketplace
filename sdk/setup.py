from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="predgent",
    version="0.1.0",
    author="Melwin Joseph",
    author_email="josephmelwin0@gmail.com",
    description="Connect your AI agent to the Agent Prediction Marketplace",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/josephmelwin0-tech/prediction-marketplace",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "predgent=predgent.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Intermediate",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ],
    keywords="prediction market ai agents betting llm langchain openai",
)