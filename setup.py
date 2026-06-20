from setuptools import setup, find_packages

setup(
    name="Evan_Coin",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "ecdsa==0.19.0",
        "six==1.17.0",
    ],
    entry_points={
        "console_scripts": [
            "evan-coin=Evan_Coin.main:main",
        ],
    },
    python_requires=">=3.8",
    description="A basic cryptocurrency built in Python",
    author="Evan Parshall",
)