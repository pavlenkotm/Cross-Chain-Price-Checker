from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="cross-chain-price-checker",
    version="0.1.0",
    author="Cross-Chain Price Checker Contributors",
    description="A library for comparing token prices across DEXs and CEXs to identify arbitrage opportunities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pavlenkotm/Cross-Chain-Price-Checker",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ccpc=cross_chain_price_checker.cli:main",
        ],
    },
)
