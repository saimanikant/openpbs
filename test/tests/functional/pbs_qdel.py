# coding: utf-8

# Copyright (C) 1994-2021 Altair Engineering, Inc.
# For more information, contact Altair at www.altair.com.
#
# This file is part of both the OpenPBS software ("OpenPBS")
# and the PBS Professional ("PBS Pro") software.
#
# Open Source License Information:
#
# OpenPBS is free software. You can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# OpenPBS is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Commercial License Information:
#
# PBS Pro is commercially licensed software that shares a common core with
# the OpenPBS software.  For a copy of the commercial license terms and
# conditions, go to: (http://www.pbspro.com/agreement.html) or contact the
# Altair Legal Department.
#
# Altair's dual-license business model allows companies, individuals, and
# organizations to create proprietary derivative works of OpenPBS and
# distribute them - whether embedded or bundled with other software -
# under a commercial license agreement.
#
# Use of Altair's trademarks, including but not limited to "PBS™",
# "OpenPBS®", "PBS Professional®", and "PBS Pro™" and Altair's logos is
# subject to Altair's trademark licensing policies.


from tests.functional import *


class TestQdel(TestFunctional):
    """
    This test suite contains tests for qdel
    """

    def test_qdel_with_server_tagged_in_jobid(self):
        """
        Test to make sure that qdel uses server tagged in jobid instead of
        the PBS_SERVER conf setting
        """
        self.du.set_pbs_config(confs={'PBS_SERVER': 'not-a-server'})
        j = Job(TEST_USER)
        j.set_attributes({ATTR_q: 'workq@' + self.server.hostname})
        jid = self.server.submit(j)
        try:
            self.server.delete(jid)
        except PbsDeleteError as e:
            self.assertFalse(
                'Unknown Host' in e.msg[0],
                "Error message is not expected as server name is"
                "tagged in the jobid")
        self.du.set_pbs_config(confs={'PBS_SERVER': self.server.hostname})

    def test_qdel_unknown(self):
        """
        Test that qdel for an unknown job throws error saying the same
        """
        j = Job(TEST_USER)
        jid = self.server.submit(j)
        self.server.delete(jid, wait=True)
        try:
            self.server.delete(jid)
            self.fail("qdel didn't throw 'Unknown job id' error")
        except PbsDeleteError as e:
            self.assertEqual("qdel: Unknown Job Id " + jid, e.msg[0])

    def test_qdel_history_job(self):
        """
        Test deleting a history job after a custom resource is deleted
        The deletion of the history job happens in teardown
        """
        self.server.add_resource('foo')
        a = {'job_history_enable': 'True'}
        rc = self.server.manager(MGR_CMD_SET, SERVER, a)
        self.assertEqual(rc, 0)        
        hook_body = "import pbs\n"
        hook_body += "e = pbs.event()\n"
        hook_body += "e.job.resources_used[\"foo\"] = \"10\"\n"
        a = {'event': 'execjob_epilogue', 'enabled': 'True'}
        self.server.create_import_hook("epi", a, hook_body)
        j = Job(TEST_USER)
        j.set_sleep_time(10)
        jid = self.server.submit(j)
        self.server.expect(JOB, {'job_state': 'R'}, id=jid)
        self.server.log_match(jid + ";Exit_status=0", interval=2,
                              max_attempts=8)
        try:
            rc = self.server.manager(MGR_CMD_DELETE, RSC, id="foo")
        except PbsManagerError as e:
            m = "Resource busy on job"
            self.assertIn(m, e.msg[0])
