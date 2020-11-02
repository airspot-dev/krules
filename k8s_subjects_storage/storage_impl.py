# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import copy

import yaml

from krules_core.subject import PropertyType

import pykube
import re


class SubjectsK8sStorage(object):

    def __init__(self, resource_path, resource_body=None, override_api_url=False):
        self._resource_path = resource_path
        self._resource_body = resource_body
        self._override_api_url = override_api_url
        self._resource_properties = None
        self._inferred_properties = None

    def __str__(self):
        return "{} instance for {}".format(self.__class__, self._resource_path)

    def _get_resource(self):
        if self._resource_body is None:
            api = self._get_api_client()
            #api_url = api.url
            #if self._use_local_proxy:

            resp = api.session.get(url=f"{api.url}{self._resource_path}")
            resp.raise_for_status()
            self._resource_body = resp.json()
        return self._resource_body

    def _get_api_client(self):
        if self._override_api_url:
            config = pykube.KubeConfig.from_url(self._override_api_url)
        else:
            config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)
        return api

    def _get_resource_properties(self):
        if self._resource_properties is None:
            props = {
                PropertyType.DEFAULT: {},
                PropertyType.EXTENDED: {}
            }
            props[PropertyType.DEFAULT].update(
                yaml.load(
                    self._get_resource().get("metadata", {}).get("annotations", {}).get("airspot.krules.dev/props", '{}'),
                    Loader=yaml.SafeLoader
                )
            )
            props[PropertyType.EXTENDED].update(
                yaml.load(
                    self._get_resource().get("metadata", {}).get("annotations", {}).get("airspot.krules.dev/ext_props", '{}'),
                    Loader=yaml.SafeLoader
                )
            )
            self._resource_properties = props
        return self._resource_properties

    def _get_inferred_properties(self):
        """
        properties inferred from the resource path
        group, apiversion, namespace, resourcetype, subresource as extended properties
        name as normal property
        (https://kubernetes.io/docs/reference/using-api/api-concepts/)
        """
        if self._inferred_properties is None:
            patterns = [
                # namespaced
                "^/apis/(?P<group>[^/]+)/(?P<apiversion>v[a-z0-9]+)/namespaces/(?P<namespace>[a-z0-9-]+)/(?P<resourcetype>[a-z]+)/(?P<name>[a-z0-9-]+)[/]?(?P<subresource>[a-z]*)$",
                # cluster scoped
                "^/apis/(?P<group>[^/]+)/(?P<apiversion>v[a-z0-9]+)/(?P<resourcetype>[a-z]+)/(?P<name>[a-z0-9-]+)[/]?(?P<subresource>[a-z]*)$",
                # api core (namespaced)
                "^/api[s]?/(?P<apiversion>v[a-z0-9]+)/namespaces/(?P<namespace>[a-z0-9-]+)/(?P<resourcetype>[a-z]+)/(?P<name>[a-z0-9-]+)[/]?(?P<subresource>[a-z]*)$",
                # api core
                "^/api[s]?/(?P<apiversion>v[a-z0-9]+)/(?P<resourcetype>[a-z]+)/(?P<name>[a-z0-9-]+)[/]?(?P<subresource>[a-z]*)$",
            ]
            match = None
            for pattern in patterns:
                match = re.match(pattern, self._resource_path)
                if match is not None:
                    break

            if match is None:
                raise ValueError(self._resource_path)
            dd = match.groupdict()
            name = dd.get("name")
            group = dd.get("group", "core")
            apiversion = dd.get("apiversion")
            namespace = dd.get("namespace")
            resourcetype = dd.get("resourcetype")
            subresource = dd.get("subresource")

            props = {
                PropertyType.DEFAULT: {},
                PropertyType.EXTENDED: {}
            }
            if group is not None:
                props[PropertyType.EXTENDED]["group"] = group
            props[PropertyType.EXTENDED]["apiversion"] = apiversion
            if namespace is not None:
                props[PropertyType.EXTENDED]["namespace"] = namespace
            props[PropertyType.EXTENDED]["resourcetype"] = resourcetype
            if subresource is not None:
                props[PropertyType.EXTENDED]["subresource"] = subresource

            props[PropertyType.EXTENDED]["name"] = name
            props[PropertyType.EXTENDED]["kind"] = self._get_resource().get("kind")

            self._inferred_properties = props

        return self._inferred_properties

    def _reset(self):
        # to avoid a call to the api server if we are sure we do not want to access properties
        # of the object other than those inferred we can provide directly the minmal resource (es: {"kind": "Pod"})
        if self._resource_body is not None and "uid" not in self._resource_body:
            self._resource_body = None
        self._resource_properties = None

    def _get_all_properties(self):
        props = {}
        props.update(self._get_resource_properties())
        props[PropertyType.DEFAULT].update(self._get_inferred_properties()[PropertyType.DEFAULT])
        props[PropertyType.EXTENDED].update(self._get_inferred_properties()[PropertyType.EXTENDED])

        return props

    def is_concurrency_safe(self):
        return False

    def is_persistent(self):
        return True

    def load(self):

        props = self._get_all_properties()

        return copy.deepcopy(props[PropertyType.DEFAULT]), copy.deepcopy(props[PropertyType.EXTENDED])


    def store(self, inserts=[], updates=[], deletes=[]):
        if len(inserts)+len(updates)+len(deletes) == 0:
            return

        props = self._get_resource_properties()
        for prop in tuple(inserts) + tuple(updates):
            props[prop.type][prop.name] = prop.value
        for prop in deletes:
            if prop.name in props[prop.type]:
                del props[prop.type][prop.name]

        api = self._get_api_client()

        patch = {
            "metadata": {
                "annotations": {
                    "airspot.krules.dev/props": yaml.dump(props[PropertyType.DEFAULT], Dumper=yaml.SafeDumper),
                    "airspot.krules.dev/ext_props": yaml.dump(props[PropertyType.EXTENDED], Dumper=yaml.SafeDumper),
                }
            }
        }
        resp = api.session.patch(url=f"{api.url}{self._resource_path}",
                                 headers={"Content-Type": "application/merge-patch+json"},
                                 json=patch)
        resp.raise_for_status()

    def set(self, prop, old_value_default=None):
        """
        Set value for property, works both in update and insert
        This funtion requires updating the resource to prepare for the next patch
        :return: value, old_value
        """
        self._reset()

        props = self._get_resource_properties()
        old_value = props[prop.type].get(prop.name, old_value_default)
        new_value = prop.get_value(old_value)
        props[prop.type][prop.name] = new_value
        patch = {
            "metadata": {
                "annotations": {
                    "airspot.krules.dev/props": yaml.dump(props[PropertyType.DEFAULT], Dumper=yaml.SafeDumper),
                    "airspot.krules.dev/ext_props": yaml.dump(props[PropertyType.EXTENDED], Dumper=yaml.SafeDumper),
                }
            }
        }

        api = self._get_api_client()
        resp = api.session.patch(url=f"{api.url}{self._resource_path}",
                                 headers={"Content-Type": "application/merge-patch+json"},
                                 json=patch)
        resp.raise_for_status()

        return new_value, old_value

    def get(self, prop):
        """
        Get a single property
        Always returns the updated value, so it needs a call to update the resource
        Raises AttributeError if not found
        """
        self._reset()
        props = self._get_all_properties()
        try:
            value = props[prop.type][prop.name]
        except KeyError:
            raise AttributeError(prop.name)

        return value

    def delete(self, prop):
        """
        Delete a single property
        This funtion requires updating the resource to prepare for the next patch
        """
        self._reset()

        props = self._get_resource_properties()
        try:
            del props[prop.type][prop.name]
        except KeyError:
            pass
        patch = {
            "metadata": {
                "annotations": {
                    "airspot.krules.dev/props": yaml.dump(props[PropertyType.DEFAULT], Dumper=yaml.SafeDumper),
                    "airspot.krules.dev/ext_props": yaml.dump(props[PropertyType.EXTENDED], Dumper=yaml.SafeDumper),
                }
            }
        }

        api = self._get_api_client()
        resp = api.session.patch(url=f"{api.url}{self._resource_path}",
                                 headers={"Content-Type": "application/merge-patch+json"},
                                 json=patch)
        resp.raise_for_status()

    def get_ext_props(self):
        """
        here we do not refresh resource because this is the only method we need if we just send the event outside
        :return: dict
        """
        return self._get_all_properties()[PropertyType.EXTENDED]

    def flush(self):
        """
        Flush remove only user added properties. Does not delete the object
        :return: Object reference
        """
        self._reset()

        api = self._get_api_client()

        patch = {
            "metadata": {
                "annotations": {
                    "airspot.krules.dev/props": "{}",
                    "airspot.krules.dev/ext_props": "{}",
                }
            }
        }
        resp = api.session.patch(url=f"{api.url}{self._resource_path}",
                                 headers={"Content-Type": "application/merge-patch+json"},
                                 json=patch)
        resp.raise_for_status()


