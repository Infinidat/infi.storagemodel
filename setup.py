
SETUP_INFO = dict(
    name = 'infi.storagemodel',
    version = '0.1.35-develop',
    author = 'Guy Rozendorn',
    author_email = 'guy@rzn.co.il',

    url = 'http://www.infinidat.com',
    license = 'PSF',
    description = """A high-level library for traversing the OS storage model.""",
    long_description = """A high-level cross-platform abstraction of the OS storage stack (LUNs, disks, volumes, etc).""",

    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Python Software Foundation License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],

    install_requires = ['distribute', 'Brownie', 'daemon', 'infi.instruct >= 0.5.9', 'infi.hbaapi >= 0.1.14', 'infi.asi >= 0.1.10', 'infi.devicemanager >= 0.1.7', 'infi.multipathtools >= 0.1.12', 'infi.wmpio >= 0.1.7', 'infi.pyutils >= 0.0.20', 'infi.dtypes.hctl', 'infi.dtypes.wwn', 'infi.mountoolinux >= 0.1.5', 'infi.parted >= 0.1.4', 'infi.sgutils >= 0.1', 'infi.diskmanagement >= 0.1.15', 'json_rest', 'infi.cwrap >= 0.2.3', ],
    namespace_packages = ['infi'],

    package_dir = {'': 'src'},
    package_data = {'': ['rescan-scsi-bus.sh', ]},
    include_package_data = True,
    zip_safe = False,

    entry_points = dict(
        console_scripts = ['devlist = infi.storagemodel.examples:devlist'],
        gui_scripts = []),
    )

platform_install_requires = {
    'windows' : [],
    'linux' : [],
    'macosx' : [],
}

def _get_os_name():
    import platform
    system = platform.system().lower().replace('-', '').replace('_', '')
    if system == 'darwin':
        return 'macosx'
    return system


def setup():
    from setuptools import setup as _setup
    from setuptools import find_packages
    SETUP_INFO['packages'] = find_packages('src')
    SETUP_INFO['install_requires'] += platform_install_requires[_get_os_name()]
    _setup(**SETUP_INFO)

if __name__ == '__main__':
    setup()

