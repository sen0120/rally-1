# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools

from rally.common.plugin import plugin
from rally.task import context

# all VerifierContexts should be always hidden
configure = functools.partial(context.configure, hidden=True)


@plugin.base()
class VerifierContext(context.BaseContext):
    """Verifier context that will be run before starting a verification."""

    def __init__(self, ctx):
        super(VerifierContext, self).__init__(ctx)
        self.verification = self.context.get("verification", {})
        self.verifier = self.context["verifier"]

    @classmethod
    def validate(cls, config):
        # do not validate jsonschema.
        pass


class ContextManager(context.ContextManager):

    @staticmethod
    def validate(ctx):
        for name, config in ctx.items():
            VerifierContext.get(name, allow_hidden=True).validate(config)

    def _get_sorted_context_lst(self):
        return sorted([
            VerifierContext.get(name, allow_hidden=True)(self.context_obj)
            for name in self.context_obj["config"].keys()])

    def _log_prefix(self):
        return "Verification %s |" % self.context_obj["verifier"]["uuid"]
