import os
import platform
import subprocess
import time
from setuptools import Extension, dist, find_namespace_packages, setup

import Cython.Compiler.Options
import numpy as np  # noqa: E402
from Cython.Build import cythonize  # noqa: E402
# from torch.utils.cpp_extension import BuildExtension, CUDAExtension
EXT_TYPE = ''
try:
    import torch
    from torch.utils.cpp_extension import BuildExtension, CUDAExtension
    EXT_TYPE = 'pytorch'
except ModuleNotFoundError:
    from Cython.Distutils import build_ext as BuildExtension
    print('Skip building ext ops due to the absence of torch.')

Cython.Compiler.Options.docstrings = False

dist.Distribution().fetch_build_eggs(['Cython', 'numpy>=1.11.1'])


def readme():
    with open('README.md', encoding='utf-8') as f:
        content = f.read()
    return content


MAJOR = 0
MINOR = 2
PATCH = ''
SUFFIX = 'rc1'
if PATCH:
    SHORT_VERSION = '{}.{}.{}{}'.format(MAJOR, MINOR, PATCH, SUFFIX)
else:
    SHORT_VERSION = '{}.{}{}'.format(MAJOR, MINOR, SUFFIX)

version_file = 'movienet/tools/version.py'


def get_git_hash():

    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH', 'HOME']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        sha = out.strip().decode('ascii')
    except OSError:
        sha = 'unknown'

    return sha


def get_hash():
    if os.path.exists('.git'):
        sha = get_git_hash()[:7]
    elif os.path.exists(version_file):
        try:
            from movienet.tools.version import __version__
            sha = __version__.split('+')[-1]
        except ImportError:
            raise ImportError('Unable to get git version')
    else:
        sha = 'unknown'

    return sha


def write_version_py():
    content = """# GENERATED VERSION FILE
# TIME: {}

__version__ = '{}'
short_version = '{}'
"""
    sha = get_hash()
    VERSION = SHORT_VERSION + '+' + sha

    with open(version_file, 'w') as f:
        f.write(content.format(time.asctime(), VERSION, SHORT_VERSION))


def get_version():
    with open(version_file, 'r') as f:
        exec(compile(f.read(), version_file, 'exec'))
    return locals()['__version__']


def make_cuda_ext(name, module, sources):

    return CUDAExtension(
        name='{}.{}'.format(module, name),
        sources=[os.path.join(*module.split('.'), p) for p in sources],
        extra_compile_args={
            'cxx': [],
            'nvcc': [
                '-D__CUDA_NO_HALF_OPERATORS__',
                '-D__CUDA_NO_HALF_CONVERSIONS__',
                '-D__CUDA_NO_HALF2_OPERATORS__',
            ]
        })


def make_cython_ext(name, module, sources):
    extra_compile_args = None
    if platform.system() != 'Windows':
        extra_compile_args = {
            'cxx': ['-Wno-unused-function', '-Wno-write-strings']
        }

    extension = Extension(
        '{}.{}'.format(module, name),
        [os.path.join(*module.split('.'), p) for p in sources],
        include_dirs=[np.get_include()],
        language='c++',
        extra_compile_args=extra_compile_args)
    extension, = cythonize(extension)
    return extension


def get_requirements(filename='requirements.txt'):
    here = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(here, filename), 'r') as f:
        requires = [line.replace('\n', '') for line in f.readlines()]
    return requires


print('EXT_TYPE', EXT_TYPE)
ext_module_lst = []
if EXT_TYPE == 'pytorch':
    ext_module_lst = [
        # make_cython_ext(
        #     name='soft_nms_cpu',
        #     module='movienet.tools.detector.persondet.modules.core.ops.nms',
        #     sources=['src/soft_nms_cpu.pyx']),
        # make_cuda_ext(
        #     name='nms_cpu',
        #     module='movienet.tools.detector.persondet.modules.core.ops.nms',
        #     sources=['src/nms_cpu.cpp']),
        make_cuda_ext(
            name='nms_cuda',
            module='movienet.tools.detector.persondet.modules.core.ops.nms',
            sources=['src/nms_cuda.cpp', 'src/nms_kernel.cu']),
        make_cuda_ext(
            name='roi_align_cuda',
            module=
            'movienet.tools.detector.persondet.modules.core.ops.roi_align',
            sources=['src/roi_align_cuda.cpp', 'src/roi_align_kernel.cu']),
        make_cuda_ext(
            name='roi_pool_cuda',
            module=
            'movienet.tools.detector.persondet.modules.core.ops.roi_pool',
            sources=['src/roi_pool_cuda.cpp', 'src/roi_pool_kernel.cu'])
       
    ]
print('EXT_MODULE_LIST', ext_module_lst)
write_version_py()
setup(
    name='movienet-tools',
    version=get_version(),
    description='Some tools for movie analysis',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/tagMatrix4/movienet-tools',
    packages=find_namespace_packages(
        exclude=('docs', 'scripts', 'local', 'tests', 'model')),
    namespace_packages=("movienet", ),
    package_data={'movienet.tools.ops': ['*/*.so']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    license='Apache License 2.0',
    setup_requires=['pytest-runner', 'cython', 'numpy'],
    tests_require=['pytest', 'xdoctest'],
    install_requires=get_requirements(),
    ext_modules=ext_module_lst,
    cmdclass={'build_ext': BuildExtension},
    zip_safe=False)
