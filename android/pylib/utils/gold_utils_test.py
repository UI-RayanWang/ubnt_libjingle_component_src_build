#!/usr/bin/env vpython
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for gold_utils."""

#pylint: disable=protected-access

import contextlib
import os
import tempfile
import unittest

from pylib.constants import host_paths
from pylib.utils import gold_utils

with host_paths.SysPath(host_paths.BUILD_PATH):
  from skia_gold_common import unittest_utils

import mock  # pylint: disable=import-error
from pyfakefs import fake_filesystem_unittest  # pylint: disable=import-error

createSkiaGoldArgs = unittest_utils.createSkiaGoldArgs


def assertArgWith(test, arg_list, arg, value):
  i = arg_list.index(arg)
  test.assertEqual(arg_list[i + 1], value)


class AndroidSkiaGoldSessionDiffTest(fake_filesystem_unittest.TestCase):
  def setUp(self):
    self.setUpPyfakefs()
    self._working_dir = tempfile.mkdtemp()

  @mock.patch.object(gold_utils.AndroidSkiaGoldSession, '_RunCmdForRcAndOutput')
  def test_commandCommonArgs(self, cmd_mock):
    cmd_mock.return_value = (None, None)
    args = createSkiaGoldArgs(git_revision='a', local_pixel_tests=False)
    sgp = gold_utils.AndroidSkiaGoldProperties(args)
    session = gold_utils.AndroidSkiaGoldSession(self._working_dir,
                                                sgp,
                                                None,
                                                'corpus',
                                                instance='instance')
    session.Diff('name', 'png_file', None)
    call_args = cmd_mock.call_args[0][0]
    self.assertIn('diff', call_args)
    assertArgWith(self, call_args, '--corpus', 'corpus')
    assertArgWith(self, call_args, '--instance', 'instance')
    assertArgWith(self, call_args, '--input', 'png_file')
    assertArgWith(self, call_args, '--test', 'name')
    assertArgWith(self, call_args, '--work-dir', self._working_dir)
    i = call_args.index('--out-dir')
    # The output directory should be a subdirectory of the working directory.
    self.assertIn(self._working_dir, call_args[i + 1])


class AndroidSkiaGoldSessionDiffLinksTest(fake_filesystem_unittest.TestCase):
  class FakeArchivedFile(object):
    def __init__(self, path):
      self.name = path

    def Link(self):
      return 'file://' + self.name

  class FakeOutputManager(object):
    def __init__(self):
      self.output_dir = tempfile.mkdtemp()

    @contextlib.contextmanager
    def ArchivedTempfile(self, image_name, _, __):
      filepath = os.path.join(self.output_dir, image_name)
      yield AndroidSkiaGoldSessionDiffLinksTest.FakeArchivedFile(filepath)

  def setUp(self):
    self.setUpPyfakefs()
    self._working_dir = tempfile.mkdtemp()

  def test_outputManagerUsed(self):
    args = createSkiaGoldArgs(git_revision='a', local_pixel_tests=True)
    sgp = gold_utils.AndroidSkiaGoldProperties(args)
    session = gold_utils.AndroidSkiaGoldSession(self._working_dir, sgp, None,
                                                None, None)
    with open(os.path.join(self._working_dir, 'input-inputhash.png'), 'w') as f:
      f.write('input')
    with open(os.path.join(self._working_dir, 'closest-closesthash.png'),
              'w') as f:
      f.write('closest')
    with open(os.path.join(self._working_dir, 'diff.png'), 'w') as f:
      f.write('diff')

    output_manager = AndroidSkiaGoldSessionDiffLinksTest.FakeOutputManager()
    session._StoreDiffLinks('foo', output_manager, self._working_dir)

    copied_input = os.path.join(output_manager.output_dir, 'given_foo.png')
    copied_closest = os.path.join(output_manager.output_dir, 'closest_foo.png')
    copied_diff = os.path.join(output_manager.output_dir, 'diff_foo.png')
    with open(copied_input) as f:
      self.assertEqual(f.read(), 'input')
    with open(copied_closest) as f:
      self.assertEqual(f.read(), 'closest')
    with open(copied_diff) as f:
      self.assertEqual(f.read(), 'diff')

    self.assertEqual(session.GetGivenImageLink('foo'), 'file://' + copied_input)
    self.assertEqual(session.GetClosestImageLink('foo'),
                     'file://' + copied_closest)
    self.assertEqual(session.GetDiffImageLink('foo'), 'file://' + copied_diff)


if __name__ == '__main__':
  unittest.main(verbosity=2)
