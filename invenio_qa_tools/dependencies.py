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

"""Dependency management related cli commands for invenio-qa-tools."""

from __future__ import absolute_import, print_function

import collections
import json
import os
import sys
from contextlib import contextmanager

import click
import yaml
from setuptools.build_meta import prepare_metadata_for_build_wheel

from invenio_qa_tools.api import build_package_requirements, \
    build_requirements_list


@contextmanager
def suppress_stdout(suppress=True):
    """Suppress output of stdout."""
    if not suppress:
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout
    else:
        yield


@contextmanager
def suppress_stderr(suppress=False):
    """Suppress output of stderr."""
    if suppress:
        with open(os.devnull, "w") as devnull:
            old_stderr = sys.stderr
            sys.stderr = devnull
            try:
                yield
            finally:
                sys.stderr = old_stderr
    else:
        yield


def generate_dist_info(repopath, suppress_output=True, suppress_errors=False):
    """."""
    # 'prepare_metadata_for_build_wheel' requires that root of current working
    #  directory contains 'setup.py' file of the package which build metadata
    # should be generated.
    os.chdir(repopath)
    with suppress_stdout(suppress_output):
        # Stdout is suppressed by default as distutils
        # generate a lot info which is not needed
        with suppress_stderr(suppress_errors):
            dist_info_dir = prepare_metadata_for_build_wheel(repopath)
    os.chdir(os.path.dirname(__file__))
    return dist_info_dir


@click.command(
    'check-dependencies',
    help='TODO')
@click.argument(
    'packages',
    metavar='FILE',
    type=click.Path(exists=True, resolve_path=True),
    nargs=-1)
@click.option('--json', 'output_format', flag_value='json')
@click.option('--yaml', 'output_format', flag_value='yaml')
@click.option('--display-distutils-output', is_flag=True)
@click.option('--suppress-distutils-warnings', is_flag=True)
@click.option('--raise-on-conflict', is_flag=True)
@click.option('--verbose', is_flag=True)
@click.pass_context
def check_dependencies(ctx,
                       packages,
                       output_format,
                       display_distutils_output=False,
                       suppress_distutils_warnings=False,
                       raise_on_conflict=False,
                       verbose=False):
    """."""
    requirements_of_packages = []

    for dir in packages:

        dist_info_dir = generate_dist_info(dir,
                                           display_distutils_output,
                                           suppress_distutils_warnings)

        metadata_path = os.path.join(dir, dist_info_dir, 'metadata.json')
        with click.open_file(metadata_path) as package_metadata:
            metadata = package_metadata.read()
            package_requirements = build_package_requirements(metadata)

        requirements_of_packages.append(package_requirements)

    packages_by_requirement = build_requirements_list(
        requirements_of_packages,
        raise_on_confict=raise_on_conflict)

    if output_format == 'json':
        click.echo(json.dumps(packages_by_requirement))
    elif output_format == 'yaml':
        click.echo(yaml.safe_dump(packages_by_requirement))
    else:

        od = collections.OrderedDict(sorted(
            packages_by_requirement.items(),
            key=lambda i: i[0].lower()))

        for package in od:
            message = click.style(package + '\n')

            conflict = len(
                od[package]['version_specifiers']) > 1

            if conflict:
                message += click.style('\tCONFLICT\n', fg='red')
            else:
                message += click.style('\tOK\n', fg='green')

            for k, v in od[package].items():
                for version in v:
                    if k != 'version_specifiers':
                        message += click.style('\t{} : {}\n'
                                               .format(version, k))

            if not conflict:
                if verbose:
                    click.echo(message)
            else:
                click.echo(message)
