from setuptools import setup, find_packages

setup(
    name="open-aiagent-mcp",
    version="0.1.0",
    description="Agentic AI framework with MCP support",
    author="Mudakka",
    license="CC BY-NC 4.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn[standard]>=0.22.0",
        "pydantic>=2.7.1",
        "python-dotenv>=1.0.1",
        "requests>=2.31.0",
    ],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Creative Commons Attribution Non-Commercial 4.0 International License",
        "Operating System :: OS Independent",
    ],
) 