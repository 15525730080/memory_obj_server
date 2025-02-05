from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="memory_obj_server",  # 项目在 PyPI 上的名称，确保未被占用
    version="0.1.0",
    author="fanbozhou",
    author_email="15525730080@163.com",
    description="python对象共享池",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/15525730080/memory_obj_server",  # 项目主页或仓库地址
    packages=find_packages(),
    install_requires=[
        "rpyc",
        "dill",
        "filelock",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
