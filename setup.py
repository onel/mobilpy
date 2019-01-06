
from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()


# tutorial: 
# https://python-packaging.readthedocs.io/en/latest/index.html
setup(name='mobilpy',
        version='0.1',
        description='Library that helps create the XML necessary for online payments through MobilPay',
        long_description=readme(),
        keywords='online payments mobilpay netopia',
        url='https://github.com/onel/mobilpy',
        author='Andrei Onel',
        author_email='andrei@edumo.org',
        license='MIT',
        packages=['mobilpy'],
        # https://pypi.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Topic :: Office/Business :: Financial',
            'Topic :: Text Processing :: Markup :: XML'
        ],
        install_requires=[
            'pycrypto',
            'pyOpenSSL'
        ],
        # include_package_data=True,
        zip_safe=False)