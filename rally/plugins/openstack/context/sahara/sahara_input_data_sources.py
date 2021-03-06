# Copyright 2015: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import requests
from six.moves.urllib import parse

from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack import osclients
from rally.plugins.openstack.scenarios.sahara import utils
from rally.plugins.openstack.scenarios.swift import utils as swift_utils
from rally.task import context


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="sahara_input_data_sources", platform="openstack",
                   order=443)
class SaharaInputDataSources(context.Context):
    """Context class for setting up Input Data Sources for an EDP job."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "input_type": {
                "enum": ["swift", "hdfs"],
            },
            "input_url": {
                "type": "string",
            },
            "swift_files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "download_url": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": False,
                    "required": ["name", "download_url"]
                }
            }
        },
        "additionalProperties": False,
        "required": ["input_type", "input_url"]
    }

    def setup(self):
        utils.init_sahara_context(self)
        self.context["sahara"]["swift_objects"] = []
        self.context["sahara"]["container_name"] = None

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            clients = osclients.Clients(user["credential"])
            if self.config["input_type"] == "swift":
                self.setup_inputs_swift(clients, tenant_id,
                                        self.config["input_url"],
                                        self.config["swift_files"],
                                        user["credential"].username,
                                        user["credential"].password)
            else:
                self.setup_inputs(clients, tenant_id,
                                  self.config["input_type"],
                                  self.config["input_url"])

    def setup_inputs(self, clients, tenant_id, input_type, input_url):
        input_ds = clients.sahara().data_sources.create(
            name=self.generate_random_name(),
            description="",
            data_source_type=input_type,
            url=input_url)

        self.context["tenants"][tenant_id]["sahara"]["input"] = input_ds.id

    def setup_inputs_swift(self, clients, tenant_id, input_url,
                           swift_files, username, password):
        swift_scenario = swift_utils.SwiftScenario(clients=clients,
                                                   context=self.context)
        # TODO(astudenov): use self.generate_random_name()
        container_name = "rally_" + parse.urlparse(input_url).netloc.rstrip(
            ".sahara")
        self.context["sahara"]["container_name"] = (
            swift_scenario._create_container(container_name=container_name))
        for swift_file in swift_files:
            content = requests.get(swift_file["download_url"]).content
            self.context["sahara"]["swift_objects"].append(
                swift_scenario._upload_object(
                    self.context["sahara"]["container_name"], content,
                    object_name=swift_file["name"]))
            input_ds_swift = clients.sahara().data_sources.create(
                name=self.generate_random_name(), description="",
                data_source_type="swift", url=input_url,
                credential_user=username, credential_pass=password)

            self.context["tenants"][tenant_id]["sahara"]["input"] = (
                input_ds_swift.id)

    def cleanup(self):
        resource_manager.cleanup(
            names=["swift.object", "swift.container"],
            users=self.context.get("users", []),
            superclass=swift_utils.SwiftScenario,
            task_id=self.get_owner_id())
        resource_manager.cleanup(
            names=["sahara.data_sources"],
            users=self.context.get("users", []),
            superclass=self.__class__,
            task_id=self.get_owner_id())
