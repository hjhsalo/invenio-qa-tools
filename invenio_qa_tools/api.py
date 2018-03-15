# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Python API of invenio-qa-tools."""

import json

from packaging.utils import canonicalize_name
from packaging.version import Version, parse


def build_package_requirements(package_metadata, **kwargs):
    """Generate package's requirements based on PEP426 metadata.

    Returns a dictionary with following structure from PEP426 package metadata
    definition produced e.g. with by setuptools `dist_info`:

            {package_A:
              {requirement_A: version_specifier_for_requirement_A},
              {requirement_B: version_specifier_for_requirement_B}
            }

    Example output:

            {invenio:
              {sphinx: (>=1.5.1)},
              {isort: (>=4.3.3)}
            }

    If two different version specifiers for same requirement are defined
    both of them are kept (e.g. ["Sphinx (>=1.5.1)", "Sphinx (>1.5)"])

    :param package_metadata:
        String representation of package's JSON metadata as defined by PEP426.
    :type package_metadata: str
    :param **run_requires:
        Should requirements of 'run_requires' key (if present in metadata)
        be taken into account as package's requirements. Defaults to True
    :type **run_requires: bool
    :param **tests_requires:
        Should requirements of 'tests_requires' key (if present in metadata)
        be taken into account as package's requirements. Defaults to True
    :type **tests_requires: bool
    :param **meta_requires:
        Should requirements of 'meta_requires' key (if present in metadata)
        be taken into account as package's requirements. Defaults to True
    :type **meta_requires: bool
    :param **build_requires:
        Should requirements of 'build_requires' key (if present in metadata)
        be taken into account as package's requirements. Defaults to True
    :type **build_requires: bool
    :param **dev_requires:
        Should requirements of 'dev_requires' key (if present in metadata)
        be taken into account as package's requirements. Defaults to True
    :type **dev_requires: bool

    """
    def _get_requirements(key, metadata):
        requirements = metadata.get(key, [])
        if len(requirements) > 1:
            unique_requirements = set()
            for req in requirements:
                if req.get('extra') == 'all':
                    return req.get('requires')
            #     unique_requirements.union(req.get('requires'))
            # return unique_requirements
        elif len(requirements) > 0:  # No 'extras' defined so no need to loop
            return requirements[0].get('requires')
        else:
            return set()

    if not package_metadata:
        raise ValueError('No package metadata provided')

    metadata = json.loads(package_metadata)

    requirements_list = set()  # Later converted to list

    if kwargs.get('run_requires', True):
        run_requires = _get_requirements('run_requires', metadata)
        requirements_list = requirements_list.union(run_requires)

    if kwargs.get('test_requires', True):
        test_requires = _get_requirements('test_requires', metadata)
        requirements_list = requirements_list.union(test_requires)

    if kwargs.get('meta_requires', True):
        meta_requires = _get_requirements('meta_requires', metadata)
        requirements_list = requirements_list.union(meta_requires)

    if kwargs.get('build_requires', True):
        build_requires = _get_requirements('build_requires', metadata)
        requirements_list = requirements_list.union(build_requires)

    if kwargs.get('dev_requires', True):
        dev_requires = _get_requirements('dev_requires', metadata)
        requirements_list = requirements_list.union(dev_requires)

    #  Get package name from metadata
    package_name = metadata['name']

    # Convert requirements_list items to dicts
    # E.g. "Sphinx (>=1.5.1)" to {sphinx: "(>=1.5.1)"}
    reqs = []
    for string in list(requirements_list):
        dep, ver = string.split()  # Split from whitespace characters.
        dep = canonicalize_name(dep)  # Canonicalize name according to PEP426.
        requirement = {dep: ver}  # e.g. {sphinx: "(>=1.5.1)"}
        reqs.append(requirement)

    return {package_name: reqs}


def build_requirements_list(package_list, raise_on_confict=False):
    """Generate list of requirements for a set of packages.

    :param package_list:
    Take following list of dictionaries as input.
    ('version_specifier' is a string defining a version
    specifier for a package's dependency as described by PEP440.)

    [
     {package_A:
          {requirement_A: version_specifier_of_this_pkg_for_requirement_A},
          {requirement_B: version_specifier_of_this_pkg_for_requirement_B}
     },
     {package_B:
          {requirement_A: version_specifier_of_this_pkg_for_requirement_A},
          {requirement_B: version_specifier_of_this_pkg_for_requirement_B},
          {requirement_C: version_specifier_of_this_pkg_for_requirement_C}
     }
    ]

    :param raise_on_confict: Should function continue even if there is a
        conflict in version_specifiers for a requirement. Default is False.
    :type raise_on_conflict: bool

    :return : On successful execution function returns following structure:
    [
     {requirement_A :
          {package_A : [version_specifier(s)_of_this_pkg_for_requirement_A]},
          {package_B : [version_specifier(s)_of_this_pkg_for_requirement_A]}
     },
     {requirement_B:
          {package_A : [version_specifier(s)_of_this_pkg_for_requirement_B]},
          {package_B : [version_specifier(s)_of_this_pkg_for_requirement_B]}
     },
     {requirement_C :
          {package_B : [version_specifier(s)_of_this_pkg_for_requirement_C]}
     }
    ]

    """
    requirements_list = {}

    for package in package_list:
        package_name, deplist = package.popitem()

        for dep in deplist:
            (dep_name, ver), = dep.items()

            if dep_name not in requirements_list:
                templist = []
                templist.append(ver)
                requirements_list[dep_name] = {package_name: templist}
            else:
                if package_name not in requirements_list[dep_name]:
                    requirements_list[dep_name][package_name] = []
                    requirements_list[dep_name][package_name].append(ver)
                else:
                    if not raise_on_confict:
                        requirements_list[dep_name][package_name].append(ver)
                    else:
                        raise ValueError('Package defines multiple '
                                         'version specifiers for '
                                         'same requirement')

            # Add 'version_strings' list to requirement object
            if 'version_specifiers' not in requirements_list[dep_name]:
                requirements_list[dep_name]['version_specifiers'] = []
                requirements_list[dep_name]['version_specifiers'].append(ver)

            if ver not in requirements_list[dep_name]['version_specifiers']:
                requirements_list[dep_name]['version_specifiers'].append(ver)

    return requirements_list
