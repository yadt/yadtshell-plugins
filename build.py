#   YADT - an Augmented Deployment Tool
#   Copyright (C) 2010-2014  Immobilien Scout GmbH
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pybuilder.core import use_plugin, init, Author

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.distutils")
use_plugin("python.frosted")

use_plugin("copy_resources")

name = 'yadtshell-plugins'
version = "1.3.8"
summary = "Yet Another Deployment Tool - the plugins"
description = summary
authors = [Author("Arne Hilmann", "arne.hilmann@gmail.com"),
           Author("Maximilien Riehl", "max@riehl.io")]
license = "GNU GPL v3"

default_task = ["analyze", "publish"]


@init
def set_properties(project):
    project.build_depends_on("mock")

    project.depends_on("yadtshell")
    project.depends_on("pyopenssl")
    project.depends_on("twisted")
    project.depends_on("simplejson")
    project.depends_on("treq")

    project.set_property("copy_resources_target", "$dir_dist")
    project.get_property("copy_resources_glob").append("setup.cfg")

    project.set_property("verbose", True)
    project.set_property('dir_dist_scripts', 'scripts')
    project.set_property('flake8_include_test_sources', True)
    project.set_property('flake8_ignore', 'E501')


@init(environments='teamcity')
def set_properties_for_teamcity_builds(project):
    project.set_property('teamcity_output', True)
    import os
    project.version = '%s-%s' % (project.version, os.environ.get('BUILD_NUMBER', 0))
    project.default_task = ['install_dependencies', 'publish']
