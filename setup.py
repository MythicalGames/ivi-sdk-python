from pathlib import Path
import pkg_resources
import re
from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess


class ivi_build_py(build_py):
    def run(self):
        from grpc_tools.protoc import main as protoc_main
        subprocess.check_call([
            'git', 'clone', '-b', 'v2.0', '--single-branch', '--depth', '1',
            'https://github.com/MythicalGames/ivi-sdk-proto',
            'ivi-sdk-proto'])
        protopaths = list(map(str, Path('ivi-sdk-proto').rglob('*.proto')))
        proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')
        if 0 != protoc_main([
            'grpc_tools.protoc', '-I{}'.format(proto_include),
            '-Iivi-sdk-proto', '--python_out=ivi_sdk',
            '--grpc_python_out=ivi_sdk'] + protopaths
        ):
            raise RuntimeError("protoc failed, see previous")
        # hackaround:
        # protobuf still doesn't correctly specify imports for Python3
        # this may break for different versions of protobuf/grpc for python
        # https://github.com/protocolbuffers/protobuf/issues/1491
        genpys = list(Path('ivi_sdk').rglob('*pb2*.py'))
        for py in genpys:
            with py.open(mode='r+t') as pyfile:
                pytext = pyfile.read()
                pyfile.seek(0)
                pyfile.write(
                    re.sub(r'\nfrom (?!google)', '\nfrom ivi_sdk.', pytext))
                pyfile.truncate()
        build_py.run(self)

    def find_package_modules(self, package, package_dir):
        genpys = list(Path('./ivi_sdk').rglob('*.py'))
        modules = []
        for f in genpys:
            modulename = f.with_suffix("")
            modules.append((package, str(modulename), str(f)))
        return modules


base_requires = ['grpcio==1.34.0', 'protobuf<4.0dev,>=3.5.0.post1']

setup(
    name='ivi_sdk',
    version='0.1',
    description='Simple IVI gRPC stream API wrapper',
    packages=[''],
    package_dir={'': 'ivi_sdk'},
    install_requires=base_requires,
    setup_requires=base_requires + ['grpcio-tools==1.34.0'],
    test_requires=base_requires + ['pytest', 'pytest-asyncio'],
    cmdclass={'build_py': ivi_build_py})
