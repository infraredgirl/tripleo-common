# Copyright 2017 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import mock
import os
from six.moves import configparser
import tempfile

from oslo_concurrency import processutils

from tripleo_common.actions import ansible
from tripleo_common.tests import base


class AnsibleActionTest(base.TestCase):

    def setUp(self):
        super(AnsibleActionTest, self).setUp()

        self.hosts = "127.0.0.2"
        self.module = "foo"
        self.remote_user = 'fido'
        self.become = True
        self.become_user = 'root'
        self.ctx = mock.MagicMock()

    @mock.patch("tripleo_common.actions.ansible.write_default_ansible_cfg")
    @mock.patch("oslo_concurrency.processutils.execute")
    def test_run(self, mock_execute, mock_write_cfg):

        mock_execute.return_value = ('', '')

        action = ansible.AnsibleAction(
            hosts=self.hosts, module=self.module, remote_user=self.remote_user,
            become=self.become, become_user=self.become_user)
        ansible_config_path = os.path.join(action.work_dir, 'ansible.cfg')
        mock_write_cfg.return_value = ansible_config_path

        action.run(self.ctx)

        env = {
            'HOME': action.work_dir,
            'ANSIBLE_CONFIG': ansible_config_path
        }

        mock_execute.assert_called_once_with(
            'ansible', self.hosts, '-vvvvv', '--module-name',
            self.module, '--user', self.remote_user, '--become',
            '--become-user', self.become_user,
            env_variables=env, cwd=action.work_dir,
            log_errors=processutils.LogErrors.ALL
        )


class AnsiblePlaybookActionTest(base.TestCase):

    def setUp(self):
        super(AnsiblePlaybookActionTest, self).setUp()

        self.playbook = "myplaybook"
        self.limit_hosts = None
        self.remote_user = 'fido'
        self.become = True
        self.become_user = 'root'
        self.extra_vars = {"var1": True, "var2": 0}
        self.verbosity = 1
        self.ctx = mock.MagicMock()

    @mock.patch("tripleo_common.actions.ansible.write_default_ansible_cfg")
    @mock.patch("oslo_concurrency.processutils.execute")
    def test_run(self, mock_execute, mock_write_cfg):

        mock_execute.return_value = ('', '')

        action = ansible.AnsiblePlaybookAction(
            playbook=self.playbook, limit_hosts=self.limit_hosts,
            remote_user=self.remote_user, become=self.become,
            become_user=self.become_user, extra_vars=self.extra_vars,
            verbosity=self.verbosity)
        ansible_config_path = os.path.join(action.work_dir, 'ansible.cfg')
        mock_write_cfg.return_value = ansible_config_path

        action.run(self.ctx)

        pb = os.path.join(action.work_dir, 'playbook.yaml')
        env = {
            'HOME': action.work_dir,
            'ANSIBLE_CONFIG': ansible_config_path
        }

        mock_execute.assert_called_once_with(
            'ansible-playbook', '-v', pb, '--user',
            self.remote_user, '--become', '--become-user', self.become_user,
            '--extra-vars', json.dumps(self.extra_vars),
            env_variables=env, cwd=action.work_dir,
            log_errors=processutils.LogErrors.ALL)


class CopyConfigFileTest(base.TestCase):

    def test_copy_config_file(self):
        with tempfile.NamedTemporaryFile() as ansible_cfg_file:
            ansible_cfg_path = ansible_cfg_file.name
            work_dir = tempfile.mkdtemp(prefix='ansible-mistral-action-test')
            # Needed for the configparser to be able to read this file.
            ansible_cfg_file.write(b'[defaults]\n')
            ansible_cfg_file.flush()

            resulting_ansible_config = ansible.write_default_ansible_cfg(
                work_dir, base_ansible_cfg=ansible_cfg_path)

            self.assertEqual(resulting_ansible_config,
                             os.path.join(work_dir, 'ansible.cfg'))

        config = configparser.ConfigParser()
        config.read(resulting_ansible_config)

        retry_files_enabled = config.get('defaults', 'retry_files_enabled')
        self.assertEqual(retry_files_enabled, 'False')
